# Implementation backlog

Ngày 28/09/2026. **Toàn bộ task implementation dưới đây chưa bắt đầu.** Tài liệu đã được soạn không có nghĩa implementation Done.

Trạng thái: `Todo`, `In progress`, `Blocked`, `Done`, `Deferred`. Khi làm đổi trạng thái ngay tại dòng task; khi Done bổ sung ngày, thay đổi và bằng chứng checks. Priority: P0 cần cho core journey hoặc integrity; P1 cần trước MVP release; P2 sau MVP. Dependency là task ID, dấu `—` là không có. Không bắt đầu task phụ thuộc quyết định Proposed khi quyết định chưa chốt.

## MVP — foundation và Discover

| ID | Priority / status | Mô tả và deliverable | Dependencies | Acceptance criteria | Docs / requirements |
|---|---|---|---|---|---|
| TASK-001 | P0 / Todo | Review baseline; chốt auth/provider/model/embedding dimension/budget/UI language; ghi ADR và open questions còn lại | — | OQ-001/002/003 có quyết định hoặc nêu blocker cụ thể; ghi tariff/source/date khi chọn live provider; ADR-007/008 có trạng thái đúng; không bật live AI khi chưa có budget | [PRD](../product/PRD.md) OQ-001..006; [ADR](DECISIONS.md) |
| TASK-002 | P0 / Todo | Scaffold `apps/web`, `apps/api`, DB Compose, env example, fake adapter, CI lint/type/unit skeleton và setup Windows | TASK-001 | Versions pin, web/API/DB health chạy được từ clean setup; fake mode không gọi network AI; README có commands đã chạy; xác nhận ADR-009 | [Architecture](../architecture/SYSTEM_ARCHITECTURE.md); NFR-005/008 |
| TASK-003 | P0 / Todo | Implement schema/migrations cho catalog, evidence, users, runs, stacks; chốt ADR-010 | TASK-002 | Migration DB sạch pass; FK/composite FK/unique/check/rollback tests; snapshot/TTL schema nhất quán; embedding D đúng model config | [Data model](../architecture/DATA_MODEL.md); FR-001/008, NFR-008 |
| TASK-004 | P0 / Todo | Catalog API categories/list/detail, keyword/filter/pagination và OpenAPI | TASK-003 | Contract tests gồm multiple categories, unknown/stale filters, page rỗng, 404 archived; kết quả không duplicate; query parameter allowlist | [API](../architecture/API_DESIGN.md); FR-002/003 |
| TASK-005 | P0 / Todo | Curated format + import dry-run/upsert; seed 15 tools có nguồn chính thức, 8 categories và capability vocabulary | TASK-003 | Import lặp không nhân bản; lỗi source/FK/type rollback; 15 records publish có evidence/date, unknown minh bạch; synthetic fixtures tách khỏi curated data | [Data model](../architecture/DATA_MODEL.md); FR-001/011 |
| TASK-006 | P0 / Todo | Explorer UI search/filter/detail nối API thật | TASK-004, TASK-005 | Filter vào URL; loading/empty/error states; official links; source/date/unknown rõ; keyboard và 360px usable | [Flows](../product/USER_FLOWS.md); FR-002/003/013 |
| TASK-007 | P0 / Todo | Integration/E2E Journey A và sửa lỗi slice | TASK-006 | Search → filter → detail → official link pass; test empty/error/archived; ghi seed và command tái hiện | [PRD](../product/PRD.md); FR-001..003 |

## MVP — retrieval và Build

| ID | Priority / status | Mô tả và deliverable | Dependencies | Acceptance criteria | Docs / requirements |
|---|---|---|---|---|---|
| TASK-008 | P0 / Todo | Embedding adapter, versioned document/hash, CLI reindex và hybrid retrieval | TASK-005, TASK-007 | RRF deterministic; exact vector query; model/revision mismatch không dùng; keyword fallback khi embed fail; rebuild chỉ records thay đổi | [AI spec](../architecture/AI_RECOMMENDATION.md), [Data model](../architecture/DATA_MODEL.md); FR-005 |
| TASK-009 | P0 / Todo | Typed constraints và deterministic eligibility/budget evaluator | TASK-008 | Hard true/false/unknown tests; offline/local RAM; pricing/usage/freshness; tổng cost stack; pool thiếu thì xét toàn eligible catalog | [AI spec](../architecture/AI_RECOMMENDATION.md); FR-004/005, NFR-003 |
| TASK-010 | P0 / Todo | Structured extraction + capability mapping + generation orchestration endpoint dùng fake/live adapters | TASK-009, TASK-012 | Input/output models strict; clarification/no_match đúng invariants; provider calls bounded; protected auth dependency, fake identity chỉ trong test; live public usage đợi TASK-015/016 | [AI spec](../architecture/AI_RECOMMENDATION.md), [API](../architecture/API_DESIGN.md); FR-004/006/007 |
| TASK-011 | P0 / Todo | Grounding validator, rationale rendering, workflow checks, một repair và run persistence | TASK-010 | Unknown IDs/evidence sai/stale bị chặn; complete/partial chính xác; graph references hợp lệ; invalid repair trả 502; result TTL/private ownership; không lưu raw prompt | [AI spec](../architecture/AI_RECOMMENDATION.md); FR-006/007, NFR-003 |
| TASK-012 | P0 / Todo | Evaluation fixtures EV-01..16, gold roles/relevance, offline runner và report format | TASK-005 | Fixtures positive/negative tách seed; metric denominator/N/A rõ; deterministic mock output; report versioned, không gọi paid provider mặc định | [AI spec](../architecture/AI_RECOMMENDATION.md); FR-012 |
| TASK-013 | P0 / Todo | Builder UI nối generation API và display evidence/roles/gaps/workflow | TASK-011 | Bốn domain statuses và technical errors có UX; giữ input; disable duplicate submit; details link bằng DB ID; không render raw unvalidated prose | [Flows](../product/USER_FLOWS.md); FR-006/007/013 |
| TASK-014 | P0 / Todo | E2E Journey B với fake adapter và adversarial regression | TASK-012, TASK-013 | Clarification/partial/complete/no_match pass; prompt injection và catalog injection không vượt allowlist; 502/503/504 hiển thị đúng | [AI spec](../architecture/AI_RECOMMENDATION.md); FR-004..007 |
| TASK-015 | P0 / Todo | Quota, cost reservation/settlement, deadline và token caps | TASK-011 | Concurrent quota không vượt; thiếu tariff/budget không bật live; total deadline 30s kể cả repair; 429 + Retry-After; usage/cost tính đủ calls | [Architecture](../architecture/SYSTEM_ARCHITECTURE.md); NFR-002/004/006 |

## MVP — authentication và Save

| ID | Priority / status | Mô tả và deliverable | Dependencies | Acceptance criteria | Docs / requirements |
|---|---|---|---|---|---|
| TASK-016 | P0 / Todo | OIDC adapter/BFF session, API JWT verification, `/me`, login-return/logout | TASK-003 | Provider thật cấp đúng audience; expired/issuer sai bị chặn; CSRF/redirect allowlist; token không localStorage/log; login trước Build/Save | [Architecture](../architecture/SYSTEM_ARCHITECTURE.md), [API](../architecture/API_DESIGN.md); FR-008 |
| TASK-017 | P0 / Todo | Stack API create/list/get/delete, snapshot từ generation, idempotency | TASK-011, TASK-016 | Scoped owner; complete/partial mới save; expired→410; stale→409; key retry không duplicate; manual empty draft; delete version check | [API](../architecture/API_DESIGN.md); FR-009/010 |
| TASK-018 | P0 / Todo | Full PUT edit transaction, item replacement/edges, version conflict | TASK-017 | Two-tab race→409; bỏ item không còn dangling edge; thay role/tool/purpose invalidates claims; archived existing vẫn đọc được; rollback atomic | [Data model](../architecture/DATA_MODEL.md), [API](../architecture/API_DESIGN.md); FR-010, NFR-008 |
| TASK-019 | P0 / Todo | My Stack UI list/create/save/edit/delete nối API | TASK-013, TASK-018 | Save/reload giữ dữ liệu; empty state; confirm delete; conflict giữ draft; modified/stale warnings đúng; auth-return không mất draft trong session | [Flows](../product/USER_FLOWS.md); FR-009/010/013 |
| TASK-020 | P0 / Todo | E2E Journey C và authorization regression hai users; smoke A/B/C | TASK-014, TASK-015, TASK-019 | Không đọc/sửa/xóa/lưu generation của user khác; direct API tests; 3 journeys pass với test provider; live mode chỉ mở qua auth+budget | [PRD](../product/PRD.md); FR-008..010, NFR-004 |

## MVP — chất lượng và phát hành

| ID | Priority / status | Mô tả và deliverable | Dependencies | Acceptance criteria | Docs / requirements |
|---|---|---|---|---|---|
| TASK-021 | P1 / Todo | Structured logs/metrics, health/readiness, retention cleanup và privacy review | TASK-015, TASK-020 | Request ID trace được stages; logs không prompts/tokens/PII; TTL 24h/14d/30d như policy; purge run không mất saved snapshots; errors không lộ internals | [Architecture](../architecture/SYSTEM_ARCHITECTURE.md); FR-012, NFR-004/007 |
| TASK-022 | P1 / Todo | Live eval có budget, so keyword/hybrid, xử lý lỗi và report | TASK-012, TASK-020, TASK-021 | ≥30 runs với versions/sample size/cost; gates AI spec đạt hoặc release blocker rõ; report không biến N/A thành pass; regression sau fixes | [AI spec](../architecture/AI_RECOMMENDATION.md); FR-012, NFR-002/003/006 |
| TASK-023 | P1 / Todo | Mở rộng curated catalog từng batch 15→40–60→100–150 tools, review freshness/role coverage | TASK-005 | 100–150 published trước Done; mỗi record source/date và category; unknown rõ; đủ fixtures/live relevant tools cho scenarios, không synthetic data lẫn production | [PRD](../product/PRD.md), [Data model](../architecture/DATA_MODEL.md); FR-001/011 |
| TASK-024 | P1 / Todo | Performance/local RAM/accessibility/security checks và fixes | TASK-020, TASK-023 | Đo NFR-001/005 trên dataset đủ; keyboard/focus/contrast và 360px pass; auth/injection/limits regression; ghi môi trường, không chỉ assertion | [PRD](../product/PRD.md); NFR-001/004/005/009 |
| TASK-025 | P1 / Todo | Chọn hosting/region, CI build/staging, migration/backup/restore runbook, privacy notice | TASK-021, TASK-024 | OQ-004/006 chốt; deployment secrets đúng; staging smoke; thử restore thành công; rollback/schema compatibility documented | [Architecture](../architecture/SYSTEM_ARCHITECTURE.md); NFR-007/008 |
| TASK-026 | P1 / Todo | Re-run eval trên final catalog/staging; pilot và release readiness report | TASK-022, TASK-023, TASK-025 | Gates PRD/E2E/eval còn đạt trên final snapshot; pilot feedback ghi thật; không blocker journey/security; chủ dự án quyết định release | [PRD](../product/PRD.md), [Roadmap](ROADMAP.md); FR-001..013, NFR-001..009 |

TASK-023 có thể tiến hành theo batches cùng các mốc khác sau TASK-005, nhưng chỉ Done khi đủ data gate. TASK-016 có thể bắt đầu ngay sau schema; không cần chờ UI Builder. Thứ tự bảng không thay thế dependencies.

## Sau MVP — chưa lên lịch

| ID | Priority / status | Deliverable dự kiến | Dependencies | Acceptance trước khi lên lịch | Reference |
|---|---|---|---|---|---|
| FUT-001 | P2 / Deferred | AI Comparison theo facts có nguồn | TASK-026 | PRD bổ sung comparison criteria/UX và freshness semantics, không dùng điểm tổng hợp vô căn cứ | [PRD](../product/PRD.md) ngoài MVP |
| FUT-002 | P2 / Deferred | Workflow visualization, cân nhắc editor sau read-only view | TASK-026 | Có user need và graph/edit contract riêng; không mở scope MVP | [PRD](../product/PRD.md) ngoài MVP |

Không đưa payments, social, training hoặc multi-agent vào backlog đang thực hiện. Chỉ tạo task mới khi có nhu cầu và quyết định phạm vi.

## Cách bắt đầu một phiên làm việc

Đọc [AGENTS](../../AGENTS.md), chọn TASK-001 đầu tiên và giải quyết các quyết định theo thứ tự auth → provider/embedding → budget → curation. Dùng output là ADR cập nhật và checklist cấu hình, không tự triển khai ứng dụng trong task review baseline. Sau đó mới TASK-002.

Mẫu ghi evidence khi cập nhật task: `Ngày — thay đổi — lệnh/kiểm tra — kết quả — môi trường/fixture — hạn chế`. Không điền trước kết quả chưa chạy; task blocked phải ghi dependency hoặc thông tin cần, không đánh dấu Done để đi tiếp.
