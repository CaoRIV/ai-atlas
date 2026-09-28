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
- **Consequences:** Phụ thuộc mạng, cost, retention và provider latency; cần budget guard, transport-isolated tests và live eval có giới hạn. Provider cụ thể được chốt sau tại ADR-011/012.

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

- **Status:** Accepted, 28/09/2026; chủ dự án chọn Auth0 Free + Google Login.
- **Context:** Save cần ownership; API AI cần hạn chế abuse và chi phí. Provider identity đã chọn: Auth0 Free; login bằng Google.
- **Decision:** Auth0 OIDC + Google Login, session cookie tại Next.js BFF, Bearer token được FastAPI xác minh; Explorer public, Build và My Stack yêu cầu auth.
- **Rationale:** Không tự triển khai password security, có identity để quota và private generation results.
- **Alternatives:** Anonymous Build với IP quota/captcha; backend-managed password login; browser giữ access token.
- **Consequences:** Tăng ma sát Build; cần token audience/JWKS/session/CSRF thật. Nếu chọn anonymous Build phải cập nhật PRD, flows, API, ownership và abuse control trước code.

## ADR-008 — Curated files và import CLI

- **Status:** Accepted, 28/09/2026; chủ dự án chốt curated files + CLI, thực hiện TASK-005.
- **Context:** 100–150 tools cần chất lượng hơn số lượng; chưa có nhu cầu admin dashboard.
- **Decision:** Maintainer biên tập file, verify nguồn thủ công, dry-run rồi atomic import; reindex bằng CLI.
- **Rationale:** Review/version-control được, tránh xây admin UI/crawler sớm.
- **Alternatives:** Admin web app, tự scrape, sửa DB thủ công không validation.
- **Consequences:** Tốn thời gian biên tập, cần hướng dẫn import/freshness. Catalog data không được giả là verified chỉ vì có URL.

## ADR-009 — Modular monolith, local host processes

- **Status:** Accepted, 28/09/2026; được kiểm tra trong TASK-002 trên Windows với host processes và database Compose.
- **Context:** Solo developer và RAM khoảng 8GB không phù hợp hạ tầng phân tán nặng.
- **Decision:** Một backend instance chia modules; Next.js/backend chạy trên host local, DB container; synchronous generation 30s; DB-backed quota/budget reservation. Foundation pin Node.js 22 + pnpm, Python 3.11 + uv và PostgreSQL 17/pgvector 0.8.6.
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

## ADR-011 — Google Gemini cho LLM và embedding

- **Status:** Accepted, 28/09/2026; phạm vi quyết định là provider.
- **Bổ sung sau đó:** ADR-012 chốt model/dimension/API offering và UI. Phần consequences bên dưới ghi trạng thái tại thời điểm chỉ chọn provider, không phải blocker model hiện tại.
- **Context:** Chủ dự án chọn Google Gemini cho cả LLM và embedding trong TASK-001.
- **Decision:** Dùng Google Gemini cho hai adapters AI, bổ sung lựa chọn cụ thể cho ADR-003; domain contracts vẫn độc lập provider.
- **Consequences:** Đề xuất OpenAI trước đó không còn áp dụng. Model, dimension, API offering (Gemini Developer API hay Vertex AI), tier, region/retention và budget chưa được chủ dự án chốt. Xem [Baseline review](BASELINE_REVIEW.md) để review cấu hình đề xuất; live AI tiếp tục bị khóa khi chưa đủ budget/tariff/guards.

## ADR-012 — Model, chế độ test và UI song ngữ

- **Status:** Accepted, 28/09/2026; bổ sung ADR-011 theo quyết định mới của chủ dự án.
- **Decision:** Gemini Developer API; LLM `gemini-3.5-flash-lite`; embedding `gemini-embedding-2` với `output_dimensionality=1536`. Pin model key, dimension và pipeline version; schema dùng `vector(1536)`.
- **Budget:** Chủ dự án chấp nhận chi phí Gemini thực tế cho development/test dựa trên kinh nghiệm với các sản phẩm AI trước; chưa đặt monthly estimate. Ngân sách deployment chốt trước TASK-025 và guard runtime triển khai ở TASK-015. Không áp dụng đề xuất 10 USD/tháng trước đó. Unit/CI không gọi Gemini; live smoke bắt buộc có API key và opt-in rõ ràng, dùng tariff/usage thật.
- **UI:** Hỗ trợ English (`en`) và tiếng Việt (`vi`) cho navigation, controls, trạng thái và thông báo. Technical identifiers giữ nguyên. Nội dung catalog, evidence, user input và AI result giữ ngôn ngữ gốc; không tự dịch factual claims. Locale chỉ là UI preference, chưa thêm field/endpoint backend. Mặc định `vi`, có chọn `English / Tiếng Việt` và lưu preference trên browser là quy ước triển khai ban đầu, có thể điều chỉnh khi làm frontend.
- **Consequences:** TASK-002 triển khai Gemini adapter thật, không có fake provider; tests dùng injected transport/response fixtures và live smoke opt-in. TASK-006/013/019 cần copy đủ hai locale, kiểm tra đổi ngôn ngữ không mất filters/draft. Chất lượng AI và production budget chưa được nghiệm thu.

## Các lựa chọn còn mở sau TASK-001 review

Review TASK-001 ngày 28/09/2026: [quyết định và checklist cấu hình](BASELINE_REVIEW.md). Auth0/curation đã chốt ở ADR-007/008; provider/model/UI ở ADR-011/012. Chủ dự án cho phép development/test phát sinh chi phí Gemini thật; production budget/tier/region/retention vẫn phải chốt trước staging. ADR-009 đã chốt trong TASK-002; ADR-010 vẫn thuộc TASK-003.

Còn mở: tenant Auth0/region thực tế, Gemini tier/region/retention, hosting/budget/retention production. Exact dependency versions của foundation đã pin trong lockfiles; nâng cấp phải chạy lại lint/type/unit/build/integration. Lịch sử ADR-011 chỉ chốt provider; ADR-012 bổ sung model/dimension đã duyệt. Theo dõi OQ-001 đến OQ-006 tại [PRD](../product/PRD.md).
