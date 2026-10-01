"use client";

import { AlertCircle, ArrowRight, Inbox, Search, X } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useId, useState } from "react";

import type { Locale } from "./locale-context";
import type { ToolSummary } from "../lib/catalog/types";

type SearchFieldProps = {
  label: string;
  locale: Locale;
  onSubmit: (query: string) => void;
  pending?: boolean;
  placeholder: string;
  submitLabel: string;
};

const pricingCopy = {
  vi: {
    contact: "Liên hệ",
    free: "Miễn phí",
    freemium: "Có gói miễn phí",
    paid: "Trả phí",
    unknown: "Chưa xác minh giá",
    unverified: "Cần xác minh giá",
    usage_based: "Theo mức dùng",
  },
  en: {
    contact: "Contact",
    free: "Free",
    freemium: "Free tier available",
    paid: "Paid",
    unknown: "Pricing not verified",
    unverified: "Pricing needs verification",
    usage_based: "Usage based",
  },
} as const;

const componentCopy = {
  vi: {
    clearSearch: "Xóa tìm kiếm",
    detail: "Xem chi tiết",
  },
  en: {
    clearSearch: "Clear search",
    detail: "View details",
  },
} as const;

export function SearchField({
  label,
  locale,
  onSubmit,
  pending = false,
  placeholder,
  submitLabel,
}: SearchFieldProps) {
  const inputId = useId();
  const [value, setValue] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit(value.trim());
  };

  return (
    <form className="search-field" onSubmit={handleSubmit} role="search">
      <label htmlFor={inputId}>{label}</label>
      <div className="search-field-row">
        <div className="search-input-wrap">
          <Search aria-hidden="true" size={20} strokeWidth={1.75} />
          <input
            autoComplete="off"
            id={inputId}
            name="q"
            onChange={(event) => setValue(event.target.value)}
            placeholder={placeholder}
            type="search"
            value={value}
          />
          {value ? (
            <button
              aria-label={componentCopy[locale].clearSearch}
              className="search-clear"
              onClick={() => setValue("")}
              type="button"
            >
              <X aria-hidden="true" size={18} strokeWidth={1.75} />
            </button>
          ) : null}
        </div>
        <button className="button button-primary search-submit" disabled={pending} type="submit">
          {submitLabel}
        </button>
      </div>
    </form>
  );
}

export function ToolCard({ locale, tool }: { locale: Locale; tool: ToolSummary }) {
  const copy = componentCopy[locale];
  const categories = tool.categories.slice(0, 2);
  const extraCategoryCount = Math.max(0, tool.categories.length - categories.length);
  const nameCharacters = Array.from(tool.name.trim());
  const monogram = (nameCharacters[0] ?? "A").toLocaleUpperCase(locale);
  const pricing = pricingCopy[locale];
  const pricingLabel =
    tool.pricing.verification_status === "verified"
      ? pricing[tool.pricing.model]
      : tool.pricing.verification_status === "unverified"
        ? pricing.unverified
        : pricing.unknown;
  const pricingNeedsReview =
    tool.pricing.verification_status !== "verified" || tool.pricing.model === "unknown";

  return (
    <article className="tool-card">
      <div className="tool-card-heading">
        <div aria-hidden="true" className="tool-monogram">
          {monogram}
        </div>
        <h3>{tool.name}</h3>
      </div>
      <p className="tool-description">{tool.description}</p>
      {categories.length > 0 ? (
        <ul aria-label={locale === "vi" ? "Danh mục" : "Categories"} className="tool-categories">
          {categories.map((category) => (
            <li className="category-badge" key={category.id}>
              {category.name}
            </li>
          ))}
          {extraCategoryCount > 0 ? (
            <li className="category-overflow">+{extraCategoryCount}</li>
          ) : null}
        </ul>
      ) : null}
      <div className="tool-card-footer">
        <span className={pricingNeedsReview ? "pricing-label pricing-label--review" : "pricing-label"}>
          {pricingLabel}
        </span>
        <Link
          aria-label={`${copy.detail} ${tool.name}`}
          className="tool-detail-link"
          href={`/tools/${encodeURIComponent(tool.id)}`}
        >
          <span>{copy.detail}</span>
          <ArrowRight aria-hidden="true" size={17} strokeWidth={1.75} />
        </Link>
      </div>
    </article>
  );
}

type FeedbackPanelProps = {
  actionLabel?: string;
  kind: "empty" | "error";
  message: string;
  onAction?: () => void;
  requestId?: string | null;
  requestIdLabel?: string;
};

export function FeedbackPanel({
  actionLabel,
  kind,
  message,
  onAction,
  requestId,
  requestIdLabel,
}: FeedbackPanelProps) {
  const Icon = kind === "error" ? AlertCircle : Inbox;

  return (
    <div className={`feedback-panel feedback-panel--${kind}`} role={kind === "error" ? "alert" : "status"}>
      <Icon aria-hidden="true" size={20} strokeWidth={1.75} />
      <div>
        <p>{message}</p>
        {requestId && requestIdLabel ? (
          <details className="request-id">
            <summary>{requestIdLabel}</summary>
            <code>{requestId}</code>
          </details>
        ) : null}
        {actionLabel && onAction ? (
          <button className="button button-secondary" onClick={onAction} type="button">
            {actionLabel}
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function ToolGridSkeleton({ label }: { label: string }) {
  return (
    <div aria-live="polite" aria-busy="true">
      <p className="loading-label">{label}</p>
      <div aria-hidden="true" className="tool-grid">
        {Array.from({ length: 6 }, (_, index) => (
          <div className="tool-card tool-card-skeleton" key={index}>
            <div className="skeleton-line skeleton-heading" />
            <div className="skeleton-line" />
            <div className="skeleton-line skeleton-line-short" />
            <div className="skeleton-line skeleton-footer" />
          </div>
        ))}
      </div>
    </div>
  );
}
