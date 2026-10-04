"use client";

import type { ReactNode } from "react";
import type { Evidence, Fact } from "../lib/catalog/types";
import { safeHttps } from "../lib/tool-navigation";
import type { Locale } from "./locale-context";
import { detailCopy, enumLabels, factLabels } from "./tool-detail-copy";

export function DisplayDate({ value, locale }: { value: string | null; locale: Locale }) {
  if (!value || !Number.isFinite(Date.parse(value))) return <span>{detailCopy[locale].unknown}</span>;
  return <time dateTime={value}>{new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", {
    year: "numeric", month: "short", day: "numeric", timeZone: "UTC",
  }).format(new Date(value))} (UTC)</time>;
}

function Value({ value, locale, verified, field = "" }: {
  value: Fact["value"]; locale: Locale; verified: boolean; field?: string;
}): ReactNode {
  const text = detailCopy[locale];
  if (value === null) return <span>{text.unknown}</span>;
  if (typeof value === "boolean") return <span>{verified ? (value ? text.yes : text.no) : (value ? text.yesUnverified : text.noUnverified)}</span>;
  if (typeof value === "number") return <span>{new Intl.NumberFormat(locale).format(value)}</span>;
  if (typeof value === "string") return <span>{["model", "platforms", "deployment_modes"].includes(field) ? enumLabels[value]?.[locale === "vi" ? 0 : 1] ?? value : value}</span>;
  if (Array.isArray(value)) return value.length ? <ul className="fact-list">{value.map((item, index) => <li key={index}><Value value={item} locale={locale} verified={verified} field={field} /></li>)}</ul> : <span>{field === "conditions" ? text.noConditions : text.noItems}</span>;
  const entries = Object.entries(value).filter(([key]) => !["provider_id", "target_tool_id"].includes(key));
  return <dl className="fact-fields">{entries.map(([key, item]) => <div key={key}>
    <dt>{factLabels[key]?.[locale === "vi" ? 0 : 1] ?? key}</dt>
    <dd><Value value={item} locale={locale} verified={verified} field={key} /></dd>
  </div>)}</dl>;
}

export function EvidenceDisclosure({ sources, locale }: { sources: Evidence[]; locale: Locale }) {
  const text = detailCopy[locale];
  if (!sources.length) return <p className="fact-source-empty">{text.noSources}</p>;
  return <details className="fact-evidence"><summary>{text.sources} ({sources.length})</summary>
    <ul>{sources.map(source => {
      const href = safeHttps(source.source_url);
      return <li key={source.id}>
        {href ? <a href={href} target="_blank" rel="noopener noreferrer">{new URL(href).hostname}<span className="visually-hidden"> — {text.newTab}</span></a> : <span>{text.unavailableLink}</span>}
        <p>{text.checked}: <DisplayDate value={source.checked_at} locale={locale} /></p>
        <p>{text.expires}: <DisplayDate value={source.expires_at} locale={locale} /></p>
      </li>;
    })}</ul>
  </details>;
}

export function FactRow({ fact, evidence, locale, label }: { fact: Fact; evidence: Evidence[]; locale: Locale; label?: string }) {
  const text = detailCopy[locale];
  const status = fact.value === null ? "unknown" : fact.verification_status;
  // The API projects current-revision evidence, including stale sources whose IDs
  // are intentionally absent from effective verified evidence_ids.
  const sources = evidence.filter(source => source.fact_key === fact.key);
  return <article className="fact-row">
    <div className="fact-heading"><h3>{label ?? factLabels[fact.key]?.[locale === "vi" ? 0 : 1] ?? fact.key}</h3>
      <span className={`fact-status fact-status--${status}`}>{status === "unknown" ? text.unknown : text[status]}</span>
    </div>
    <div className="fact-value"><Value value={status === "unknown" ? null : fact.value} locale={locale} verified={status === "verified"} field={fact.key} /></div>
    <EvidenceDisclosure sources={sources} locale={locale} />
  </article>;
}
