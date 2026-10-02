"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CatalogClientError, getCategories, getTools } from "../lib/catalog/client";
import type { Category, ToolSummary } from "../lib/catalog/types";
import { FeedbackPanel, SearchField, ToolCard, ToolGridSkeleton } from "./discover-components";
import { useLocale } from "./locale-context";

type LoadState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; requestId: string | null };

const copy = {
  vi: {
    categoriesDescription: "Chọn một lĩnh vực để bắt đầu lọc thư viện.",
    categoriesEmpty: "Chưa có danh mục công khai.",
    categoriesError: "Chưa thể tải danh mục lúc này.",
    categoriesHeading: "Danh mục",
    eyebrow: "Khám phá có căn cứ",
    heading: "Tìm công cụ AI. Xây stack phù hợp.",
    loadingCategories: "Đang tải danh mục…",
    loadingTools: "Đang tải công cụ…",
    note: "Catalog được tuyển chọn và mọi factual claim sẽ gắn với evidence còn hiệu lực.",
    requestId: "Mã yêu cầu",
    retry: "Thử lại",
    searchLabel: "Bạn đang tìm công cụ nào?",
    searchPlaceholder: "Tên công cụ hoặc tác vụ…",
    searchSubmit: "Tìm công cụ",
    supporting: "Khám phá công cụ theo nhu cầu và kết hợp thành quy trình có căn cứ.",
    toolsDescription: "Sáu công cụ đầu tiên theo thứ tự tên từ catalog hiện tại.",
    toolsEmpty: "Chưa có công cụ công khai trong thư viện.",
    toolsError: "Chưa thể tải công cụ lúc này.",
    toolsHeading: "Công cụ trong thư viện",
  },
  en: {
    categoriesDescription: "Choose an area to start filtering the library.",
    categoriesEmpty: "No public categories are available yet.",
    categoriesError: "Categories are unavailable right now.",
    categoriesHeading: "Categories",
    eyebrow: "Evidence-led discovery",
    heading: "Find AI tools. Build the right stack.",
    loadingCategories: "Loading categories…",
    loadingTools: "Loading tools…",
    note: "The catalog is curated, and every factual claim will link to current evidence.",
    requestId: "Request ID",
    retry: "Try again",
    searchLabel: "What kind of tool are you looking for?",
    searchPlaceholder: "Tool name or task…",
    searchSubmit: "Find tools",
    supporting: "Explore tools for your needs and combine them into an evidence-led workflow.",
    toolsDescription: "The first six tools by name from the current catalog.",
    toolsEmpty: "No public tools are available in the library yet.",
    toolsError: "Tools are unavailable right now.",
    toolsHeading: "Tools in the library",
  },
} as const;

export function HomeContent() {
  const { locale } = useLocale();
  const router = useRouter();
  const text = copy[locale];
  const [categoriesState, setCategoriesState] = useState<LoadState<Category[]>>({ status: "loading" });
  const [toolsState, setToolsState] = useState<LoadState<ToolSummary[]>>({ status: "loading" });
  const [categoriesAttempt, setCategoriesAttempt] = useState(0);
  const [toolsAttempt, setToolsAttempt] = useState(0);
  const [searchValue, setSearchValue] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void getCategories({ signal: controller.signal })
      .then((response) => setCategoriesState({ status: "success", data: response.data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setCategoriesState({
            status: "error",
            requestId: error instanceof CatalogClientError ? error.requestId : null,
          });
        }
      });
    return () => controller.abort();
  }, [categoriesAttempt]);

  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ page: "1", page_size: "6", sort: "name" });
    void getTools(query, { signal: controller.signal })
      .then((response) => setToolsState({ status: "success", data: response.data }))
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setToolsState({
            status: "error",
            requestId: error instanceof CatalogClientError ? error.requestId : null,
          });
        }
      });
    return () => controller.abort();
  }, [toolsAttempt]);

  const handleSearch = useCallback(
    (query: string) => {
      const params = new URLSearchParams();
      if (query) {
        params.set("q", query);
      }
      const serialized = params.toString();
      router.push(serialized ? `/explorer?${serialized}` : "/explorer");
    },
    [router],
  );

  return (
    <div className="home-page">
      <section className="home-intro" aria-labelledby="home-title">
        <p className="eyebrow">{text.eyebrow}</p>
        <h1 id="home-title">{text.heading}</h1>
        <p className="supporting">{text.supporting}</p>
        <SearchField
          label={text.searchLabel}
          locale={locale}
          onSubmit={handleSearch}
          onValueChange={setSearchValue}
          placeholder={text.searchPlaceholder}
          submitLabel={text.searchSubmit}
          value={searchValue}
        />
        <p className="foundation-note">{text.note}</p>
      </section>

      <section aria-labelledby="categories-title" className="home-section">
        <div className="section-heading">
          <h2 id="categories-title">{text.categoriesHeading}</h2>
          <p>{text.categoriesDescription}</p>
        </div>
        {categoriesState.status === "loading" ? (
          <div aria-busy="true" aria-live="polite" className="category-loading">
            <span>{text.loadingCategories}</span>
            <div aria-hidden="true" className="category-skeletons">
              {Array.from({ length: 5 }, (_, index) => (
                <span key={index} />
              ))}
            </div>
          </div>
        ) : null}
        {categoriesState.status === "success" && categoriesState.data.length > 0 ? (
          <div className="category-links">
            {categoriesState.data.map((category) => (
              <Link
                className="category-link"
                href={`/explorer?${new URLSearchParams({ category: category.slug }).toString()}`}
                key={category.id}
              >
                {category.name}
              </Link>
            ))}
          </div>
        ) : null}
        {categoriesState.status === "success" && categoriesState.data.length === 0 ? (
          <FeedbackPanel kind="empty" message={text.categoriesEmpty} />
        ) : null}
        {categoriesState.status === "error" ? (
          <FeedbackPanel
            actionLabel={text.retry}
            kind="error"
            message={text.categoriesError}
            onAction={() => {
              setCategoriesState({ status: "loading" });
              setCategoriesAttempt((attempt) => attempt + 1);
            }}
            requestId={categoriesState.requestId}
            requestIdLabel={text.requestId}
          />
        ) : null}
      </section>

      <section aria-labelledby="tools-title" className="home-section">
        <div className="section-heading">
          <h2 id="tools-title">{text.toolsHeading}</h2>
          <p>{text.toolsDescription}</p>
        </div>
        {toolsState.status === "loading" ? <ToolGridSkeleton label={text.loadingTools} /> : null}
        {toolsState.status === "success" && toolsState.data.length > 0 ? (
          <div className="tool-grid">
            {toolsState.data.map((tool) => (
              <ToolCard key={tool.id} locale={locale} tool={tool} />
            ))}
          </div>
        ) : null}
        {toolsState.status === "success" && toolsState.data.length === 0 ? (
          <FeedbackPanel kind="empty" message={text.toolsEmpty} />
        ) : null}
        {toolsState.status === "error" ? (
          <FeedbackPanel
            actionLabel={text.retry}
            kind="error"
            message={text.toolsError}
            onAction={() => {
              setToolsState({ status: "loading" });
              setToolsAttempt((attempt) => attempt + 1);
            }}
            requestId={toolsState.requestId}
            requestIdLabel={text.requestId}
          />
        ) : null}
      </section>
    </div>
  );
}
