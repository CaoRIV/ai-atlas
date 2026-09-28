# Product Requirements Document

Ngày: 28/09/2026 · Phiên bản: 0.1 · Trạng thái: baseline thiết kế, chưa triển khai.

## 1. Vấn đề và tầm nhìn

Người dùng cần chuyển từ một mục tiêu thực tế sang tập công cụ có thể sử dụng trong giới hạn thiết bị, ngân sách và kỹ năng. Một directory thiếu cấu trúc không thể chứng minh vì sao một tool phù hợp hoặc kết nối được với tool khác. AI Atlas kết hợp discovery và recommendation trên cùng catalog có provenance.

Chưa có nghiên cứu người dùng hoặc số liệu thị trường trong dự án. Các personas và ngưỡng thành công dưới đây là giả thuyết thiết kế cần kiểm chứng qua pilot.

## 2. Người dùng ưu tiên

| Persona giả định | Nhu cầu | Ràng buộc tiêu biểu | Giá trị cần kiểm chứng |
|---|---|---|---|
| Sinh viên học Applied AI | Làm chatbot PDF đầu tiên | Windows, 8GB RAM, miễn phí/chi phí thấp | Hiểu vai trò và giới hạn từng tool |
| Developer cá nhân | Chọn API và developer tools | Có API, budget tháng, thời gian tích hợp | Stack có căn cứ, ít thử sai |
| Content creator, sau MVP | Kết hợp tạo ảnh/video/audio | Chi phí, nền tảng, quy trình xuất dữ liệu | Tái sử dụng stack theo công việc |

Ưu tiên giải quyết tác vụ coding, research/learning và RAG. Không hứa rằng mọi mục tiêu trong catalog đều tạo được stack hoàn chỉnh.

## 3. Journeys và phạm vi

**Discover:** mở Explorer → tìm/lọc → xem chi tiết, nguồn và ngày xác minh → mở website chính thức.

**Build:** nhập mục tiêu → phân biệt hard constraints/preferences → nhận stack hoặc thông báo thiếu dữ liệu → đọc vai trò, evidence, workflow → xem catalog record.

**Save:** đăng nhập → lưu kết quả hoặc tạo stack thủ công → đổi tools/roles → mở lại stack của mình. Stack cá nhân là private trong MVP.

MVP có catalog 100–150 records biên tập; quản trị bằng file dữ liệu và CLI import, không cần admin UI. Cho phép Explorer anonymous; generation và lưu stack yêu cầu đăng nhập trong baseline đề xuất ADR-007 để kiểm soát chi phí. Cần chốt ADR này ở TASK-001 trước implementation phụ thuộc.

## 4. Functional requirements

| ID | Yêu cầu MVP | Tiêu chí nghiệm thu |
|---|---|---|
| FR-001 | Catalog phân biệt Tool/Model/Provider, nhiều categories và capabilities | 100–150 tools `published` khi release; slug duy nhất; mỗi tool có nguồn chính thức, description và verification date |
| FR-002 | Tìm theo từ khóa và lọc metadata | Query tên/description trả kết quả phân trang; nhiều category dùng OR trong cùng nhóm, AND giữa các nhóm filter; không có match trả danh sách rỗng |
| FR-003 | Trang tool có thông tin có cấu trúc | Hiển thị provider, categories/tags, capabilities, pricing, platforms, API, open-source, integrations, nguồn, ngày xác minh; trường chưa biết ghi rõ `unknown`; official URL mở được từ UI |
| FR-004 | Trích xuất mục tiêu và constraints | Phân biệt hard/soft/missing; constraints nhập trong form ưu tiên hơn suy luận từ prompt; mâu thuẫn trả clarification, không tự chọn một bên |
| FR-005 | Hybrid retrieval và lọc hard constraints | Kết hợp keyword/embedding theo [AI spec](../architecture/AI_RECOMMENDATION.md); unknown không được coi là thỏa hard constraint; toàn bộ IDs trả về thuộc catalog candidates |
| FR-006 | Đề xuất stack có vai trò và evidence | Kết quả có status, items, rationale, evidence IDs, gaps và workflow; claims giá/compatibility chỉ khi có evidence thích hợp; validator chặn IDs/claims sai |
| FR-007 | Xử lý thiếu dữ liệu và lỗi AI | Trả `partial`, `no_match`, `needs_clarification` theo contract; timeout/provider failure có lỗi rõ ràng; không giả kết quả thành công |
| FR-008 | Xác thực và quyền sở hữu | Backend xác minh identity; mọi stack route yêu cầu auth; user B không xem/sửa/xóa stack của A dù biết UUID |
| FR-009 | Lưu, liệt kê, đọc và xóa stack | Lưu kết quả với snapshot và reference tools; reload còn dữ liệu; delete xác nhận trên UI; request lặp do retry không tạo bản sao khi dùng idempotency key |
| FR-010 | Tạo thủ công và sửa stack | Đổi title/purpose, thêm/xóa/thay tool, đổi role/order; transaction cập nhật toàn bộ; phát hiện concurrent edit; sửa tay không được gắn nhãn đã AI kiểm chứng |
| FR-011 | Biên tập, import và kiểm chứng catalog | Dry-run chỉ ra lỗi trước ghi DB; import lặp theo stable ID không nhân bản; thay facts làm invalid evidence/embeddings liên quan; không public records draft/archived |
| FR-012 | Evaluation và observability cơ bản | Chạy bộ scenario cố định, xuất các metric theo AI spec; request ID nối logs với response; không log prompt cá nhân mặc định |
| FR-013 | Điều hướng và khả năng tiếp cận | Ba journey hoạt động bằng keyboard; loading/empty/error có thông báo; layout dùng được ở viewport 360px và desktop |

Không yêu cầu seed phải có thông tin giá hoặc API đã biết cho mọi tool. Record được publish với `unknown` nếu minh bạch; không eligible khi thuộc tính đó là hard constraint.

## 5. Non-functional requirements

Các ngưỡng là **release targets ban đầu**, phải ghi environment/dataset/cỡ mẫu khi đo.

| ID | Yêu cầu | Cách kiểm chứng |
|---|---|---|
| NFR-001 | API đọc catalog p95 ≤ 800ms phía server | 100 requests, concurrency 5, catalog 150 tools, môi trường staging đã ghi cấu hình; không tính cold start, báo cold start riêng |
| NFR-002 | Generation có timeout tổng 30s; p95 ≤ 20s là mục tiêu | Đo ≥ 30 live runs trên provider/model đã chọn; timeout trả lỗi, không treo UI; local fake-provider không chứng minh live latency |
| NFR-003 | Hard-constraint và identity validation fail closed | 100% kết quả được phát ra vượt validator; adversarial suite chặn unknown/ID ngoài catalog/owner sai; báo cả abstention rate để tránh đạt bằng cách từ chối mọi request |
| NFR-004 | Bảo vệ dữ liệu và secrets | Không secret trong client/repo/log; kiểm tra cross-user, token sai/hết hạn, SQL injection, prompt injection và rate limits |
| NFR-005 | Local phù hợp máy khoảng 8GB RAM | Chạy host frontend/backend, chỉ DB trong container; không local LLM; ghi peak memory và trải nghiệm 3 journeys trên máy mục tiêu trước release |
| NFR-006 | Chi phí AI hữu hạn | Token caps, quota và budget guard; mỗi run ghi usage và estimated cost khi có pricing config; giá không có thì cost `null`, không ghi 0 |
| NFR-007 | Có thể vận hành và phục hồi | Health/readiness, logs có request ID, DB backup và một lần restore thử thành công trước release |
| NFR-008 | Contract và dữ liệu nhất quán | Schema validation, FK/unique/check constraints, transaction khi sửa stack, migration test trên DB sạch; CI chặn lỗi |
| NFR-009 | Accessibility cơ bản | Kiểm tra keyboard, focus, label, thông báo lỗi và contrast theo checklist; không tuyên bố chứng nhận accessibility |

## 6. Ngoài MVP

AI Comparison nâng cao và interactive workflow editor được hoãn. Schema vẫn giữ facts riêng, stack roles và edges để hỗ trợ sau này. Các hạng mục multi-agent, training/fine-tuning, internet scraping diện rộng, giá realtime toàn cầu, reviews/ratings, leaderboards, social, marketplace/payments và subscriptions phức tạp không được đưa vào implementation MVP.

## 7. Đo thành công

- Engineering release gate: 3 journeys pass E2E; không còn lỗi chặn journey hoặc lỗ hổng ownership đã biết; đạt các gate evaluation trong [AI spec](../architecture/AI_RECOMMENDATION.md).
- Data gate: 100–150 published tools, 100% có source/date; mọi claim dùng cho hard constraints có evidence còn hiệu lực.
- Pilot đề xuất: ít nhất 5 người thuộc nhóm ưu tiên thử 3 tác vụ; mục tiêu ≥ 4 người hoàn thành Discover và Save không cần trợ giúp. Đây chưa phải kết quả nghiên cứu.
- Funnel cần đo có consent phù hợp: search → tool detail, build → kết quả hợp lệ, build → save; chỉ dùng event tối thiểu, không chứa raw prompt. Chưa đặt mục tiêu conversion khi chưa có baseline.
- Theo dõi `partial/no_match`, clarification, provider failure và cost/run; phân loại nguyên nhân data gaps trước khi đổi model.

## 8. Assumptions và câu hỏi mở

| ID | Giả định/điểm cần quyết định | Chủ trì, hạn chốt | Phương án tạm dùng |
|---|---|---|---|
| OQ-001 | LLM và embedding provider/model, region, retention? | Chủ dự án, TASK-001 | Adapter cấu hình; không chọn tên model hoặc giá chưa xác minh |
| OQ-002 | Identity provider, login method, generation có auth? | Chủ dự án, TASK-001 | OIDC + BFF session, login trước Build theo ADR-007 |
| OQ-003 | Ngân sách AI/infrastructure tối đa tháng? | Chủ dự án, TASK-001 | Live AI bị tắt đến khi có budget và tariff config |
| OQ-004 | Backend hosting và production region? | Chủ dự án, TASK-025 | Một backend instance + managed Postgres nếu ngân sách cho phép |
| OQ-005 | Có đủ evidence cho 100–150 tools trong 6 tuần? | Maintainer, TASK-005/TASK-023 | 15 records cho slice, 40–60 cho beta, 100–150 trước release |
| OQ-006 | Ngôn ngữ UI và policy dữ liệu? | Chủ dự án, TASK-001/TASK-025 | UI tiếng Việt, technical terms English; retention đề xuất tại architecture |

Nếu lịch không đủ, dời ngày release hoặc thống nhất sửa PRD; không âm thầm giảm chất lượng/độ phủ rồi gọi đó là MVP đã nghiệm thu.
