import { z } from "zod";

export const PricingModelSchema = z.enum([
  "free",
  "freemium",
  "paid",
  "usage_based",
  "contact",
  "unknown",
]);
export type PricingModel = z.infer<typeof PricingModelSchema>;

export const VerificationStatusSchema = z.enum(["verified", "unverified", "unknown"]);
export type VerificationStatus = z.infer<typeof VerificationStatusSchema>;

export const PlatformSchema = z.enum(["web", "windows", "macos", "linux", "ios", "android"]);
export type Platform = z.infer<typeof PlatformSchema>;

export const CategorySchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
});
export type Category = z.infer<typeof CategorySchema>;

export const PricingSummarySchema = z.object({
  model: PricingModelSchema,
  verification_status: VerificationStatusSchema,
});
export type PricingSummary = z.infer<typeof PricingSummarySchema>;

export const ToolSummarySchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  description: z.string(),
  categories: z.array(CategorySchema),
  pricing: PricingSummarySchema,
  last_verified_at: z.string().nullable(),
});
export type ToolSummary = z.infer<typeof ToolSummarySchema>;

export const NamedEntitySchema = z.object({
  id: z.string(),
  name: z.string(),
});
export type NamedEntity = z.infer<typeof NamedEntitySchema>;

export const FactSchema = z.object({
  key: z.string(),
  value: z.json(),
  verification_status: VerificationStatusSchema,
  evidence_ids: z.array(z.string()),
});
export type Fact = z.infer<typeof FactSchema>;

export const CapabilitySchema = z.object({
  key: z.string(),
  name: z.string(),
  evidence_ids: z.array(z.string()),
});
export type Capability = z.infer<typeof CapabilitySchema>;

export const EvidenceSchema = z.object({
  id: z.string(),
  fact_key: z.string(),
  source_url: z.string(),
  checked_at: z.string(),
  expires_at: z.string(),
});
export type Evidence = z.infer<typeof EvidenceSchema>;

export const ToolDetailSchema = ToolSummarySchema.extend({
  official_url: z.string(),
  provider: NamedEntitySchema.nullable(),
  tags: z.array(z.string()),
  models: z.array(NamedEntitySchema),
  capabilities: z.array(CapabilitySchema),
  facts: z.array(FactSchema),
  evidence: z.array(EvidenceSchema),
  revision: z.number().int(),
  warnings: z.array(z.string()),
});
export type ToolDetail = z.infer<typeof ToolDetailSchema>;

export const PaginationSchema = z.object({
  page: z.number().int(),
  page_size: z.number().int(),
  total: z.number().int(),
});
export type Pagination = z.infer<typeof PaginationSchema>;

export const CategoriesResponseSchema = z.object({
  data: z.array(CategorySchema),
  request_id: z.string(),
});
export type CategoriesResponse = z.infer<typeof CategoriesResponseSchema>;

export const ToolsResponseSchema = z.object({
  data: z.array(ToolSummarySchema),
  pagination: PaginationSchema,
  request_id: z.string(),
});
export type ToolsResponse = z.infer<typeof ToolsResponseSchema>;

export const ToolResponseSchema = z.object({
  data: ToolDetailSchema,
  request_id: z.string(),
});
export type ToolResponse = z.infer<typeof ToolResponseSchema>;

export const CatalogErrorDetailSchema = z.object({
  field: z.string(),
  reason: z.string(),
});
export type CatalogErrorDetail = z.infer<typeof CatalogErrorDetailSchema>;

export const CatalogErrorResponseSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.array(CatalogErrorDetailSchema),
  }),
  request_id: z.string(),
});
export type CatalogErrorResponse = z.infer<typeof CatalogErrorResponseSchema>;
