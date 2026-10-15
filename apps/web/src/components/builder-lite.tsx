"use client";

import { AlertCircle, ArrowRight, CheckCircle2, CircleHelp, SearchX } from "lucide-react";
import Link from "next/link";
import { type FormEvent, useMemo, useRef, useState } from "react";

import { buildCandidates, BuilderClientError } from "../lib/builder/client";
import type {
  BuilderLiteRequest,
  BuilderLiteResponse,
  BuilderStatus,
  ConstraintName,
  DecisionReason,
} from "../lib/builder/types";
import { safeHttps } from "../lib/tool-navigation";
import { useLocale } from "./locale-context";

type ResultState =
  | { status: "idle" }
  | { status: "pending" }
  | { status: "success"; response: BuilderLiteResponse }
  | { status: "error"; requestId: string | null };

type FormState = {
  objective: string;
  platform: "" | "web" | "windows" | "macos" | "linux" | "ios" | "android";
  ramGb: string;
  deployment: "" | "cloud_allowed" | "local_only";
  offlineRequired: boolean;
  apiRequired: boolean;
  budgetUsdMonth: string;
  monthlyUsage: string;
};

const initialForm: FormState = {
  objective: "",
  platform: "",
  ramGb: "",
  deployment: "",
  offlineRequired: false,
  apiRequired: false,
  budgetUsdMonth: "",
  monthlyUsage: "",
};

const exampleObjective = {
  vi: "Tôi cần một công cụ AI hỗ trợ viết và chỉnh sửa nội dung qua hội thoại.",
  en: "I need an AI tool for drafting and editing content through conversation.",
} as const;

const copy = {
  vi: {
    adjust: "Điều chỉnh yêu cầu",
    apiRequired: "Bắt buộc có API",
    budget: "Ngân sách tối đa (USD/tháng)",
    candidates: "Candidates đủ điều kiện",
    checked: "Kiểm tra",
    constraints: "Thiết bị và yêu cầu",
    constraintsCount: (count: number) => `${count} điều kiện đã nhập`,
    constraintsEmpty: "Chưa có điều kiện bắt buộc",
    deployment: "Hình thức triển khai",
    deploymentAny: "Chưa chỉ định",
    deploymentCloud: "Cloud được phép",
    deploymentLocal: "Chỉ local",
    description:
      "Baseline deterministic: kết hợp keyword/semantic retrieval khi embeddings khả dụng và chỉ cho hard constraint đi qua khi catalog có evidence còn hiệu lực.",
    evidence: "Evidence",
    example: "Dùng ví dụ",
    excluded: "Candidates bị loại",
    expires: "Hết hiệu lực",
    gaps: "Khoảng trống dữ liệu",
    heading: "Builder Lite",
    internalBeta: "Internal beta · Gemini chỉ dùng cho embeddings · chưa tạo stack hoàn chỉnh",
    limitationHeading: "Giới hạn của baseline",
    limitations: {
      semantic_retrieval_unavailable:
        "Semantic retrieval tạm không khả dụng; kết quả đang dùng keyword fallback.",
      single_tool_candidates_not_stack: "Kết quả là candidates riêng lẻ, chưa phải stack nhiều vai trò.",
      no_ai_extraction: "Objective chưa được AI trích xuất thành roles hoặc workflow.",
    },
    monthlyUsage: "Mức sử dụng dự kiến",
    monthlyUsageHint: "Cần khi đặt hard budget; ví dụ 1.000 requests/tháng.",
    noDecisions: "Không có hard constraint cần đánh giá.",
    objective: "Bạn muốn hoàn thành việc gì?",
    objectiveHint: "10–4000 ký tự. Keyword cụ thể giúp baseline tìm đúng hơn.",
    offlineRequired: "Bắt buộc hoạt động offline",
    platform: "Hệ điều hành / nền tảng",
    platformAny: "Chưa chỉ định",
    ram: "RAM khả dụng (GB)",
    reason: {
      constraint_met: "Có evidence đáp ứng điều kiện.",
      constraint_not_met: "Evidence cho thấy không đáp ứng điều kiện.",
      fact_missing: "Catalog chưa có fact cần thiết.",
      fact_not_verified: "Fact chưa verified hoặc evidence đã stale.",
      pricing_not_comparable: "Chưa thể chứng minh tổng chi phí trong ngân sách.",
      monthly_usage_required: "Cần mức sử dụng dự kiến để đánh giá hard budget.",
    },
    requestError: "Không thể chạy Builder Lite lúc này.",
    requestId: "Mã yêu cầu",
    status: {
      complete: ["Đã đủ điều kiện", "Baseline đã tìm thấy candidates."],
      partial: ["Đã tìm thấy candidates", "Đây chưa phải stack hoàn chỉnh; xem evidence và giới hạn bên dưới."],
      no_match: ["Chưa tìm được candidate phù hợp", "Không có tool nào vừa khớp keyword vừa vượt qua mọi hard constraint."],
      needs_clarification: ["Cần làm rõ yêu cầu", "Bổ sung thông tin được nêu trong khoảng trống dữ liệu rồi gửi lại."],
    },
    submit: "Tìm candidates",
    submitting: "Đang đánh giá…",
    summary: "Objective đã đánh giá",
    toolDetail: "Xem chi tiết",
  },
  en: {
    adjust: "Adjust requirements",
    apiRequired: "API required",
    budget: "Maximum budget (USD/month)",
    candidates: "Eligible candidates",
    checked: "Checked",
    constraints: "Device and requirements",
    constraintsCount: (count: number) => `${count} constraints entered`,
    constraintsEmpty: "No hard constraints entered",
    deployment: "Deployment",
    deploymentAny: "Not specified",
    deploymentCloud: "Cloud allowed",
    deploymentLocal: "Local only",
    description:
      "Deterministic baseline: combines keyword and semantic retrieval when embeddings are available, and passes hard constraints only with current catalog evidence.",
    evidence: "Evidence",
    example: "Use example",
    excluded: "Excluded candidates",
    expires: "Expires",
    gaps: "Data gaps",
    heading: "Builder Lite",
    internalBeta: "Internal beta · Gemini is used only for embeddings · no complete stack yet",
    limitationHeading: "Baseline limitations",
    limitations: {
      semantic_retrieval_unavailable:
        "Semantic retrieval is temporarily unavailable; results use keyword fallback.",
      single_tool_candidates_not_stack: "Results are individual candidates, not a multi-role stack.",
      no_ai_extraction: "The objective is not yet extracted into roles or a workflow by AI.",
    },
    monthlyUsage: "Expected monthly usage",
    monthlyUsageHint: "Required with a hard budget; for example 1,000 requests/month.",
    noDecisions: "No hard constraints required evaluation.",
    objective: "What do you want to accomplish?",
    objectiveHint: "10–4000 characters. Specific keywords improve this baseline.",
    offlineRequired: "Must work offline",
    platform: "Operating system / platform",
    platformAny: "Not specified",
    ram: "Available RAM (GB)",
    reason: {
      constraint_met: "Current evidence satisfies the constraint.",
      constraint_not_met: "Evidence shows the constraint is not satisfied.",
      fact_missing: "The catalog does not contain the required fact.",
      fact_not_verified: "The fact is unverified or its evidence is stale.",
      pricing_not_comparable: "Total cost cannot be proven within the budget.",
      monthly_usage_required: "Expected usage is required to evaluate a hard budget.",
    },
    requestError: "Builder Lite is unavailable right now.",
    requestId: "Request ID",
    status: {
      complete: ["Requirements satisfied", "The baseline found eligible candidates."],
      partial: ["Candidates found", "This is not a complete stack; review the evidence and limitations below."],
      no_match: ["No eligible candidate found", "No tool both matched the keywords and passed every hard constraint."],
      needs_clarification: ["Requirements need clarification", "Add the information identified in data gaps and submit again."],
    },
    submit: "Find candidates",
    submitting: "Evaluating…",
    summary: "Evaluated objective",
    toolDetail: "View details",
  },
} as const;

function requestFromForm(form: FormState): BuilderLiteRequest {
  const constraints: BuilderLiteRequest["constraints"] = {};
  if (form.platform) constraints.platform = form.platform;
  if (form.ramGb) constraints.ram_gb = Number(form.ramGb);
  if (form.deployment) constraints.deployment = form.deployment;
  if (form.offlineRequired) constraints.offline_required = true;
  if (form.apiRequired) constraints.api_required = true;
  if (form.budgetUsdMonth) constraints.budget_usd_month = Number(form.budgetUsdMonth);
  if (form.budgetUsdMonth && form.monthlyUsage.trim()) {
    constraints.monthly_usage = form.monthlyUsage.trim();
  }
  return { objective: form.objective.trim(), constraints };
}

function constraintLabel(name: ConstraintName, locale: "vi" | "en"): string {
  const labels = {
    vi: {
      platform: "Nền tảng",
      ram_gb: "RAM",
      deployment: "Triển khai",
      offline_required: "Offline",
      api_required: "API",
      budget_usd_month: "Ngân sách",
    },
    en: {
      platform: "Platform",
      ram_gb: "RAM",
      deployment: "Deployment",
      offline_required: "Offline",
      api_required: "API",
      budget_usd_month: "Budget",
    },
  } as const;
  return labels[locale][name];
}

function StatusPanel({ status, locale }: { status: BuilderStatus; locale: "vi" | "en" }) {
  const text = copy[locale];
  const [title, description] = text.status[status];
  const Icon = status === "no_match" ? SearchX : status === "needs_clarification" ? CircleHelp : CheckCircle2;
  return (
    <div className={`builder-status builder-status--${status}`} role="status">
      <Icon aria-hidden="true" size={22} strokeWidth={1.75} />
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </div>
  );
}

export function BuilderLite() {
  const { locale } = useLocale();
  const text = copy[locale];
  const objectiveRef = useRef<HTMLTextAreaElement>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [result, setResult] = useState<ResultState>({ status: "idle" });
  const constraintCount = useMemo(
    () =>
      [form.platform, form.ramGb, form.deployment, form.offlineRequired, form.apiRequired, form.budgetUsdMonth].filter(Boolean)
        .length,
    [form],
  );

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setResult({ status: "pending" });
    try {
      const response = await buildCandidates(requestFromForm(form));
      setResult({ status: "success", response });
    } catch (error) {
      setResult({
        status: "error",
        requestId: error instanceof BuilderClientError ? error.requestId : null,
      });
    }
  };

  const useExample = () => {
    if (form.objective && !window.confirm(locale === "vi" ? "Thay nội dung hiện tại bằng ví dụ?" : "Replace the current objective with the example?")) {
      return;
    }
    setForm((current) => ({ ...current, objective: exampleObjective[locale] }));
    objectiveRef.current?.focus();
  };

  const response = result.status === "success" ? result.response : null;

  return (
    <div className="builder-page">
      <header className="builder-header">
        <p className="eyebrow">{text.internalBeta}</p>
        <h1>{text.heading}</h1>
        <p className="supporting">{text.description}</p>
      </header>

      <form className="builder-form" onSubmit={submit}>
        <div className="builder-objective">
          <div className="builder-label-row">
            <label htmlFor="builder-objective">{text.objective}</label>
            <span aria-live="polite">{form.objective.length}/4000</span>
          </div>
          <textarea
            aria-describedby="builder-objective-hint"
            id="builder-objective"
            maxLength={4000}
            minLength={10}
            onChange={(event) => setForm((current) => ({ ...current, objective: event.target.value }))}
            ref={objectiveRef}
            required
            rows={6}
            value={form.objective}
          />
          <div className="builder-field-help" id="builder-objective-hint">
            <span>{text.objectiveHint}</span>
            <button className="text-button" onClick={useExample} type="button">
              {text.example}
            </button>
          </div>
        </div>

        <details className="builder-constraints">
          <summary>
            <span>{text.constraints}</span>
            <span>{constraintCount ? text.constraintsCount(constraintCount) : text.constraintsEmpty}</span>
          </summary>
          <div className="builder-constraint-grid">
            <label>
              <span>{text.platform}</span>
              <select
                onChange={(event) => setForm((current) => ({ ...current, platform: event.target.value as FormState["platform"] }))}
                value={form.platform}
              >
                <option value="">{text.platformAny}</option>
                <option value="web">Web</option>
                <option value="windows">Windows</option>
                <option value="macos">macOS</option>
                <option value="linux">Linux</option>
                <option value="ios">iOS</option>
                <option value="android">Android</option>
              </select>
            </label>
            <label>
              <span>{text.ram}</span>
              <input
                inputMode="decimal"
                max="1024"
                min="0.1"
                onChange={(event) => setForm((current) => ({ ...current, ramGb: event.target.value }))}
                step="0.1"
                type="number"
                value={form.ramGb}
              />
            </label>
            <label>
              <span>{text.deployment}</span>
              <select
                onChange={(event) => setForm((current) => ({ ...current, deployment: event.target.value as FormState["deployment"] }))}
                value={form.deployment}
              >
                <option value="">{text.deploymentAny}</option>
                <option value="cloud_allowed">{text.deploymentCloud}</option>
                <option value="local_only">{text.deploymentLocal}</option>
              </select>
            </label>
            <label>
              <span>{text.budget}</span>
              <input
                inputMode="decimal"
                max="1000000"
                min="0"
                onChange={(event) => setForm((current) => ({ ...current, budgetUsdMonth: event.target.value }))}
                step="0.01"
                type="number"
                value={form.budgetUsdMonth}
              />
            </label>
            {form.budgetUsdMonth ? (
              <label className="builder-wide-field">
                <span>{text.monthlyUsage}</span>
                <textarea
                  aria-describedby="builder-usage-hint"
                  maxLength={1000}
                  onChange={(event) => setForm((current) => ({ ...current, monthlyUsage: event.target.value }))}
                  rows={3}
                  value={form.monthlyUsage}
                />
                <small id="builder-usage-hint">{text.monthlyUsageHint}</small>
              </label>
            ) : null}
            <label className="builder-check-field">
              <input
                checked={form.offlineRequired}
                onChange={(event) => setForm((current) => ({ ...current, offlineRequired: event.target.checked }))}
                type="checkbox"
              />
              <span>{text.offlineRequired}</span>
            </label>
            <label className="builder-check-field">
              <input
                checked={form.apiRequired}
                onChange={(event) => setForm((current) => ({ ...current, apiRequired: event.target.checked }))}
                type="checkbox"
              />
              <span>{text.apiRequired}</span>
            </label>
          </div>
        </details>

        <button className="button button-primary builder-submit" disabled={result.status === "pending"} type="submit">
          {result.status === "pending" ? text.submitting : text.submit}
        </button>
      </form>

      <section aria-busy={result.status === "pending"} aria-live="polite" className="builder-results">
        {result.status === "error" ? (
          <div className="builder-error" role="alert">
            <AlertCircle aria-hidden="true" size={22} strokeWidth={1.75} />
            <div>
              <p>{text.requestError}</p>
              {result.requestId ? <code>{text.requestId}: {result.requestId}</code> : null}
            </div>
          </div>
        ) : null}

        {response ? (
          <>
            <StatusPanel locale={locale} status={response.data.status} />
            <div className="builder-summary">
              <h2>{text.summary}</h2>
              <p>{response.data.objective_summary}</p>
              <button className="button button-secondary" onClick={() => objectiveRef.current?.focus()} type="button">
                {text.adjust}
              </button>
            </div>

            {response.data.data_gaps.length ? (
              <section className="builder-result-section" aria-labelledby="builder-gaps-title">
                <h2 id="builder-gaps-title">{text.gaps}</h2>
                <ul className="builder-gap-list">
                  {response.data.data_gaps.map((gap, index) => (
                    <li key={`${gap.tool_id ?? "request"}-${gap.constraint}-${index}`}>
                      <strong>{gap.tool_name ? `${gap.tool_name} · ` : ""}{constraintLabel(gap.constraint, locale)}</strong>
                      <span>{text.reason[gap.reason as DecisionReason]}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {response.data.candidates.length ? (
              <section className="builder-result-section" aria-labelledby="builder-candidates-title">
                <h2 id="builder-candidates-title">{text.candidates}</h2>
                <div className="builder-candidate-list">
                  {response.data.candidates.map((candidate) => (
                    <article className="builder-candidate" key={candidate.tool.id}>
                      <div>
                        <h3>{candidate.tool.name}</h3>
                        <p>{candidate.tool.description}</p>
                      </div>
                      <ul className="builder-decision-list">
                        {candidate.decisions.length ? candidate.decisions.map((decision) => (
                          <li key={decision.constraint}>
                            <strong>{constraintLabel(decision.constraint, locale)}</strong>
                            <span>{text.reason[decision.reason]}</span>
                          </li>
                        )) : <li>{text.noDecisions}</li>}
                      </ul>
                      {candidate.evidence.length ? (
                        <details className="builder-evidence">
                          <summary>{text.evidence} ({candidate.evidence.length})</summary>
                          <ul>
                            {candidate.evidence.map((evidence) => {
                              const href = safeHttps(evidence.source_url);
                              return (
                                <li key={evidence.id}>
                                  {href ? <a href={href} rel="noopener noreferrer" target="_blank">{evidence.fact_key} · {new URL(href).hostname}</a> : <span>{evidence.fact_key}</span>}
                                  <span>{text.checked}: {new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" }).format(new Date(evidence.checked_at))}</span>
                                  <span>{text.expires}: {new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" }).format(new Date(evidence.expires_at))}</span>
                                </li>
                              );
                            })}
                          </ul>
                        </details>
                      ) : null}
                      <Link className="tool-detail-link" href={`/tools/${encodeURIComponent(candidate.tool.id)}`}>
                        <span>{text.toolDetail}</span>
                        <ArrowRight aria-hidden="true" size={17} strokeWidth={1.75} />
                      </Link>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            {response.data.exclusions.length ? (
              <details className="builder-exclusions">
                <summary>{text.excluded} ({response.data.exclusions.length})</summary>
                <ul>
                  {response.data.exclusions.map((excluded) => (
                    <li key={excluded.tool.id}>
                      <strong>{excluded.tool.name}</strong>
                      <ul>
                        {excluded.decisions.filter((decision) => decision.outcome !== "pass").map((decision) => (
                          <li key={decision.constraint}>{constraintLabel(decision.constraint, locale)}: {text.reason[decision.reason]}</li>
                        ))}
                      </ul>
                    </li>
                  ))}
                </ul>
              </details>
            ) : null}

            <section className="builder-limitations" aria-labelledby="builder-limitations-title">
              <h2 id="builder-limitations-title">{text.limitationHeading}</h2>
              <ul>
                {response.data.limitations.map((limitation) => <li key={limitation}>{text.limitations[limitation]}</li>)}
              </ul>
            </section>
          </>
        ) : null}
      </section>
    </div>
  );
}
