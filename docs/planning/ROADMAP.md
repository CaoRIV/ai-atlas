# Roadmap MVP — 6 tuần

Đây là ước lượng cho một developer có khoảng 20–25 giờ/tuần, đang học Applied AI/AI Engineering. Dành khoảng 20% thời gian cho học, debugging và rework. Không có cam kết release theo ngày khi chưa đo tốc độ tuần đầu. Các task chưa triển khai; xem [Tasks](TASKS.md).

## Nguyên tắc sắp xếp

Mỗi mốc tạo một hành vi dùng được từ UI đến database/API. Hoàn thành Explorer slice sớm; đưa fake-provider Builder vào trước live tuning; thêm auth production trước mở generation thật. Không làm toàn bộ frontend rồi mới backend. Data curation bắt đầu sớm và tiếp tục mỗi tuần.

Nếu chỉ có 4 tuần, mục tiêu khả thi là internal beta 40–60 tools và 3 journeys, không gọi đó là release đạt toàn bộ PRD. Muốn release đủ 100–150 tools và các quality gates cần giữ tuần 5–6 hoặc điều chỉnh lịch theo tốc độ thực tế.

## M0 — Chốt baseline và scaffold, đầu tuần 1

- **Mục tiêu:** loại bỏ blockers provider/auth/budget và có môi trường chạy/test được.
- **Deliverables:** TASK-001, TASK-002; ADR decisions, versions đã pin, `.env.example`, local setup/CI skeleton.
- **Dependencies:** bộ spec hiện tại; chủ dự án chốt các lựa chọn bắt buộc.
- **Acceptance:** local web/API health và DB kết nối được; fake provider chạy không cần paid key; secret không lọt client; ghi commands thực tế.
- **Rủi ro:** Docker/WSL RAM, OIDC audience không phù hợp. Thử cấu hình nhỏ, xử lý trước khi phát triển auth-dependent flow.
- **DoD:** setup tái lập được, ADR trạng thái đúng, task có bằng chứng kiểm tra. Không coi scaffolding là feature hoàn thành.

## M1 — Discover vertical slice, cuối tuần 1

- **Mục tiêu:** người dùng mở một tool thực từ database qua Explorer UI.
- **Deliverables:** TASK-003 đến TASK-007; schema/import tối thiểu, 15 curated tools, search/filter/detail và smoke test Journey A.
- **Dependencies:** M0; schema/provenance đã nhất quán.
- **Acceptance:** empty/error states hoạt động; tool nhiều categories không duplicate; unknown hiển thị đúng; official source/date có thật ở curated records; schema trên DB sạch chạy được.
- **Rủi ro:** metadata quá phức tạp; chỉ triển khai vocabulary trong spec, không thêm generic knowledge graph.
- **DoD:** một lát cắt end-to-end chạy được, không chỉ mocked UI; PRD FR-001 chưa được coi hoàn tất về số lượng 100–150 tools.

## M2 — Dữ liệu và retrieval, tuần 2

- **Mục tiêu:** dữ liệu có thể tìm theo capability và lọc constraints bằng code.
- **Deliverables:** TASK-008, TASK-009, TASK-012 khởi tạo eval fixtures; tiếp tục TASK-023 tới 40–60 tools dùng cho beta.
- **Dependencies:** M1; provider/dimension chốt ở TASK-001, fixtures từ TASK-005.
- **Acceptance:** keyword baseline và hybrid có report Recall@5; unknown/stale không pass hard filter; index rebuild phát hiện revision; chưa cần UI AI hoàn thiện.
- **Rủi ro:** curation là bottleneck, Vietnamese query retrieval kém. Ưu tiên coverage roles developers/students, đo trước khi đổi embedding model.
- **DoD:** retrieval tests và deterministic constraint tests pass; dữ liệu verified có evidence, records thiếu facts để unknown.

## M3 — Build vertical slice, tuần 3

- **Mục tiêu:** nhập mục tiêu và nhận complete/partial/no_match/clarification có căn cứ trên UI.
- **Deliverables:** TASK-010, TASK-011, TASK-013, TASK-014, TASK-015; bắt đầu TASK-016 để mở authenticated live flow.
- **Dependencies:** M2; output schema và evaluation fixtures.
- **Acceptance:** fake-provider E2E đi qua backend validation; live mode chỉ bật với auth/quota/budget guards; invalid IDs, stale evidence, prompt injection bị chặn; workflow unverified có nhãn.
- **Rủi ro:** provider output thất thường, latency/cost. Giữ một repair, context caps; lỗi technical trả error chứ không giả no_match.
- **DoD:** Journey B offline kiểm chứng; nếu chưa auth/live eval thì ghi rõ chưa đạt live release gate, không mở public endpoint tạm không auth.

## M4 — Save vertical slice, tuần 4

- **Mục tiêu:** đăng nhập thật, lưu/chỉnh/tải lại stack private.
- **Deliverables:** TASK-016 đến TASK-020; private CRUD, snapshots, idempotency/versioning và E2E ba journeys.
- **Dependencies:** M3 contracts; identity provider hoạt động; DB owner relationships.
- **Acceptance:** hai tài khoản không truy cập chéo; duplicate save với key không tạo bản sao; tab sửa cũ nhận 409; modified stack không giữ nhãn verified sai.
- **Rủi ro:** auth integration và concurrent edits. Không tự xây password system; test API ngoài UI để xác nhận authorization.
- **DoD:** 3 journeys chạy nội bộ; blockers security/data integrity đã xử lý. Đây là internal beta, chưa phải release đủ data/eval.

## M5 — Quality và operational readiness, tuần 5

- **Mục tiêu:** đo hệ thống thật, xử lý failure modes và giới hạn chi phí.
- **Deliverables:** TASK-021, TASK-022; TASK-023 tiếp tục; UI accessibility, telemetry/cleanup, live eval report và fixes.
- **Dependencies:** M4; budget cho live eval được chốt.
- **Acceptance:** đo đầy đủ [AI metrics](../architecture/AI_RECOMMENDATION.md); mọi emitted identity/constraint/schema valid; logs không raw prompts/secrets; 429/timeout/503 có test.
- **Rủi ro:** live quality không đạt. Phân loại retrieval/data/generation, sửa nguyên nhân; không thay metric để che thất bại.
- **DoD:** regression suite pass; report có sample size, versions, cost; chỗ chưa đạt gate có blocker rõ, không đánh dấu Done release.

## M6 — Data completion, pilot và release candidate, tuần 6

- **Mục tiêu:** đủ catalog và vận hành có thể kiểm tra/phục hồi.
- **Deliverables:** TASK-023 đến TASK-026; 100–150 published tools, performance/RAM evidence, staging/runbook, backup restore test, pilot feedback.
- **Dependencies:** M5; hosting/region/privacy choices chốt trước staging.
- **Acceptance:** source/date 100%; stale hard facts không được dùng; E2E sau deployment; restore đã thử; pilot không còn lỗi chặn 3 journeys.
- **Rủi ro:** thiếu giờ curation hoặc provider quota. Dời release khi cần; không fabricate verification dates hoặc giảm gate ngầm.
- **DoD:** toàn bộ release gates PRD có evidence và chủ dự án quyết định phát hành. TASK-026 không tự cấp quyền deploy trong lần soạn spec này.

## Definition of Done dùng chung

Scope/acceptance task đạt; checks liên quan đã chạy với kết quả được ghi; lỗi ownership/constraint/schema không còn; docs cập nhật đúng contract; không secrets; reviewer/chủ dự án có thể tái hiện. Fake-provider test không thay live AI evaluation, design review không thay integration test.

Hàng tuần kiểm tra task blocked, tốc độ và curation count; điều chỉnh tuần tiếp theo dựa trên số liệu. Sau MVP mới xét comparison/workflow visualization; multi-agent không là bước tiếp theo mặc định.
