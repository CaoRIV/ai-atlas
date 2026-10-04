"use client";

import { ArrowLeft, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { CatalogClientError, getTool } from "../lib/catalog/client";
import type { DetailState } from "../lib/catalog/detail-state";
import { explorerReturnHref, safeHttps } from "../lib/tool-navigation";
import { FeedbackPanel } from "./discover-components";
import { useLocale } from "./locale-context";
import { detailCopy } from "./tool-detail-copy";
import { DisplayDate, FactRow } from "./tool-facts";

export function ToolDetailContent({ toolId, initial, returnTo }: {
  toolId: string; initial: DetailState; returnTo?: string;
}) {
  const { locale } = useLocale();
  const text = detailCopy[locale];
  const [state, setState] = useState(initial);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => active.current?.abort(), []);
  const retry = async () => {
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    setState({ status: "loading" });
    try {
      const response = await getTool(toolId, { signal: controller.signal });
      if (!controller.signal.aborted) setState({ status: "ready", data: response.data });
    } catch (error) {
      if (controller.signal.aborted) return;
      setState(error instanceof CatalogClientError && error.status === 404
        ? { status: "not_found" }
        : { status: "error", requestId: error instanceof CatalogClientError ? error.requestId : null });
    }
  };
  const back = <Link className="detail-back" href={explorerReturnHref(returnTo)}><ArrowLeft aria-hidden size={18} strokeWidth={1.75} />{text.back}</Link>;
  if (state.status === "not_found") return <div className="detail-page">{back}<section><h1>{text.missing}</h1><p>{text.missingBody}</p></section></div>;
  if (state.status === "loading") return <div className="detail-page">{back}<div role="status" aria-busy="true"><p>{text.loading}</p><div aria-hidden className="detail-skeleton skeleton-line" /></div></div>;
  if (state.status === "error") return <div className="detail-page">{back}<FeedbackPanel kind="error" message={text.error} actionLabel={text.retry} onAction={() => void retry()} requestId={state.requestId} requestIdLabel={text.request} /></div>;
  const tool = state.data;
  const official = safeHttps(tool.official_url);
  const summaryKeys = ["platforms", "api_available", "open_source"];
  const groups = [
    { title: text.capabilities, facts: tool.facts.filter(f => f.key.startsWith("capability:")) },
    { title: text.pricing, facts: tool.facts.filter(f => f.key === "pricing") },
    { title: text.integrations, facts: tool.facts.filter(f => f.key.startsWith("integration:")) },
    { title: text.technical, facts: tool.facts.filter(f => !summaryKeys.includes(f.key) && !f.key.startsWith("capability:") && !f.key.startsWith("integration:") && f.key !== "pricing") },
  ];
  const factRow = (fact: typeof tool.facts[number]) => <FactRow key={fact.key} fact={fact} evidence={tool.evidence} locale={locale} label={tool.capabilities.find(c => `capability:${c.key}` === fact.key)?.name} />;
  return <div className="detail-page">
    {back}
    <header className="detail-header">
      <div className="detail-identity"><div aria-hidden className="tool-monogram">{Array.from(tool.name)[0]}</div><div><h1>{tool.name}</h1>{tool.provider ? <p>{tool.provider.name}</p> : null}</div></div>
      <p className="detail-description">{tool.description}</p>
      <ul className="tool-categories">{tool.categories.map(c => <li key={c.id}><Link className="category-badge" href={`/explorer?category=${encodeURIComponent(c.slug)}`}>{c.name}</Link></li>)}</ul>
      {official ? <a className="button button-primary detail-official" href={official} target="_blank" rel="noopener noreferrer">{text.official}<ExternalLink aria-hidden size={18} strokeWidth={1.75} /><span className="visually-hidden"> — {text.newTab}</span></a> : <p>{text.unavailableLink}</p>}
    </header>
    <div className="detail-columns">
      <div className="detail-main">{groups.map(group => <section className="detail-section" key={group.title}>
        <h2>{group.title}</h2>
        {group.facts.length ? group.facts.map(factRow) : <p className="detail-empty">{text.empty}</p>}
        {group.title === text.pricing && group.facts.some(f => f.value !== null) ? <p className="detail-note">{text.pricingNote}</p> : null}
        {group.title === text.technical && tool.models.length > 0 ? <div><h3>{text.models}</h3><ul>{tool.models.map(m => <li key={m.id}>{m.name}</li>)}</ul></div> : null}
      </section>)}</div>
      <aside className="detail-summary" aria-label={text.summary}><h2>{text.summary}</h2>
        {summaryKeys.map(key => factRow(tool.facts.find(f => f.key === key) ?? { key, value: null, verification_status: "unknown", evidence_ids: [] }))}
        <div className="detail-review"><h3>{text.reviewed}</h3><DisplayDate value={tool.last_verified_at} locale={locale} /><p>{text.reviewNote}</p></div>
      </aside>
    </div>
  </div>;
}
