import { lazy } from "react";
import type { DatasetView, DomainModule } from "./types";

export const WORKFLOW_MODULES: Record<string, DomainModule> = {
  "sre/incidents": {
    Detail: lazy(() => import("./sre/incidents/IncidentDetail")),
    handledActions: ["manual-action"],
  },
  "sre/reviews": {
    Detail: lazy(() => import("./sre/reviews/ReviewDetail")),
    events: [{ name: "check", label: "Check now", done: "Pull request discovery queued." }],
  },
};

export function workflowModule(domain: string, workflow: string): DomainModule {
  return WORKFLOW_MODULES[`${domain}/${workflow}`] ?? {};
}

export const DATASET_VIEWS: Record<string, DatasetView> = {
  "stonks/prices": lazy(() => import("./stonks/prices/PriceExplorer")),
};

export function datasetView(domain: string, dataset: string): DatasetView | undefined {
  return DATASET_VIEWS[`${domain}/${dataset}`];
}
