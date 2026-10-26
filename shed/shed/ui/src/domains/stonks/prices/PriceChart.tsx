import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";

export type Bar = {
  bar_date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
};

type CompleteBar = Bar & { open: number; high: number; low: number };

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function complete(bar: Bar): bar is CompleteBar {
  return bar.open !== null && bar.high !== null && bar.low !== null;
}

function monthsBefore(day: string, months: number): string {
  const moment = new Date(`${day}T00:00:00Z`);
  moment.setUTCMonth(moment.getUTCMonth() - months);
  return moment.toISOString().slice(0, 10);
}

export function PriceChart({ bars, months }: { bars: Bar[]; months: number | null }) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const candles = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumes = useRef<ISeriesApi<"Histogram"> | null>(null);

  useEffect(() => {
    if (!container.current) return;
    const grid = "rgba(230,230,230,.06)";
    const created = createChart(container.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: token("--text-dim"),
        fontFamily: token("--mono"),
      },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      rightPriceScale: { borderColor: token("--line") },
      timeScale: { borderColor: token("--line") },
    });
    const up = token("--green");
    const down = token("--red");
    const candleSeries = created.addSeries(CandlestickSeries, {
      upColor: up,
      downColor: down,
      borderUpColor: up,
      borderDownColor: down,
      wickUpColor: up,
      wickDownColor: down,
    });
    candleSeries.priceScale().applyOptions({ scaleMargins: { top: 0.05, bottom: 0.25 } });
    const volumeSeries = created.addSeries(HistogramSeries, { priceFormat: { type: "volume" }, priceScaleId: "" });
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    chart.current = created;
    candles.current = candleSeries;
    volumes.current = volumeSeries;
    return () => {
      created.remove();
      chart.current = null;
      candles.current = null;
      volumes.current = null;
    };
  }, []);

  useEffect(() => {
    const priced = bars.filter(complete);
    candles.current?.setData(
      priced.map((bar) => ({ time: bar.bar_date, open: bar.open, high: bar.high, low: bar.low, close: bar.close })),
    );
    volumes.current?.setData(
      priced.map((bar) => ({
        time: bar.bar_date,
        value: bar.volume ?? 0,
        color: bar.close >= bar.open ? "rgba(95,208,138,.35)" : "rgba(255,95,87,.35)",
      })),
    );
  }, [bars]);

  useEffect(() => {
    const timeScale = chart.current?.timeScale();
    const last = bars.at(-1)?.bar_date;
    if (!timeScale || !last) return;
    if (months === null) timeScale.fitContent();
    else timeScale.setVisibleRange({ from: monthsBefore(last, months), to: last });
  }, [bars, months]);

  return <div ref={container} className="price-chart" />;
}
