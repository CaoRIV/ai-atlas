import { z } from "zod";

import { PlatformSchema, ToolSummarySchema } from "../catalog/types";

export const BuilderStatusSchema = z.enum([
  "complete",
  "partial",
  "no_match",
  "needs_clarification",
]);
export type BuilderStatus = z.infer<typeof BuilderStatusSchema>;

export const ConstraintNameSchema = z.enum([
  "platform",
  "ram_gb",
  "deployment",
  "offline_required",
  "api_required",
  "budget_usd_month",
]);
export type ConstraintName = z.infer<typeof ConstraintNameSchema>;

export const DecisionReasonSchema = z.enum([
  "constraint_met",
  "constraint_not_met",
  "fact_missing",
  "fact_not_verified",
  "pricing_not_comparable",
  "monthly_usage_required",
]);
export type DecisionReason = z.infer<typeof DecisionReasonSchema>;

export const BuilderConstraintsSchema = z
  .object({
    platform: PlatformSchema.nullable().optional(),
    ram_gb: z.number().positive().max(1024).nullable().optional(),
    deployment: z.enum(["cloud_allowed", "local_only"]).nullable().optional(),
    offline_required: z.boolean().nullable().optional(),
    api_required: z.boolean().nullable().optional(),
    budget_usd_month: z.number().nonnegative().max(1_000_000).nullable().optional(),
    monthly_usage: z.string().min(1).max(1000).nullable().optional(),
  })
  .strict();
export type BuilderConstraints = z.infer<typeof BuilderConstraintsSchema>;

export const BuilderLiteRequestSchema = z
  .object({
    objective: z.string().min(10).max(4000),
    constraints: BuilderConstraintsSchema,
  })
  .strict();
export type BuilderLiteRequest = z.infer<typeof BuilderLiteRequestSchema>;

export const EvidenceReferenceSchema = z
  .object({
    id: z.string(),
    fact_key: z.string(),
    source_url: z.string(),
    checked_at: z.string(),
    expires_at: z.string(),
  })
  .strict();

export const ConstraintDecisionSchema = z
  .object({
    constraint: ConstraintNameSchema,
    outcome: z.enum(["pass", "fail", "unknown"]),
    reason: DecisionReasonSchema,
    fact_key: z.string().nullable(),
    evidence_ids: z.array(z.string()),
  })
  .strict();

export const BuilderCandidateSchema = z
  .object({
    tool: ToolSummarySchema,
    decisions: z.array(ConstraintDecisionSchema),
    evidence: z.array(EvidenceReferenceSchema),
  })
  .strict();
export type BuilderCandidate = z.infer<typeof BuilderCandidateSchema>;

export const ExcludedCandidateSchema = z
  .object({
    tool: ToolSummarySchema,
    decisions: z.array(ConstraintDecisionSchema),
  })
  .strict();
export type ExcludedCandidate = z.infer<typeof ExcludedCandidateSchema>;

export const DataGapSchema = z
  .object({
    tool_id: z.string().nullable(),
    tool_name: z.string().nullable(),
    constraint: ConstraintNameSchema,
    reason: DecisionReasonSchema,
  })
  .strict();
export type DataGap = z.infer<typeof DataGapSchema>;

export const BuilderLiteResultSchema = z
  .object({
    status: BuilderStatusSchema,
    objective_summary: z.string(),
    candidates: z.array(BuilderCandidateSchema),
    exclusions: z.array(ExcludedCandidateSchema),
    data_gaps: z.array(DataGapSchema),
    limitations: z.array(
      z.enum(["keyword_only_retrieval", "single_tool_candidates_not_stack", "no_ai_extraction"]),
    ),
  })
  .strict();
export type BuilderLiteResult = z.infer<typeof BuilderLiteResultSchema>;

export const BuilderLiteResponseSchema = z
  .object({
    data: BuilderLiteResultSchema,
    request_id: z.string(),
  })
  .strict();
export type BuilderLiteResponse = z.infer<typeof BuilderLiteResponseSchema>;
