# REST API design

Thiết kế `/api/v1`, chưa có API chạy thật. Nguồn entities: [Data model](DATA_MODEL.md); recommendation result: [AI spec](AI_RECOMMENDATION.md). Contract này là baseline cho OpenAPI khi TASK-004/TASK-010 triển khai.

## 1. Quy ước chung

- JSON snake_case; UUID strings; timestamps RFC 3339 UTC; không tin ownership/verified flags do client gửi.
- Object response: `{"data": {...}, "request_id": "UUID"}`. List response: `{"data": [], "pagination": {"page": 1, "page_size": 20, "total": 0}, "request_id": "UUID"}`. Generation dùng envelope riêng như AI spec. `DELETE` 204 không body.
- Pagination `page >= 1`, `page_size=20` mặc định, tối đa 100; offset pagination đủ cho catalog nhỏ. Stable sort có UUID tie-break. Page vượt total trả data rỗng, không 404.
- Text input trim/Unicode normalize; unknown body/query keys bị từ chối 422 để tránh hiểu nhầm filter đã áp dụng. Không nhận SQL/order expression tùy ý.
- Auth là Bearer access token do identity provider đã cấu hình cấp. Browser authenticated gọi qua Next.js BFF dùng cookie/CSRF; FastAPI vẫn kiểm token. Public catalog không bắt buộc auth.
- Request ID do server tạo/chuẩn hóa và trả trong header `X-Request-ID` cùng body. Tất cả lỗi theo envelope bên dưới; 401 có challenge phù hợp; 429 có `Retry-After`.

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Dữ liệu đầu vào không hợp lệ.",
    "details": [{"field": "constraints.ram_gb", "reason": "must_be_positive"}]
  },
  "request_id": "50000000-0000-4000-8000-000000000001"
}
```

Common errors: 401 invalid/expired token; 403 account disabled; 404 resource absent/not owned; 422 invalid input; 429 quota; 500 internal error. Message không lộ SQL, secret, private resource hoặc raw provider output. `details` là array `{field,reason}`, có thể rỗng. Các status dưới đây bổ sung vào common errors.

## 2. Catalog routes

| Method/path | Auth | Request | Response và errors |
|---|---|---|---|
| `GET /api/v1/categories` | Không | Không có params | 200 list không pagination: `data:[{id,slug,name}]` |
| `GET /api/v1/tools` | Không | Query theo bảng dưới | 200 paginated ToolSummary; 422 filter sai |
| `GET /api/v1/tools/{tool_id}` | Không | UUID | 200 ToolDetail; 404 nếu draft/archived/không có; 422 UUID sai |
| `GET /api/v1/me` | Có | Không body | 200 `data:{id,display_name}`; 401 nếu chưa login |

| Filter tools | Kiểu/mặc định | Ngữ nghĩa |
|---|---|---|
| `q` | string 0–200 chars | Keyword name/description/tags; rỗng như omitted; Explorer không gọi LLM |
| `category` | comma-separated slugs, tối đa 8 | OR trong nhóm; slug không tồn tại → 422 |
| `platform` | enum web/windows/macos/linux/ios/android | Chỉ records có fact verified fresh chứa platform |
| `pricing_model` | enum free/freemium/paid/usage_based/contact/unknown | Unknown bao gồm fact null/unverified/stale; không ám chỉ tổng cost |
| `api_available` | boolean | true/false chỉ match fact có evidence fresh tương ứng, không match null |
| `open_source` | boolean | Cùng nguyên tắc true/false/null |
| `sort` | relevance/name/updated, mặc định relevance khi có q, name khi không | relevance cần q không rỗng; name tăng dần; updated giảm dần |
| `page`, `page_size` | int | Theo quy ước chung |

Giữa các nhóm filter dùng AND. Public catalog filter khác generation hard evaluator: platform web không tự đổi thành Windows; Builder xử lý execution context riêng. No results không phải server error.

ToolSummary gồm `id, slug, name, description, categories:[{id,slug,name}], pricing:{model,verification_status}, last_verified_at`. ToolDetail thêm `official_url`, `provider:{id,name}|null`, `tags`, `models:[{id,name}]`, `capabilities:[{key,name,evidence_ids}]`, `facts:[{key,value,verification_status,evidence_ids}]`, `evidence:[{id,fact_key,source_url,checked_at,expires_at}]`, `revision`, `warnings`. Stale facts vẫn hiển thị value với warning/verification_status unverified; không trình bày như confirmed. Không trả checked_by nội bộ hoặc unpublished notes.

Categories seed gồm Chatting & Assistants, Coding & Development, Image Generation & Editing, Video Generation & Editing, Audio & Speech, Research & Learning, Productivity & Automation, AI Agents. Slugs tương ứng `chatting-assistants`, `coding-development`, `image-generation-editing`, `video-generation-editing`, `audio-speech`, `research-learning`, `productivity-automation`, `ai-agents`.

## 3. Generation

### POST /api/v1/stack-generations

Auth: bắt buộc theo đề xuất ADR-007; chốt trước TASK-010. Body như [AI spec](AI_RECOMMENDATION.md): `objective` 10–4000 chars; `constraints` object optional; `preferences` array tối đa 10 enum values (`free_tier`, `beginner_friendly`, `open_source`, `fewer_tools`).

Constraint keys: `platform` theo enum tools; `ram_gb` > 0 và ≤ 1024; `deployment` cloud_allowed/local_only; `offline_required`, `api_required` booleans; `budget_usd_month` number ≥ 0; `monthly_usage` string 1–1000 chars. Mọi field constraints có thể null/omitted. Server parse monthly_usage trong extraction thành usage assumptions hiển thị cho user; không tự khẳng định số liệu user chưa cung cấp. Budget khác USD không được silently converted.

200 trả `{generation_id,result,usage,request_id}`; result schema và status invariants theo AI spec. Usage gồm `input_tokens`, `output_tokens`, `estimated_cost_usd`, `pricing_version`; tokens cộng các text calls; embedding usage ghi riêng trong internal run metadata và tính vào estimated cost. Không trả raw chain-of-thought, system prompt hoặc catalog credentials.

Errors: 409 `CATALOG_CHANGED`; 422 input sai; 429 `QUOTA_EXCEEDED`/`BUDGET_EXCEEDED`; 502 `INVALID_MODEL_OUTPUT`; 503 `AI_UNAVAILABLE`/`AI_NOT_CONFIGURED`; 504 `AI_TIMEOUT`. Domain thiếu candidates trả 200 no_match, không 404/500. Backend có thể ghi failed run metadata nhưng không trả invalid result.

Generation là synchronous, không có polling/jobs API trong MVP. Disable double-submit trên UI. Không tự retry POST khi network outcome không rõ; retry do user khởi tạo có thể tính quota/cost lần nữa, cần thông báo. `generation_id` dùng lưu stack trong 24h; không có public result URL.

## 4. Stack resources

| Method/path | Auth | Body/query | Response và errors |
|---|---|---|---|
| `GET /api/v1/stacks` | Có | page, page_size; sort mặc định updated desc, không filter owner | 200 paginated StackSummary, chỉ current user |
| `POST /api/v1/stacks` | Có | Discriminated body generated/manual bên dưới; optional `Idempotency-Key: UUID` | 201 StackDetail; replay cùng key/body 200; 409 key conflict/tool unavailable; 410 generation expired |
| `GET /api/v1/stacks/{stack_id}` | Có | UUID | 200 StackDetail; 404 absent/not owned |
| `PUT /api/v1/stacks/{stack_id}` | Có | Full editable representation + expected_version | 200 StackDetail version mới; 409 stale version hoặc tool unavailable |
| `DELETE /api/v1/stacks/{stack_id}` | Có | `expected_version` query int ≥ 1 | 204; 404 absent/not owned; 409 stale version |

StackSummary: `id,title,purpose,item_count,validation_state,version,created_at,updated_at`. StackDetail thêm `items`, `workflow`, `generation_snapshot`, `warnings`; owner không cần public field vì tất cả scoped current user.

Item response: `{item_id,tool_id,role,position,rationale,evidence_ids,tool_snapshot}`; tool_snapshot tối thiểu `{name,slug,official_url,revision,claims,evidence}` do server dựng từ catalog hoặc validated generation. Edge response theo WorkflowEdge ở AI spec. `generation_snapshot` chứa result gốc cùng pipeline/catalog versions; không biến snapshot thành tuyên bố freshness hiện tại.

### Tạo từ generation

```json
{
  "source": "generation",
  "generation_id": "30000000-0000-4000-8000-000000000001",
  "title": "Chatbot PDF thử nghiệm"
}
```

Server đọc private run thuộc user; chỉ cho save complete/partial còn result trong TTL. Run không thuộc user/không có → 404; hết TTL → 410; no_match/needs_clarification/failed → 422 `UNSAVEABLE_RESULT`. Purpose lấy objective_summary, items/claims lấy validated snapshot, không nhận tùy ý client. Evidence hết hạn hoặc tool không còn published từ lúc generate → 409 `GENERATION_STALE`, yêu cầu generate lại hoặc tạo manual. Kiểm tra constraints/revisions một lần nữa trước save.

### Tạo thủ công

```json
{
  "source": "manual",
  "title": "Bộ công cụ học tập",
  "purpose": "Thử nghiệm quy trình đọc tài liệu",
  "items": [],
  "workflow": []
}
```

Manual/update editable item: `{item_id:UUID,tool_id:UUID,role:string,position:int}`; client tạo item UUID để tham chiếu trong workflow nhưng server xác minh uniqueness và ownership. Editable edge: `{from_item_id,to_item_id,description}`; manual edge luôn unverified và evidence rỗng. Không cho client nhập rationale/claims/verification flags. IDs mới không được trùng item thuộc stack khác; trả 422 chung, không tiết lộ stack đó.

### Sửa toàn bộ phần editable

```json
{
  "expected_version": 1,
  "title": "Bộ công cụ học tập",
  "purpose": "Thử nghiệm quy trình đọc tài liệu",
  "items": [],
  "workflow": []
}
```

Validation: title 1–120 chars; purpose 1–2000; items 0–20; role 1–80; positions liên tục từ 1; edges ≤ 40; không duplicate item_id/position; endpoints cùng stack; edges theo thứ tự tăng, không self-loop. New/replacement tools phải published; giữ item cũ archived được phép và có warning. Bỏ item phải bỏ edges tương ứng hoặc server loại trong transaction và phản ánh response; baseline chọn server tự loại dangling edges do item bị xóa, nhưng reject endpoints chưa từng có trong request/stack.

PUT trong một transaction, so expected_version rồi tăng version. Thay purpose/items/workflow chuyển generated thành modified; manual vẫn manual. Server giữ evidence cho item/edge không đổi; thay tool/role xóa rationale/claims liên quan, reset edges liên quan thành unverified. Sửa title đơn thuần giữ validation_state. Response phản ánh bản canonical, UI thay local state bằng response.

Idempotency của create: scoped `(owner_id,key)`, lưu canonical body hash trong stack row; cùng key/body trả resource hiện có, body khác trả 409. Unique constraint + transaction xử lý concurrent retry. Key tồn tại suốt vòng đời stack; sau delete không bảo đảm replay, UI không tự retry tạo bản đã xóa. Client nên luôn dùng key cho save button.

## 5. Auth và endpoint vận hành

Login/callback/logout thuộc Next.js/auth adapter, không tự xây `/password` endpoints trong FastAPI. OIDC details chốt TASK-001; mọi frontend/backend contract liên quan token phải test thật ở TASK-016 trước nghiệm thu Save. Logout là POST có CSRF, không GET mutation.

`GET /health/live`: 200 `{"status":"ok"}` khi process sống. `GET /health/ready`: 200 ready hoặc 503 khi DB/schema chưa sẵn sàng; không expose DB credentials/version chi tiết hoặc gọi provider trả phí. Không có public import/admin endpoints; curated import qua CLI có DB credential riêng được bảo vệ.

## 6. Contract test bắt buộc

Happy paths và error envelope, pagination ổn định, unknown filters, null vs false, archived records; generation enums/schema và invalid provider output; cross-user run/stack read/write/delete; create idempotency cùng/khác body; PUT version race/atomic rollback; deletion edges; generation TTL; stale evidence; JWT invalid issuer/audience/expiry; quota/budget atomicity. Ví dụ UUID trong docs là fixtures, không IDs production hoặc dữ liệu đã tồn tại.
