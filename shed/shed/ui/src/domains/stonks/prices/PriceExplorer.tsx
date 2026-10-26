import { useEffect, useMemo, useState } from "react";
import { RequestError } from "../../../api/client";
import type { DatasetRows } from "../../../model";
import type { DatasetViewProps } from "../../types";
import { PriceChart, type Bar } from "./PriceChart";

type Stock = {
  isin: string;
  symbol: string;
  name: string;
  exchange: string;
  currency: string;
  close: number | null;
  bar_date: string;
};

type History = { isin: string; trade_date: string; bars: Bar[] };

const NO_HISTORY = "No price history for this trade date yet. It appears after the next Spark run.";

const RANGES: { label: string; months: number | null }[] = [
  { label: "1M", months: 1 },
  { label: "3M", months: 3 },
  { label: "6M", months: 6 },
  { label: "1Y", months: 12 },
  { label: "Max", months: null },
];

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function price(value: number | null | undefined): string {
  return typeof value === "number" ? value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
}

function stocksOf(prices: DatasetRows, names: Map<string, string>): Stock[] {
  const stocks = prices.rows.map((row) => {
    const isin = text(row.isin);
    return {
      isin,
      symbol: text(row.symbol),
      name: names.get(isin) || text(row.symbol),
      exchange: text(row.exchange),
      currency: text(row.currency),
      close: typeof row.close === "number" ? row.close : null,
      bar_date: text(row.bar_date),
    };
  });
  return stocks.sort((left, right) => left.name.localeCompare(right.name));
}

function matches(stock: Stock, needle: string): boolean {
  return [stock.name, stock.symbol, stock.isin].some((value) => value.toLowerCase().includes(needle));
}

function change(bars: Bar[]): number | null {
  const [previous, last] = bars.slice(-2);
  if (!previous || !last || previous.close === 0) return null;
  return (last.close / previous.close - 1) * 100;
}

export default function PriceExplorer({ client, data, selectedId, onSelect }: DatasetViewProps) {
  const [names, setNames] = useState<Map<string, string>>(new Map());
  const [search, setSearch] = useState("");
  const [months, setMonths] = useState<number | null>(12);
  const [history, setHistory] = useState<History | null>(null);
  const [error, setError] = useState("");
  const tradeDate = data.trade_date ?? "";

  useEffect(() => {
    const controller = new AbortController();
    const query = tradeDate ? `?trade_date=${tradeDate}` : "";
    client
      .getJson<DatasetRows>(`/datasets/universe${query}`, controller.signal)
      .then((universe) => setNames(new Map(universe.rows.map((row) => [text(row.isin), text(row.name)]))))
      .catch(() => {
        if (!controller.signal.aborted) setNames(new Map());
      });
    return () => controller.abort();
  }, [client, tradeDate]);

  const stocks = useMemo(() => stocksOf(data, names), [data, names]);
  const needle = search.trim().toLowerCase();
  const shown = needle ? stocks.filter((stock) => matches(stock, needle)) : stocks;
  const active = stocks.find((stock) => stock.isin === selectedId) ?? stocks[0] ?? null;
  const activeIsin = active?.isin;

  useEffect(() => {
    if (!activeIsin) return;
    const controller = new AbortController();
    const query = tradeDate ? `?trade_date=${tradeDate}` : "";
    setHistory(null);
    setError("");
    client
      .getJson<History>(`/history/${encodeURIComponent(activeIsin)}${query}`, controller.signal)
      .then((loaded) => {
        setHistory(loaded);
        setError("");
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) return;
        if (reason instanceof RequestError && reason.status === 404) setError(NO_HISTORY);
        else setError(reason instanceof Error ? reason.message : "Price history unavailable.");
      });
    return () => controller.abort();
  }, [client, activeIsin, tradeDate]);

  const bars = history?.isin === activeIsin ? history.bars : [];
  const moved = change(bars);

  return (
    <div className="price-explorer">
      <aside className="stock-list" aria-label="Stocks">
        <input
          className="data-grid-filter"
          type="search"
          placeholder="Search name, symbol or ISIN"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Search stocks"
        />
        <span className="data-grid-count">
          {shown.length} / {stocks.length} stocks
        </span>
        <ul className="stock-rows">
          {shown.map((stock) => (
            <li key={stock.isin}>
              <button
                className={`stock-row ${stock.isin === activeIsin ? "selected" : ""}`}
                aria-pressed={stock.isin === activeIsin}
                onClick={() => onSelect(stock.isin)}
              >
                <span className="stock-name">{stock.name}</span>
                <span className="stock-close">{price(stock.close)}</span>
                <span className="stock-symbol">{stock.symbol}</span>
                <span className="stock-currency">{stock.currency}</span>
              </button>
            </li>
          ))}
        </ul>
        {shown.length === 0 && <p className="empty">No stock matches.</p>}
      </aside>
      <section className="price-panel" aria-label={active ? `${active.name} prices` : "Prices"}>
        {active ? (
          <>
            <header className="price-header">
              <div>
                <h4>{active.name}</h4>
                <small>
                  {active.symbol} · {active.isin}
                  {active.exchange ? ` · ${active.exchange}` : ""}
                </small>
              </div>
              <div className="price-quote">
                <strong>
                  {price(active.close)} <small>{active.currency}</small>
                </strong>
                {moved !== null && (
                  <span className={moved >= 0 ? "price-up" : "price-down"}>
                    {moved >= 0 ? "+" : ""}
                    {moved.toFixed(2)}%
                  </span>
                )}
                <small>{active.bar_date}</small>
              </div>
            </header>
            <nav className="dataset-tabs price-ranges" aria-label="Range">
              {RANGES.map((range) => (
                <button
                  key={range.label}
                  className={`dataset-tab ${months === range.months ? "selected" : ""}`}
                  aria-pressed={months === range.months}
                  onClick={() => setMonths(range.months)}
                >
                  {range.label}
                </button>
              ))}
            </nav>
            {error === NO_HISTORY && <p className="empty">{error}</p>}
            {error && error !== NO_HISTORY && <p role="alert" className="error">{error}</p>}
            {!error && !history && <p className="empty">Loading price history…</p>}
            <PriceChart bars={bars} months={months} />
          </>
        ) : (
          <p className="empty">No prices for this trade date.</p>
        )}
      </section>
    </div>
  );
}
