from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from ai_atlas_api.builder_models import (
    BuilderCandidate,
    BuilderConstraints,
    BuilderLiteRequest,
    BuilderLiteResult,
    ConstraintDecision,
    ConstraintName,
    DataGap,
    DecisionReason,
    EvidenceReference,
    ExcludedCandidate,
)
from ai_atlas_api.catalog import EFFECTIVE_FACTS, CatalogRepository
from ai_atlas_api.catalog_models import ToolSummary
from ai_atlas_api.retrieval import HybridRetriever

EffectiveStatus = Literal["verified", "unverified", "unknown"]


@dataclass
class FactSnapshot:
    value: Any
    status: EffectiveStatus
    evidence: list[EvidenceReference] = field(default_factory=list)


@dataclass(frozen=True)
class CandidatePool:
    summaries: list[ToolSummary]
    facts: dict[UUID, dict[str, FactSnapshot]]
    warnings: tuple[str, ...] = ()


def _decision(
    constraint: ConstraintName,
    fact_key: str,
    facts: dict[str, FactSnapshot],
    matches: bool | None,
    *,
    unknown_reason: DecisionReason = "fact_not_verified",
) -> ConstraintDecision:
    fact = facts.get(fact_key)
    if fact is None:
        return ConstraintDecision(
            constraint=constraint,
            outcome="unknown",
            reason="fact_missing",
            fact_key=fact_key,
        )
    if fact.status != "verified" or matches is None:
        return ConstraintDecision(
            constraint=constraint,
            outcome="unknown",
            reason=unknown_reason,
            fact_key=fact_key,
        )
    return ConstraintDecision(
        constraint=constraint,
        outcome="pass" if matches else "fail",
        reason="constraint_met" if matches else "constraint_not_met",
        fact_key=fact_key,
        evidence_ids=[item.id for item in fact.evidence],
    )


def _contains(value: Any, expected: str) -> bool | None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        return None
    return expected in value


def _boolean(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _ram_matches(value: Any, available_ram_gb: float) -> bool | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) <= available_ram_gb


def _budget_decision(budget: float, facts: dict[str, FactSnapshot]) -> ConstraintDecision:
    fact = facts.get("pricing")
    if fact is None:
        return ConstraintDecision(
            constraint="budget_usd_month",
            outcome="unknown",
            reason="fact_missing",
            fact_key="pricing",
        )
    if fact.status != "verified" or not isinstance(fact.value, dict):
        return ConstraintDecision(
            constraint="budget_usd_month",
            outcome="unknown",
            reason="fact_not_verified",
            fact_key="pricing",
        )
    model = fact.value.get("model")
    if model == "free":
        return ConstraintDecision(
            constraint="budget_usd_month",
            outcome="pass",
            reason="constraint_met",
            fact_key="pricing",
            evidence_ids=[item.id for item in fact.evidence],
        )
    monthly_min = fact.value.get("monthly_min")
    currency = fact.value.get("currency")
    if (
        isinstance(monthly_min, int | float)
        and not isinstance(monthly_min, bool)
        and currency == "USD"
        and float(monthly_min) > budget
    ):
        return ConstraintDecision(
            constraint="budget_usd_month",
            outcome="fail",
            reason="constraint_not_met",
            fact_key="pricing",
            evidence_ids=[item.id for item in fact.evidence],
        )
    return ConstraintDecision(
        constraint="budget_usd_month",
        outcome="unknown",
        reason="pricing_not_comparable",
        fact_key="pricing",
    )


def evaluate_constraints(
    constraints: BuilderConstraints, facts: dict[str, FactSnapshot]
) -> list[ConstraintDecision]:
    decisions: list[ConstraintDecision] = []
    if constraints.platform is not None:
        fact = facts.get("platforms")
        decisions.append(
            _decision(
                "platform",
                "platforms",
                facts,
                _contains(fact.value, constraints.platform) if fact else None,
            )
        )
    if constraints.ram_gb is not None:
        fact = facts.get("min_ram_gb")
        decisions.append(
            _decision(
                "ram_gb",
                "min_ram_gb",
                facts,
                _ram_matches(fact.value, constraints.ram_gb) if fact else None,
            )
        )
    if constraints.deployment == "local_only":
        fact = facts.get("deployment_modes")
        decisions.append(
            _decision(
                "deployment",
                "deployment_modes",
                facts,
                _contains(fact.value, "local") if fact else None,
            )
        )
    if constraints.offline_required:
        fact = facts.get("offline_supported")
        decisions.append(
            _decision(
                "offline_required",
                "offline_supported",
                facts,
                _boolean(fact.value) if fact else None,
            )
        )
    if constraints.api_required:
        fact = facts.get("api_available")
        decisions.append(
            _decision(
                "api_required",
                "api_available",
                facts,
                _boolean(fact.value) if fact else None,
            )
        )
    if constraints.budget_usd_month is not None:
        decisions.append(_budget_decision(constraints.budget_usd_month, facts))
    return decisions


class BuilderLiteService:
    def __init__(self, repository: CatalogRepository, retriever: HybridRetriever) -> None:
        self.repository = repository
        self.retriever = retriever

    def build(self, request: BuilderLiteRequest) -> BuilderLiteResult:
        if (
            request.constraints.budget_usd_month is not None
            and request.constraints.monthly_usage is None
        ):
            return BuilderLiteResult(
                status="needs_clarification",
                objective_summary=request.objective,
                candidates=[],
                exclusions=[],
                data_gaps=[
                    DataGap(
                        tool_id=None,
                        tool_name=None,
                        constraint="budget_usd_month",
                        reason="monthly_usage_required",
                    )
                ],
                limitations=self.limitations(),
            )

        pool = self._candidate_pool(request.objective)
        candidates: list[BuilderCandidate] = []
        exclusions: list[ExcludedCandidate] = []
        gaps: list[DataGap] = []
        for summary in pool.summaries:
            facts = pool.facts.get(summary.id, {})
            decisions = evaluate_constraints(request.constraints, facts)
            rejected = [decision for decision in decisions if decision.outcome != "pass"]
            if rejected:
                exclusions.append(ExcludedCandidate(tool=summary, decisions=decisions))
                gaps.extend(
                    DataGap(
                        tool_id=summary.id,
                        tool_name=summary.name,
                        constraint=decision.constraint,
                        reason=decision.reason,
                    )
                    for decision in rejected
                    if decision.outcome == "unknown"
                )
                continue
            candidates.append(
                BuilderCandidate(
                    tool=summary,
                    decisions=decisions,
                    evidence=self._candidate_evidence(facts, decisions),
                )
            )

        return BuilderLiteResult(
            status="partial" if candidates else "no_match",
            objective_summary=request.objective,
            candidates=candidates,
            exclusions=exclusions,
            data_gaps=gaps,
            limitations=self.limitations(pool.warnings),
        )

    @staticmethod
    def limitations(warnings: tuple[str, ...] = ()) -> list[str]:
        return [
            *warnings,
            "single_tool_candidates_not_stack",
            "no_ai_extraction",
        ]

    @staticmethod
    def _candidate_evidence(
        facts: dict[str, FactSnapshot], decisions: list[ConstraintDecision]
    ) -> list[EvidenceReference]:
        relevant_keys = {decision.fact_key for decision in decisions if decision.outcome == "pass"}
        relevant_keys.update(
            key for key in facts if key == "identity" or key.startswith("capability:")
        )
        by_id: dict[UUID, EvidenceReference] = {}
        for key in sorted(item for item in relevant_keys if item is not None):
            fact = facts.get(key)
            if fact and fact.status == "verified":
                for evidence in fact.evidence:
                    by_id[evidence.id] = evidence
        return list(by_id.values())[:10]

    def _candidate_pool(self, objective: str) -> CandidatePool:
        retrieval = self.retriever.retrieve(objective)
        if not retrieval.tool_ids:
            return CandidatePool(summaries=[], facts={}, warnings=retrieval.warnings)

        with self.repository.connection() as connection:
            rows = connection.execute(
                """SELECT t.* FROM tools t
                   WHERE t.publication_status = 'published' AND t.id = ANY(%s)""",
                (list(retrieval.tool_ids),),
            ).fetchall()
            row_by_id = {row["id"]: row for row in rows}
            ordered_rows = [
                row_by_id[tool_id] for tool_id in retrieval.tool_ids if tool_id in row_by_id
            ]
            if not ordered_rows:
                return CandidatePool(summaries=[], facts={}, warnings=retrieval.warnings)
            summaries = self.repository.summaries(connection, ordered_rows)
            tool_ids = [summary.id for summary in summaries]
            fact_rows = connection.execute(
                EFFECTIVE_FACTS
                + """SELECT f.tool_id, f.key, f.value, f.effective_status,
                            e.id AS evidence_id, e.source_url, e.checked_at, e.expires_at
                     FROM effective_facts f
                     LEFT JOIN evidence e ON e.fact_id = f.id
                       AND e.fact_revision = f.revision
                       AND e.checked_at <= CURRENT_TIMESTAMP
                       AND CURRENT_TIMESTAMP < e.expires_at
                     WHERE f.tool_id = ANY(%s)
                     ORDER BY f.tool_id, f.key, e.checked_at DESC, e.id""",
                (tool_ids,),
            ).fetchall()

        facts: dict[UUID, dict[str, FactSnapshot]] = {tool_id: {} for tool_id in tool_ids}
        for row in fact_rows:
            tool_facts = facts[row["tool_id"]]
            snapshot = tool_facts.setdefault(
                row["key"],
                FactSnapshot(value=row["value"], status=row["effective_status"]),
            )
            if row["evidence_id"] is not None and snapshot.status == "verified":
                snapshot.evidence.append(
                    EvidenceReference(
                        id=row["evidence_id"],
                        fact_key=row["key"],
                        source_url=row["source_url"],
                        checked_at=row["checked_at"],
                        expires_at=row["expires_at"],
                    )
                )
        return CandidatePool(
            summaries=summaries,
            facts=facts,
            warnings=retrieval.warnings,
        )
