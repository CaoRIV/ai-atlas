# Architecture decisions

Ngày lập: 28/09/2026. `Accepted` nghĩa baseline kiến trúc đã được yêu cầu trong brief, không phải tính năng đã triển khai. `Proposed` là lựa chọn thiết kế cần chốt trước task phụ thuộc. Nếu đổi quyết định Accepted, thêm ADR thay thế với lý do; không sửa lịch sử như thể chưa có quyết định cũ.

## ADR-001 — Next.js và FastAPI

- **Status:** Accepted.
- **Context:** UI directory/stack và AI backend cần contracts rõ, nhóm nhỏ ưu tiên công cụ thông dụng theo brief.
- **Decision:** Next.js + TypeScript + Tailwind CSS cho frontend; FastAPI + Pydantic cho backend.
- **Rationale:** TypeScript hỗ trợ UI có kiểu, Python phù hợp pipeline/evaluation; schema backend kiểm tra trust boundaries.
- **Alternatives:** Next.js full-stack, Django monolith, SPA + API khác.
- **Consequences:** Hai runtime/toolchains; cần contract tests/OpenAPI để tránh lệch types. Không duplicate business rules ở BFF.

## ADR-002 — PostgreSQL và pgvector

- **Status:** Accepted.
- **Context:** Catalog quan hệ, private stacks và embeddings cần thống nhất identity/provenance.
- **Decision:** Một PostgreSQL database có pgvector; keyword và vector retrieval trong cùng data boundary.
- **Rationale:** Quy mô 100–150 tools không cần search cluster hoặc vector DB riêng.
- **Alternatives:** PostgreSQL + external vector database; Elasticsearch; chỉ keyword.
- **Consequences:** Cần hosting hỗ trợ extension và pin embedding dimension. Exact vector scan là baseline; ANN chỉ bổ sung khi có số đo.

## ADR-003 — AI qua API, adapter có thể thay đổi

- **Status:** Accepted.
- **Context:** Máy Windows khoảng 8GB RAM, ngân sách hạn chế; không cần training/local LLM.
- **Decision:** LLM extraction/generation và embeddings qua API; adapter chuẩn hóa schema/usage/errors; model/provider cấu hình được.
- **Rationale:** Giảm tài nguyên local; có thể đánh giá provider sau mà không đổi domain contracts.
- **Alternatives:** Local inference, fine-tuning, khóa trực tiếp SDK provider vào domain.
- **Consequences:** Phụ thuộc mạng, cost, retention và provider latency; cần budget guard, fake adapter và live eval có giới hạn. Provider cụ thể vẫn mở.

## ADR-004 — Documentation-first và scoped tasks

- **Status:** Accepted.
- **Context:** Các coding agents cần persistent context và thứ tự thực hiện nhất quán.
- **Decision:** PRD → technical contracts/ADRs → roadmap → scoped backlog → implementation/test → cập nhật docs.
- **Rationale:** Giảm rewrite, tránh features vượt MVP và claims chưa được kiểm tra.
- **Alternatives:** Code trước rồi viết docs; một prompt dài không chia nguồn sự thật.
- **Consequences:** Tốn công duy trì docs theo contract. Không để docs Done khiến task implementation bị đánh dấu Done theo.

## ADR-005 — Unified catalog, tách Tool/Model/Provider

- **Status:** Accepted.
- **Context:** Directory và recommendation phải dùng cùng IDs và facts; một tool có thể dùng nhiều models/categories.
- **Decision:** Entities riêng và relationship tables cần thiết; provenance theo từng fact, stable UUID; saved stacks tham chiếu tools kèm snapshot.
- **Rationale:** Không nhầm model thành ứng dụng; facts có thể dùng cho comparison sau này; cập nhật catalog không làm mất ngữ cảnh saved stack.
- **Alternatives:** Một bảng tên AI chung; hai catalog riêng cho Explorer và Builder; unstructured blobs thuần túy.
- **Consequences:** Import/schema chặt hơn; cần revision/freshness và validation cho fact keys. Không tạo ecosystem graph đầy đủ trong MVP.

## ADR-006 — Một recommendation pipeline trước multi-agent

- **Status:** Accepted.
- **Context:** Nhiệm vụ chủ yếu là retrieval, constraints và explanations; cần đo lỗi/cost theo stage.
- **Decision:** Pipeline hữu hạn extract → capability → retrieve → filter → generate → validate, tối đa một repair.
- **Rationale:** Dễ debug, đánh giá và kiểm soát deadline hơn autonomous agents.
- **Alternatives:** Multi-agent orchestration, chain không validation, recommendation chỉ từ model knowledge.
- **Consequences:** Không tự research internet, execute workflow hoặc có vòng lặp tự chủ. Thiếu dữ liệu phải abstain/partial rõ ràng.

## ADR-007 — OIDC/BFF và login trước generation

- **Status:** Proposed; chốt TASK-001 trước TASK-010/TASK-016.
- **Context:** Save cần ownership; API AI cần hạn chế abuse và chi phí. Chưa có provider identity được chọn.
- **Decision đề xuất:** OIDC provider, session cookie tại Next.js BFF, Bearer token được FastAPI xác minh; Explorer public, Build và My Stack yêu cầu auth.
- **Rationale:** Không tự triển khai password security, có identity để quota và private generation results.
- **Alternatives:** Anonymous Build với IP quota/captcha; backend-managed password login; browser giữ access token.
- **Consequences:** Tăng ma sát Build; cần token audience/JWKS/session/CSRF thật. Nếu chọn anonymous Build phải cập nhật PRD, flows, API, ownership và abuse control trước code.

## ADR-008 — Curated files và import CLI

- **Status:** Proposed; chốt TASK-001, thực hiện TASK-005.
- **Context:** 100–150 tools cần chất lượng hơn số lượng; chưa có nhu cầu admin dashboard.
- **Decision đề xuất:** Maintainer biên tập file, verify nguồn thủ công, dry-run rồi atomic import; reindex bằng CLI.
- **Rationale:** Review/version-control được, tránh xây admin UI/crawler sớm.
- **Alternatives:** Admin web app, tự scrape, sửa DB thủ công không validation.
- **Consequences:** Tốn thời gian biên tập, cần hướng dẫn import/freshness. Catalog data không được giả là verified chỉ vì có URL.

## ADR-009 — Modular monolith, local host processes

- **Status:** Proposed; chốt TASK-002 sau kiểm tra môi trường.
- **Context:** Solo developer và RAM khoảng 8GB không phù hợp hạ tầng phân tán nặng.
- **Decision đề xuất:** Một backend instance chia modules; Next.js/backend chạy trên host local, DB container; synchronous generation 30s; DB-backed quota/budget reservation.
- **Rationale:** Ít service, dễ debug, không Redis/queue/Kubernetes.
- **Alternatives:** All-in-Docker mặc định, serverless mọi bước, async worker/microservices.
- **Consequences:** Không job resume dài hạn, throughput ban đầu hạn chế. Scale-out cần admission/concurrency strategy và benchmark mới. Hosting chưa được quyết định.

## ADR-010 — Typed facts và evidence freshness

- **Status:** Proposed; chốt TASK-003 dựa trên fixtures và query review.
- **Context:** Boolean thiếu dữ liệu không thể coi như false; price/integration thay đổi độc lập record.
- **Decision đề xuất:** Fact values typed theo vocabulary, evidence gắn fact revision, TTL theo loại, unknown fail closed ở hard constraints; rationale từ validated claims.
- **Rationale:** Chặn giá/capabilities bịa hoặc stale, giữ kiến trúc comparison-compatible.
- **Alternatives:** Chỉ last_verified_at cấp tool; mọi fact là text description; hoàn toàn để LLM judge grounding.
- **Consequences:** Nhiều validation hơn và một số request phải no_match. TTL 30/90 ngày là policy cần đánh giá lại, không số liệu thị trường. Tài liệu [Data model](../architecture/DATA_MODEL.md) quy định chi tiết.

## Các lựa chọn chưa quyết định

LLM/embedding model và dimension, exact dependency versions, identity provider, hosting/region, ngân sách, retention production. Theo dõi OQ-001 đến OQ-006 tại [PRD](../product/PRD.md). Chốt lựa chọn bằng evidence phù hợp ở thời điểm triển khai; bộ spec hiện không yêu cầu mua dịch vụ hoặc cài dependencies.
