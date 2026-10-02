"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CatalogClientError, getTools } from "../lib/catalog/client";
import type { ToolsResponse } from "../lib/catalog/types";
import {
  buildExplorerHref,
  getEffectiveExplorerSort,
  normalizeExplorerQuery,
  parseExplorerState,
  toCatalogQuery,
  type ExplorerSort,
  type ExplorerState,
  withExplorerPage,
  withExplorerSearch,
  withExplorerSort,
} from "../lib/explorer-state";
import { FeedbackPanel, SearchField, ToolCard, ToolGridSkeleton } from "./discover-components";
import { useLocale, type Locale } from "./locale-context";

type RequestState =
  | { key: string; status: "loading" }
  | { data: ToolsResponse; key: string; status: "success" }
  | { key: string; requestId: string | null; status: "error" };

type NavigationMode = "push" | "replace";

const copy = {
  vi: {
    empty: "Không có công cụ phù hợp với tìm kiếm và bộ lọc hiện tại.",
    error: "Chưa thể tải kết quả lúc này.",
    heading: "Khám phá công cụ AI",
    loading: "Đang tải kết quả…",
    next: "Trang sau",
    page: (page: number, total: number) => `Trang ${page} / ${total}`,
    previous: "Trang trước",
    requestId: "Mã yêu cầu",
    resultsHeading: "Kết quả",
    results: (total: number) => `${total} kết quả`,
    retry: "Thử lại",
    searchLabel: "Tìm theo tên hoặc tác vụ",
    searchPlaceholder: "Tên công cụ hoặc tác vụ…",
    searchSubmit: "Tìm kiếm",
    sort: "Sắp xếp",
    sortName: "Tên A–Z",
    sortRelevance: "Liên quan nhất",
    sortUpdated: "Cập nhật gần đây",
    supporting: "Tìm kiếm và so sánh thông tin đã được kiểm chứng trong catalog tuyển chọn.",
  },
  en: {
    empty: "No tools match the current search and filters.",
    error: "Results are unavailable right now.",
    heading: "Explore AI tools",
    loading: "Loading results…",
    next: "Next page",
    page: (page: number, total: number) => `Page ${page} of ${total}`,
    previous: "Previous page",
    requestId: "Request ID",
    resultsHeading: "Results",
    results: (total: number) => `${total} results`,
    retry: "Try again",
    searchLabel: "Search by name or task",
    searchPlaceholder: "Tool name or task…",
    searchSubmit: "Search",
    sort: "Sort",
    sortName: "Name A–Z",
    sortRelevance: "Most relevant",
    sortUpdated: "Recently updated",
    supporting: "Search and compare verified information across the curated catalog.",
  },
} as const;

type ExplorerSearchProps = {
  appliedQuery: string;
  locale: Locale;
  onCommit: (query: string, mode: NavigationMode) => void;
};

function ExplorerSearch({ appliedQuery, locale, onCommit }: ExplorerSearchProps) {
  const text = copy[locale];
  const [value, setValue] = useState(appliedQuery);
  const [isComposing, setIsComposing] = useState(false);
  const committedQuery = useRef(appliedQuery);

  useEffect(() => {
    if (isComposing) return;
    const normalized = normalizeExplorerQuery(value);
    if (normalized === committedQuery.current) return;

    const timeout = window.setTimeout(() => {
      if (normalized === committedQuery.current) return;
      committedQuery.current = normalized;
      onCommit(normalized, "replace");
    }, 300);
    return () => window.clearTimeout(timeout);
  }, [isComposing, onCommit, value]);

  const submit = useCallback(
    (query: string) => {
      committedQuery.current = query;
      onCommit(query, "push");
    },
    [onCommit],
  );

  return (
    <SearchField
      label={text.searchLabel}
      locale={locale}
      onCompositionChange={setIsComposing}
      onSubmit={submit}
      onValueChange={setValue}
      placeholder={text.searchPlaceholder}
      submitLabel={text.searchSubmit}
      value={value}
    />
  );
}

export function ExplorerContent() {
  const { locale } = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const serializedUrlState = searchParams.toString();
  const appliedState = useMemo(
    () => parseExplorerState(new URLSearchParams(serializedUrlState)),
    [serializedUrlState],
  );
  const catalogQuery = useMemo(() => toCatalogQuery(appliedState), [appliedState]);
  const [attempt, setAttempt] = useState(0);
  const requestKey = `${catalogQuery.toString()}#${attempt}`;
  const [requestState, setRequestState] = useState<RequestState>({ key: "", status: "loading" });
  const requestSequence = useRef(0);
  const text = copy[locale];

  const navigate = useCallback(
    (nextState: ExplorerState, mode: NavigationMode) => {
      const href = buildExplorerHref(nextState);
      const currentHref = serializedUrlState ? `${pathname}?${serializedUrlState}` : pathname;
      if (href !== currentHref) router[mode](href);
    },
    [pathname, router, serializedUrlState],
  );

  const commitSearch = useCallback(
    (query: string, mode: NavigationMode) => {
      navigate(withExplorerSearch(appliedState, query), mode);
    },
    [appliedState, navigate],
  );

  useEffect(() => {
    const controller = new AbortController();
    const sequence = ++requestSequence.current;

    void getTools(catalogQuery, { signal: controller.signal })
      .then((response) => {
        if (sequence === requestSequence.current && !controller.signal.aborted) {
          setRequestState({ data: response, key: requestKey, status: "success" });
        }
      })
      .catch((error: unknown) => {
        if (sequence === requestSequence.current && !controller.signal.aborted) {
          setRequestState({
            key: requestKey,
            requestId: error instanceof CatalogClientError ? error.requestId : null,
            status: "error",
          });
        }
      });

    return () => {
      controller.abort();
      if (requestSequence.current === sequence) requestSequence.current += 1;
    };
  }, [catalogQuery, requestKey]);

  const visibleState: RequestState =
    requestState.key === requestKey ? requestState : { key: requestKey, status: "loading" };
  const effectiveSort = getEffectiveExplorerSort(appliedState);
  const totalPages =
    visibleState.status === "success"
      ? Math.max(1, Math.ceil(visibleState.data.pagination.total / visibleState.data.pagination.page_size))
      : 1;

  return (
    <div className="explorer-page">
      <header className="explorer-header">
        <p className="eyebrow">AI Explorer</p>
        <h1>{text.heading}</h1>
        <p className="supporting">{text.supporting}</p>
        <ExplorerSearch
          appliedQuery={appliedState.q}
          key={appliedState.q}
          locale={locale}
          onCommit={commitSearch}
        />
      </header>

      <section aria-labelledby="explorer-results-title" className="explorer-results">
        <div className="explorer-toolbar">
          <div>
            <h2 id="explorer-results-title">{text.resultsHeading}</h2>
            {visibleState.status === "success" ? (
              <p aria-live="polite" className="results-status">{text.results(visibleState.data.pagination.total)}</p>
            ) : null}
          </div>
          <label className="explorer-sort">
            <span>{text.sort}</span>
            <select
              onChange={(event) => navigate(withExplorerSort(appliedState, event.target.value as ExplorerSort), "push")}
              value={effectiveSort}
            >
              {appliedState.q ? <option value="relevance">{text.sortRelevance}</option> : null}
              <option value="name">{text.sortName}</option>
              <option value="updated">{text.sortUpdated}</option>
            </select>
          </label>
        </div>

        {visibleState.status === "loading" ? <ToolGridSkeleton label={text.loading} /> : null}
        {visibleState.status === "error" ? (
          <FeedbackPanel
            actionLabel={text.retry}
            kind="error"
            message={text.error}
            onAction={() => setAttempt((current) => current + 1)}
            requestId={visibleState.requestId}
            requestIdLabel={text.requestId}
          />
        ) : null}
        {visibleState.status === "success" && visibleState.data.data.length === 0 ? (
          <FeedbackPanel kind="empty" message={text.empty} />
        ) : null}
        {visibleState.status === "success" && visibleState.data.data.length > 0 ? (
          <div className="tool-grid">
            {visibleState.data.data.map((tool) => <ToolCard key={tool.id} locale={locale} tool={tool} />)}
          </div>
        ) : null}

        {visibleState.status === "success" && visibleState.data.pagination.total > 0 ? (
          <nav aria-label={locale === "vi" ? "Phân trang kết quả" : "Results pagination"} className="pagination">
            <button
              className="button button-secondary"
              disabled={appliedState.page <= 1}
              onClick={() => navigate(withExplorerPage(appliedState, appliedState.page - 1), "push")}
              type="button"
            >
              <ChevronLeft aria-hidden="true" size={18} strokeWidth={1.75} />
              <span className="pagination-label">{text.previous}</span>
            </button>
            <span>{text.page(appliedState.page, totalPages)}</span>
            <button
              className="button button-secondary"
              disabled={appliedState.page >= totalPages}
              onClick={() => navigate(withExplorerPage(appliedState, appliedState.page + 1), "push")}
              type="button"
            >
              <span className="pagination-label">{text.next}</span>
              <ChevronRight aria-hidden="true" size={18} strokeWidth={1.75} />
            </button>
          </nav>
        ) : null}
      </section>
    </div>
  );
}
