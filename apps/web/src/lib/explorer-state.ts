import type { Platform, PricingModel } from "./catalog/types";

export const EXPLORER_PAGE_SIZE = 20;

export type ExplorerSort = "name" | "relevance" | "updated";

export type ExplorerState = {
  apiAvailable: boolean | null;
  categories: string[];
  openSource: boolean | null;
  page: number;
  platform: Platform | null;
  pricingModel: PricingModel | null;
  q: string;
  sort: ExplorerSort | null;
};

const platforms: Record<Platform, true> = {
  web: true,
  windows: true,
  macos: true,
  linux: true,
  ios: true,
  android: true,
};
const pricingModels: Record<PricingModel, true> = {
  free: true,
  freemium: true,
  paid: true,
  usage_based: true,
  contact: true,
  unknown: true,
};
const sorts: Record<ExplorerSort, true> = { relevance: true, name: true, updated: true };

function readEnum<T extends string>(value: string | null, values: Partial<Record<T, true>>): T | null {
  return value !== null && Object.hasOwn(values, value) ? (value as T) : null;
}

function readBoolean(value: string | null): boolean | null {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

function readPage(value: string | null): number {
  if (value === null || !/^[1-9]\d*$/.test(value)) return 1;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : 1;
}

export function normalizeExplorerQuery(value: string): string {
  return value.normalize("NFC").trim();
}

export function parseExplorerState(params: URLSearchParams): ExplorerState {
  const q = normalizeExplorerQuery(params.get("q") ?? "");
  const categories = Array.from(
    new Set(
      (params.get("category") ?? "")
        .split(",")
        .map((slug) => slug.trim())
        .filter(Boolean),
    ),
  );
  const sort = readEnum(params.get("sort"), sorts);

  return {
    apiAvailable: readBoolean(params.get("api_available")),
    categories,
    openSource: readBoolean(params.get("open_source")),
    page: readPage(params.get("page")),
    platform: readEnum(params.get("platform"), platforms),
    pricingModel: readEnum(params.get("pricing_model"), pricingModels),
    q,
    sort: sort === "relevance" && !q ? null : sort,
  };
}

export function getEffectiveExplorerSort(state: ExplorerState): ExplorerSort {
  return state.sort ?? (state.q ? "relevance" : "name");
}

export function serializeExplorerState(state: ExplorerState): URLSearchParams {
  const params = new URLSearchParams();
  if (state.q) params.set("q", state.q);
  if (state.categories.length > 0) params.set("category", state.categories.join(","));
  if (state.platform) params.set("platform", state.platform);
  if (state.pricingModel) params.set("pricing_model", state.pricingModel);
  if (state.apiAvailable !== null) params.set("api_available", String(state.apiAvailable));
  if (state.openSource !== null) params.set("open_source", String(state.openSource));
  if (state.sort && (state.sort !== "relevance" || state.q)) params.set("sort", state.sort);
  if (state.page > 1) params.set("page", String(state.page));
  return params;
}

export function toCatalogQuery(state: ExplorerState): URLSearchParams {
  const params = serializeExplorerState(state);
  params.set("sort", getEffectiveExplorerSort(state));
  params.set("page", String(state.page));
  params.set("page_size", String(EXPLORER_PAGE_SIZE));
  return params;
}

export function buildExplorerHref(state: ExplorerState): string {
  const query = serializeExplorerState(state).toString();
  return query ? `/explorer?${query}` : "/explorer";
}

export function withExplorerSearch(state: ExplorerState, value: string): ExplorerState {
  const q = normalizeExplorerQuery(value);
  return {
    ...state,
    page: 1,
    q,
    sort: !q && state.sort === "relevance" ? null : state.sort,
  };
}

type ExplorerFilters = Pick<
  ExplorerState,
  "apiAvailable" | "categories" | "openSource" | "platform" | "pricingModel"
>;

export function withExplorerFilters(
  state: ExplorerState,
  filters: Partial<ExplorerFilters>,
): ExplorerState {
  return { ...state, ...filters, page: 1 };
}

export function withExplorerSort(state: ExplorerState, sort: ExplorerSort): ExplorerState {
  return {
    ...state,
    page: 1,
    sort: sort === "relevance" && !state.q ? null : sort,
  };
}

export function withExplorerPage(state: ExplorerState, page: number): ExplorerState {
  return { ...state, page: Math.max(1, Math.trunc(page)) };
}
