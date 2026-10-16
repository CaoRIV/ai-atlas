import { describe, expect, it } from "vitest";

import { BuilderConstraintsSchema, ConstraintDecisionSchema } from "./types";

describe("Builder constraint contracts", () => {
  it("preserves false, null, and omitted input semantics", () => {
    expect(BuilderConstraintsSchema.parse({})).toEqual({});
    expect(
      BuilderConstraintsSchema.parse({
        offline_required: false,
        api_required: null,
      }),
    ).toEqual({offline_required: false, api_required: null});
  });

  it("rejects coercion, unknown fields, and usage without a budget", () => {
    expect(BuilderConstraintsSchema.safeParse({ram_gb: "8"}).success).toBe(false);
    expect(BuilderConstraintsSchema.safeParse({offline_required: 1}).success).toBe(false);
    expect(BuilderConstraintsSchema.safeParse({unsupported: true}).success).toBe(false);
    expect(BuilderConstraintsSchema.safeParse({monthly_usage: "100 requests"}).success).toBe(
      false,
    );
  });

  it("normalizes monthly usage when a budget is present", () => {
    expect(
      BuilderConstraintsSchema.parse({
        budget_usd_month: 10,
        monthly_usage: "  100 requests  ",
      }).monthly_usage,
    ).toBe("100 requests");
  });
});

describe("Constraint decision contracts", () => {
  it("accepts unknown only with an unknown reason and no evidence claim", () => {
    expect(
      ConstraintDecisionSchema.parse({
        constraint: "platform",
        outcome: "unknown",
        reason: "fact_missing",
        fact_key: "platforms",
        evidence_ids: [],
      }).outcome,
    ).toBe("unknown");

    expect(
      ConstraintDecisionSchema.safeParse({
        constraint: "platform",
        outcome: "fail",
        reason: "fact_missing",
        fact_key: "platforms",
        evidence_ids: [],
      }).success,
    ).toBe(false);
    expect(
      ConstraintDecisionSchema.safeParse({
        constraint: "platform",
        outcome: "unknown",
        reason: "fact_not_verified",
        fact_key: "platforms",
        evidence_ids: ["evidence-id"],
      }).success,
    ).toBe(false);
  });
});
