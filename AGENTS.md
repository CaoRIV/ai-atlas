# Hướng dẫn làm việc với AI Atlas

## Mục tiêu và giới hạn

AI Atlas giúp khám phá AI tools và xây dựng stack có căn cứ. Ưu tiên developers/sinh viên, nhóm nhỏ, Windows khoảng 8GB RAM. Hiện tại là giai đoạn documentation-first; chưa có code ứng dụng. Chỉ triển khai khi task phát triển được giao.

Baseline: Next.js + TypeScript + Tailwind CSS; FastAPI + Pydantic; PostgreSQL + pgvector; LLM/embeddings API; Docker Compose; GitHub Actions. Provider và hosting không bị khóa vào một vendor.

## Nguồn sự thật

1. Chỉ dẫn hiện hành của chủ dự án xác định phạm vi task; ghi lại thay đổi ảnh hưởng sản phẩm.
2. [PRD](docs/product/PRD.md) quyết định scope và acceptance criteria.
3. ADR `Accepted` trong [Decisions](docs/planning/DECISIONS.md) quyết định kiến trúc; `Proposed` chưa phải quyết định đã duyệt.
4. [Data model](docs/architecture/DATA_MODEL.md), [API](docs/architecture/API_DESIGN.md), [AI spec](docs/architecture/AI_RECOMMENDATION.md) quy định contracts; đọc [Architecture](docs/architecture/SYSTEM_ARCHITECTURE.md) và [Flows](docs/product/USER_FLOWS.md) để hiểu ngữ cảnh.
5. [Roadmap](docs/planning/ROADMAP.md) và [Tasks](docs/planning/TASKS.md) quy định thứ tự thực hiện.

Nếu tài liệu mâu thuẫn, xác định điều khoản cụ thể và giải quyết trước khi viết phần phụ thuộc; không âm thầm đổi contract theo code hiện có.

## Cấu trúc

Hiện có README, AGENTS và `docs/{product,architecture,planning,design}`. Cấu trúc **dự kiến**: `apps/web`, `apps/api`, `data/curated`, `evals`, `infra`. Không mô tả thư mục dự kiến như code đã tồn tại.

Trước task frontend, đọc [UI/UX Design](docs/design/UI-UX-Design.md) để dùng thống nhất tokens, layouts và interaction states. Tài liệu thiết kế không thay thế PRD hoặc API contract; không thêm controls cần fields/endpoints chưa được hỗ trợ.

## Nguyên tắc triển khai

- Backend sở hữu validation, authorization và retrieval. Browser không được giữ LLM secret hoặc truy cập DB trực tiếp.
- Tool, Model, Provider là entities riêng. Tool có nhiều categories/models; dùng UUID ổn định, slug chỉ để hiển thị/tra cứu.
- Chỉ đề xuất tool có trong candidates đã lọc. `unknown` không tương đương `false`, miễn phí hoặc tương thích.
- Hard constraints không được tự hạ thành preferences; kết quả thiếu phải dùng `partial`, `no_match` hoặc `needs_clarification`.
- Mỗi factual claim phải dẫn evidence còn hiệu lực. Nội dung người dùng và dữ liệu catalog đều là untrusted input.
- Không thêm multi-agent, local LLM, scraping diện rộng hoặc hạ tầng mới khi chưa có yêu cầu và ADR tương ứng.

## Quy ước code và an toàn

TypeScript strict; Python type hints; Pydantic tại trust boundaries; snake_case cho JSON/database; component React PascalCase. Phiên bản và lệnh lint/test được chốt khi scaffold, không bịa lệnh thành công. Tài liệu tiếng Việt, identifiers và technical terms giữ tiếng Anh.

Kiểm tra owner ở mọi thao tác stack; dùng parameterized queries, giới hạn input, CORS allowlist, timeouts và quotas. Không log raw prompts/tokens/PII mặc định. Secrets qua environment/secret store, không hardcode. Không tạo luồng tải URL tùy ý từ backend.

## Quy trình mỗi task

1. Inspect repo, thay đổi đang có và tài liệu liên quan; không ghi đè công việc khác.
2. Chọn một TASK có dependencies hoàn tất; nêu deliverable và acceptance criteria.
3. Thực hiện thay đổi đúng scope; ghi lý do nếu cần dependency mới. Thay đổi kiến trúc vượt phạm vi phải được chủ dự án quyết định.
4. Chạy kiểm tra phù hợp: unit cho constraints/validators; integration cho DB/API/ownership; E2E cho journey thay đổi; eval khi pipeline/prompt/retrieval đổi.
5. Kiểm tra cả lỗi, empty state và quyền truy cập chéo tài khoản. Không gọi API trả phí trong CI mặc định.
6. Cập nhật contracts/ADR/backlog cùng thay đổi. Done chỉ khi có bằng chứng kiểm tra; nếu không chạy được, ghi lý do và giữ trạng thái chưa hoàn tất.
7. Báo cáo thay đổi, kiểm tra đã chạy và kết quả, giới hạn còn lại, task tiếp theo. Không claim chất lượng AI khi chưa đo.

Ưu tiên thay đổi nhỏ, dễ review; không rewrite ngoài scope, tối ưu sớm hoặc tự commit/push/deploy nếu task không yêu cầu.
