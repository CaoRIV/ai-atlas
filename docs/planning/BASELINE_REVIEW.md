# TASK-001 — Baseline đã chốt và bàn giao

Ngày: 28/09/2026. Phạm vi: review tài liệu và quyết định cấu hình; chưa triển khai ứng dụng. Nguồn: [PRD](../product/PRD.md), [ADR](DECISIONS.md), [Architecture](../architecture/SYSTEM_ARCHITECTURE.md), [AI spec](../architecture/AI_RECOMMENDATION.md).

## Quyết định của chủ dự án

| Hạng mục | Kết quả | ADR / giới hạn |
|---|---|---|
| Auth | Auth0 Free + Google Login; OIDC/BFF; Explorer public, Build/Save cần login | ADR-007 Accepted. “Auth Free” được hiểu là Auth0 Free theo phương án đang thảo luận; chưa tạo tenant |
| LLM | gemini-3.5-flash-lite qua Gemini Developer API | ADR-011/012 Accepted; model access thực tế chưa test |
| Embedding | gemini-embedding-2, output_dimensionality=1536 | ADR-012; migration pin vector(1536), query/document cùng model space |
| Budget | Chưa ước lượng vì đang test; ngân sách deploy chốt sau | Không phê duyệt đề xuất 10 USD/tháng. Fake mode; live AI bị khóa khi chưa có budget/tier/tariff/guards |
| Curation | Curated files + CLI, verify nguồn thủ công, dry-run/atomic import | ADR-008 Accepted; triển khai TASK-005 |
| UI | English và tiếng Việt | ADR-012; UI controls/states có en/vi; nội dung catalog/user/AI giữ nguyên ngôn ngữ gốc |

Quy ước UI ban đầu: mặc định vi, selector English / Tiếng Việt, lưu browser preference; đổi locale không mất filters/draft. Không thêm locale vào API hoặc dịch factual claims trong task này. PRD FR-013, design và backlog đã mang yêu cầu song ngữ sang các task frontend.

## Acceptance TASK-001

| Tiêu chí gốc | Evidence / kết luận |
|---|---|
| OQ-001/002/003 có quyết định hoặc blocker cụ thể | Provider/model/D/API offering/auth đã chốt; budget/tier/region/retention chưa có được ghi bên dưới |
| Tariff/source/date khi chọn live provider | Bảng tariff và nguồn chính thức phía dưới, kiểm tra 28/09/2026; chưa phải cấu hình runtime hoặc quyền chi tiêu |
| ADR-007/008 có trạng thái đúng | Accepted theo xác nhận chủ dự án; ADR-011 giữ lịch sử provider, ADR-012 bổ sung model/UI/test |
| Không bật live AI khi chưa budget | Không có code hoặc live calls; architecture/AI spec giữ fail-closed; TASK-002 chỉ scaffold fake mode |

TASK-001 hoàn tất phần review theo tiêu chí cho phép ghi blocker. Điều này không nghiệm thu M0 runtime hoặc live readiness. TASK-002 có thể bắt đầu khi được giao; các bước live phải chờ giải quyết blockers tương ứng.

## Checklist cấu hình cho TASK-002

- Pin dependency versions và kiểm tra Windows/DB trong TASK-002; ADR-009 vẫn Proposed cho tới kiểm tra môi trường. ADR-010 chốt tại TASK-003.
- DATABASE_URL; OIDC_ISSUER/AUDIENCE/CLIENT_ID/CLIENT_SECRET; SESSION_SECRET: env placeholders, không credentials trong docs/client.
- LLM_PROVIDER và EMBEDDING_PROVIDER: Google Gemini; LLM_MODEL=gemini-3.5-flash-lite; EMBEDDING_MODEL=gemini-embedding-2; EMBEDDING_DIM=1536. Tên adapter key cụ thể pin khi scaffold; fake adapter không gọi network AI.
- AI_MONTHLY_BUDGET_USD chưa đặt; không suy ra unlimited hoặc free. Secrets LLM_API_KEY theo env server, không prefix public.
- Giữ caps AI spec và tối đa một repair/30s; tính đủ thinking tokens trong billable output. Quota 5 requests/10 phút và 30/ngày/user vẫn là default đề xuất cần chốt trước live.
- Health web/API/DB, CI/offline checks và commands tái hiện thuộc TASK-002, chưa chạy trong review này.

## Blockers được chuyển sang giai đoạn phù hợp

| Blocker | Chủ trì / hạn gỡ | Tác động |
|---|---|---|
| Budget live test, quota, Gemini free/paid tier | Chủ dự án trước lần gọi Gemini thật đầu tiên, kể cả embedding/reindex | Không bật live; dùng fake fixtures cho phát triển/CI. “Chỉ test” không tự miễn yêu cầu budget |
| Quyền truy cập model, region/retention của Google project | Chủ dự án + implementer trước live; privacy production TASK-025 | Không coi chọn model là bằng chứng khả dụng tài khoản hoặc data residency |
| Auth0 tenant/region, Google OAuth credentials, audience/JWKS/logout | TASK-016 trước authenticated live flow | Có thể scaffold placeholders; chưa tuyên bố login hoạt động |
| Hosting, budget production, backup/retention/privacy notice | Chủ dự án tại TASK-025, trước staging/deploy | Không triển khai cloud ngoài scope |

Ngân sách là hạn mức chi tiêu được phép, không cần bằng dự đoán hóa đơn chính xác. Có thể quyết định hạn mức test riêng khi cần; chưa bắt chủ dự án ước lượng production để scaffold.

## Evidence kiểm tra

Đã đối chiếu PRD/ADR/API/architecture/data model/flows/design và backlog. Kiểm tra liên kết, whitespace và trạng thái acceptance được chạy sau cập nhật; kết quả ghi tại TASKS. Không có code, migration, unit/integration/E2E hoặc live eval ở task tài liệu; không tạo tài khoản, gọi API trả phí, commit/push/deploy.

## Dịch vụ và tariff tham khảo — tra cứu ngày 28/09/2026

### Baseline đã chốt và giới hạn

| Thành phần | Cấu hình | Căn cứ và giới hạn |
|---|---|---|
| Identity | Auth0 Free, Google Login qua Universal Login; tenant Japan nếu tài khoản cho phép | Free công bố tối đa 25.000 monthly active users [S1]; hỗ trợ Google connection [S2], custom API JWT với audience riêng [S3] và region Japan [S4]. Cần cấu hình Google OAuth credentials riêng trước production, kiểm tra issuer/audience/JWKS thật trong TASK-016 |
| LLM extraction/generation/repair | Đã chốt `gemini-3.5-flash-lite` qua Gemini Developer API | Có Structured Outputs và thinking [S5]; adapter phải tính cả thinking tokens trong cost và giới hạn output. Chưa claim quality/latency đạt eval |
| Embedding | Đã chốt `gemini-embedding-2`, `EMBEDDING_DIM=1536` | Đặt `output_dimensionality=1536` rõ ràng vì default là 3072 [S6]. Chỉ dùng text cho catalog MVP; version cả document/query formatting và đo Recall@5 |
| Local database | PostgreSQL + pgvector qua Docker Compose | Giữ baseline dự án; chưa thuê cloud DB. Host chạy web/API để giới hạn tài nguyên; RAM thực tế đo ở task sau |
| Ngân sách giai đoạn local | Chưa ước lượng ngân sách theo chủ dự án; fake mode mặc định; không tự điền 10 USD/tháng hoặc ngân sách 0 như đã duyệt | Hạn mức test phải chốt trước live, budget deploy trước TASK-025; không suy ra free tier cho Gemini từ Auth0 Free |

Dùng chung Google Gemini cho LLM và embedding theo quyết định chủ dự án. Gemini Developer API đã được chủ dự án chốt; Vertex AI không thuộc baseline hiện tại. Fake mode vẫn mặc định; không tự chuyển sang model khác khi lỗi vì thay model có thể thay cost/quality. Auth0 đã duyệt; mức ngân sách 10 USD/tháng trước đó không áp dụng.

### Tariff đề xuất để cấu hình sau phê duyệt

Tariff reference version: `proposal-2026-09-28-gemini-standard-v1`. Currency USD; đơn vị 1.000.000 tokens; giá Gemini Developer API standard paid cho text, không giả định cache hit hoặc Batch discount; không áp dụng giá này cho Vertex AI.

| Model | Input | Cached input | Output | Nguồn |
|---|---:|---:|---:|---|
| gemini-3.5-flash-lite | 0,30 USD | Không áp dụng trong estimate | 2,50 USD, gồm thinking tokens | [S7] |
| gemini-embedding-2 (text) | 0,20 USD | Không áp dụng trong estimate | Không áp dụng | [S7] |

Ví dụ giả định tổng mỗi lượt Build gồm tất cả text calls là 10.000 input tokens + 2.000 billable output tokens (đã gồm thinking), cùng 1.000 embedding tokens: `10000/1000000*0.30 + 2000/1000000*2.50 + 1000/1000000*0.20 = 0.0082 USD/lượt`; 1.000 lượt khoảng 8,20 USD. Đây chỉ là ví dụ, không phải usage đo được hay upper bound. Repair, reindex, eval, retry và thuế có thể tăng chi phí. Admission phải reserve đủ input/output/thinking theo caps thực tế và đối soát usage, không chỉ đếm text hiển thị.

### Dữ liệu và phần chưa chốt

Gemini Developer API có policy khác nhau giữa unpaid và paid services [S8]. Bảng giá ghi free tier dùng dữ liệu để cải thiện sản phẩm, paid tier không [S7]; cần đối chiếu điều khoản áp dụng theo tài khoản/khu vực trước live. Đề xuất chỉ thử synthetic/public data ở free tier, dùng paid tier cho nội dung người dùng. Chưa xác minh retention/region thực tế của project; không cam kết Zero Data Retention hoặc dữ liệu nằm ở Việt Nam/Japan. TTL 24h của AI Atlas không thay retention provider.

Auth0 Japan mới là region đề xuất; chưa tạo tenant hoặc xác minh retention tài khoản/logs/backups theo cấu hình. Production privacy notice và hosting vẫn thuộc TASK-025. Chưa có kiểm chứng quyền gọi model trên tài khoản người dùng.

### Lịch sử lựa chọn

Đề xuất OpenAI trước đó được thay bằng Google Gemini theo chỉ dẫn chủ dự án ngày 28/09/2026. Không có code hoặc vector đã tạo nên chưa cần migration/re-embed. Chọn model stable được tài liệu hiện hành liệt kê; kiểm tra lại lifecycle khi triển khai [S10].

Hosting cloud vẫn chốt ở TASK-025 khi biết tải và budget deploy. Auth0 và model cụ thể đã được chốt ở lần xác nhận tiếp theo; ngân sách và live calls chưa được duyệt.

### Nguồn chính thức

- [S1 — Auth0 pricing](https://auth0.com/pricing)
- [S2 — Google Login](https://auth0.com/docs/authenticate/identity-providers/social-identity-providers/google)
- [S3 — Custom API access token và audience](https://auth0.com/docs/secure/tokens/access-tokens/get-access-tokens)
- [S4 — Auth0 tenant regions](https://auth0.com/docs/get-started/auth0-overview/create-tenants)
- [S5 — Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [S6 — Gemini embeddings và dimension](https://ai.google.dev/gemini-api/docs/embeddings)
- [S7 — Gemini pricing và data use](https://ai.google.dev/gemini-api/docs/pricing)
- [S8 — Gemini API terms](https://ai.google.dev/gemini-api/terms)
- [S10 — Gemini lifecycle và access](https://ai.google.dev/gemini-api/docs/deprecations)
