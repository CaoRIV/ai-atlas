# AI Atlas — Discover, Compare & Build Your AI Stack

> Discover AI. Build your stack.

AI Atlas là nền tảng khám phá AI tools và xây dựng AI stack theo mục tiêu, thiết bị và ngân sách của người dùng. Sản phẩm kết nối một thư viện được biên tập với hệ thống đề xuất có căn cứ, giúp trả lời: có công cụ nào, công cụ nào phù hợp và chúng kết hợp thành quy trình như thế nào?

**Trạng thái ngày 09/10/2026:** TASK-001..006 Done; TASK-007 đang triển khai, 007.1–007.4 Done. Home/Explorer/tool detail dùng Catalog API thật. Frontend gần nhất 35 tests, ESLint/typecheck/build pass; 72 matrix + 7 state axe scans không có violations, 3 state results đã review thủ công. Playwright runner dựng PostgreSQL tạm đã migrate/import đúng 202 records, FastAPI, Next production và Chromium bằng một command; 8 Journey A cases chạy thành GitHub Actions gate cho PR và push vào `develop`/`main`, có bounded timeout, failure artifacts và teardown luôn chạy. Xem [commands, evidence và giới hạn](docs/operations/DISCOVER_VERIFICATION.md). Backend gần nhất 208 unit + 84 integration từ TASK-005.6.

## Vấn đề và người dùng

Danh sách liên kết đơn thuần chưa giúp người dùng đánh giá giới hạn, chi phí và khả năng kết hợp công cụ. AI Atlas ưu tiên developers và sinh viên học lập trình/AI; sau MVP có thể mở rộng cho content creators và người làm việc văn phòng.

## MVP dự kiến

- **AI Explorer:** tìm kiếm, lọc và đọc thông tin 100–150 tools được biên tập, có nguồn và ngày kiểm chứng.
- **AI Stack Builder:** chuyển mô tả mục tiêu thành các vai trò cần thiết, chọn tools từ database, giải thích có bằng chứng và trả workflow dạng văn bản.
- **My AI Stack:** đăng nhập, lưu, tạo thủ công, thay thế hoặc xóa tools và truy cập lại stack cá nhân.
- Quản trị dữ liệu bằng quy trình import/validate dành cho maintainer; evaluation và observability cơ bản.

So sánh nâng cao, workflow editor tương tác, multi-agent, scraping diện rộng, thanh toán và social features nằm ngoài MVP. Tên sản phẩm thể hiện cả tầm nhìn dài hạn; Compare chưa phải tính năng đã có.

## Công nghệ và kiến trúc

Next.js, TypeScript, Tailwind CSS cho frontend; Python, FastAPI, Pydantic cho backend; PostgreSQL và pgvector cho dữ liệu và retrieval. Runtime AI dùng Gemini Developer API qua adapter backend. Docker Compose chạy database local, GitHub Actions chạy checks; hosting chưa chốt.

```mermaid
flowchart LR
    U[Người dùng] --> W[Next.js]
    W --> A[FastAPI]
    A --> D[(PostgreSQL và pgvector)]
    A --> L[LLM và Embedding API]
    W --> I[Identity provider]
    A --> I
```

Backend sở hữu business rules, kiểm tra quyền và recommendation validation. Không dùng semantic similarity để kết luận compatibility. Không cần local LLM, Redis, Kafka hay Kubernetes trong MVP.

## Đọc tài liệu theo thứ tự

| Thứ tự | Tài liệu | Mục đích |
|---|---|---|
| 1 | [AGENTS.md](AGENTS.md) | Quy tắc làm việc và nguồn sự thật |
| 2 | [PRD](docs/product/PRD.md) | Yêu cầu và tiêu chí nghiệm thu |
| 3 | [User flows](docs/product/USER_FLOWS.md) | Hành trình, trạng thái và lỗi |
| 4 | [System architecture](docs/architecture/SYSTEM_ARCHITECTURE.md) | Thành phần và ranh giới trách nhiệm |
| 5 | [Data model](docs/architecture/DATA_MODEL.md) | Entities, provenance, ownership |
| 6 | [AI recommendation](docs/architecture/AI_RECOMMENDATION.md) | Retrieval, grounding và evaluation |
| 7 | [API design](docs/architecture/API_DESIGN.md) | Hợp đồng frontend/backend |
| 8 | [Decisions](docs/planning/DECISIONS.md) | Quyết định đã chấp nhận và đề xuất |
| 9 | [Roadmap](docs/planning/ROADMAP.md) | Mốc triển khai trong 6 tuần |
| 10 | [Tasks](docs/planning/TASKS.md) | Backlog, phụ thuộc và trạng thái |
| 11 | [UI/UX Design](docs/design/UI-UX-Design.md) | Design tokens, màn hình, responsive và interaction states; đọc trước task frontend |

## Lộ trình

Tuần 1 hoàn thành một lát cắt Explorer từ database đến UI; tuần 2 hoàn thiện dữ liệu và retrieval; tuần 3 đưa Stack Builder qua validation; tuần 4 hoàn tất đăng nhập và lưu stack; tuần 5 đánh giá và gia cố; tuần 6 bổ sung dữ liệu, sửa lỗi và thử triển khai. Đây là ước lượng cho một người, có thể giãn theo năng lực và thời gian học.

## Toolchain đã pin

| Thành phần | Phiên bản |
|---|---|
| Node.js | `22.23.3` trong `.node-version`; hỗ trợ `>=22.16 <23` |
| pnpm | `12.6.0` |
| Next.js / React | `16.3.6` / `19.3.0` |
| TypeScript / Tailwind CSS | `6.0.3` / `4.3.3` |
| Radix Dialog / Lucide React | `1.1.23` / `1.49.0` |
| Python | `3.11` |
| uv | `0.9.28` |
| FastAPI / Pydantic | `0.141.1` / `2.13.5` |
| google-genai | `2.23.0` |
| PostgreSQL / pgvector image | PostgreSQL 17 / `pgvector/pgvector:0.8.6-pg17-bookworm` |

TypeScript 6 được giữ vì toolchain ESLint của Next.js chưa hỗ trợ TypeScript 7. Lockfiles `pnpm-lock.yaml` và `uv.lock` là nguồn dependency tái lập.

## Chạy local trên Windows

Yêu cầu: Node.js 22, Corepack, `uv`, Docker Desktop và PowerShell. Script setup dùng pnpm/Python cache trong workspace, cài dependencies theo lockfile và chỉ tạo `.env` từ `.env.example` khi file chưa tồn tại.

```powershell
.\scripts\setup.ps1
docker compose up --detach --wait db
```

Nếu cổng `5432` đã được dùng, chọn cổng khác trước khi chạy Compose và cập nhật `DATABASE_URL` trong `.env`:

```powershell
$env:POSTGRES_PORT = "55432"
docker compose up --detach --wait db
```

Nếu Docker API chưa sẵn sàng, mở Docker Desktop và đợi engine khởi động rồi chạy lại. Không cần npm global: `scripts/pnpm.ps1` tải đúng pnpm 12.6.0 qua Corepack và tránh phụ thuộc npm trên máy.

Áp dụng versioned SQL migrations trước khi chạy API. Đặt `DATABASE_URL` theo cổng PostgreSQL thực tế:

```powershell
$env:DATABASE_URL = "postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:5432/ai_atlas"
uv run python apps/api/src/ai_atlas_api/migrations.py up
uv run python apps/api/src/ai_atlas_api/migrations.py status
```

Rollback yêu cầu target tường minh. Lệnh sau xóa toàn bộ schema do migrations quản lý nên chỉ dùng trên database test riêng:

```powershell
uv run python apps/api/src/ai_atlas_api/migrations.py down --to 0
```

Chạy API và web trong hai terminal. `API_BASE_URL` là server-only origin của FastAPI; không đổi thành biến `NEXT_PUBLIC_*`:

```powershell
# Terminal 1
uv run uvicorn ai_atlas_api.main:app --app-dir apps/api/src --reload --port 8000

# Terminal 2
$env:API_BASE_URL = "http://127.0.0.1:8000"
$env:CATALOG_API_TIMEOUT_MS = "10000"
.\scripts\pnpm.ps1 --filter @ai-atlas/web dev
```

Các probe có sẵn:

- Web: `GET http://127.0.0.1:3000/api/health`
- API process: `GET http://127.0.0.1:8000/health/live`
- API dependencies: `GET http://127.0.0.1:8000/health/ready`; trả `503` nếu database chưa cấu hình, không kết nối được hoặc thiếu extension `vector`

## Kiểm tra

Chạy lint, strict typecheck, unit tests và production build không gọi Gemini:

```powershell
.\scripts\check.ps1
```

Với database Compose đang healthy, chạy integration tests. Migration tests tự tạo và xóa database tạm, không sửa schema trong database được cấu hình bởi `DATABASE_URL`:

```powershell
$env:DATABASE_URL = "postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:5432/ai_atlas"
uv run pytest -m integration
```

Live smoke dùng Gemini thật, tạo một structured generation và một embedding. Lệnh này phát sinh usage/chi phí thật, chỉ chạy khi đã đặt cả key lẫn opt-in:

```powershell
$env:GEMINI_API_KEY = "<your-key>"
$env:RUN_LIVE_AI_TESTS = "1"
uv run pytest -m live -s
```

Dừng database nhưng giữ dữ liệu bằng `docker compose down`. Chỉ khi chủ động cần database sạch cho integration/migration test mới dùng lệnh sau; nó xóa volume `ai-atlas_ai_atlas_postgres_data` cùng toàn bộ dữ liệu local trong volume:

```powershell
docker compose down --volumes
```

Không có runtime fake provider. Unit/CI inject SDK client response tại boundary của adapter; workflow CI không đặt `GEMINI_API_KEY` và loại marker `live`. Gemini key, OIDC secrets và session secret chỉ tồn tại ở server environment, không dùng biến `NEXT_PUBLIC_*`.

TASK-001..006 đã Done; TASK-006 hoàn tất ngày 05/10/2026. TASK-007 là bước tiếp theo trong Discover slice; TASK-016 cũng đủ dependency. Không dán key vào chat hoặc commit. Trạng thái và evidence đầy đủ nằm trong [backlog](docs/planning/TASKS.md).

## Catalog API

Sau khi apply migrations và khởi động API, xem OpenAPI tại `http://127.0.0.1:8000/openapi.json` hoặc Swagger UI tại `http://127.0.0.1:8000/docs`. Public routes:

- `GET /api/v1/categories`
- `GET /api/v1/tools?q=keyword&category=coding-development&api_available=true&page=1&page_size=20`
- `GET /api/v1/tools/{tool_id}` (UUID)

Database chưa có curated seed thì list trả rỗng; category slug chưa tồn tại trả 422. TASK-005 cung cấp 8 categories và 15 tools có nguồn; import tường minh theo [operating guide](docs/operations/CURATED_CATALOG.md). Filter true/false chỉ nhận facts verified với evidence cùng revision còn hạn; detail hiển thị stale facts dưới trạng thái unverified. Query key lạ hoặc parameter lặp trả 422, draft/archived detail trả 404, DB chưa sẵn sàng trả 503. Chi tiết response và filters ở [API contract](docs/architecture/API_DESIGN.md).

Review fixes TASK-004: model relation chỉ hiển thị khi model-use fact verified fresh và value true; fact verified false vẫn giữ nguồn nhưng không công bố model. HTTP error envelope giữ exception headers, gồm `Allow: GET` cho 405, cùng request ID. Hai regression cases, 49 unit tests, 46 integration tests và smoke HTTP thật đã pass tại TASK-004; evidence lịch sử trong backlog. Curated importer/seed đã hoàn tất ở TASK-005.

## Frontend Catalog boundary — TASK-006.1

Next.js cung cấp ba allowlisted same-origin read routes; browser không gọi FastAPI trực tiếp:

- `GET /api/catalog/categories`
- `GET /api/catalog/tools` — giữ nguyên query để FastAPI validate
- `GET /api/catalog/tools/{tool_id}`

Gateway chỉ đọc server-side `API_BASE_URL`, không dùng `NEXT_PUBLIC_*`, CORS, generic proxy hoặc direct database access. `CATALOG_API_TIMEOUT_MS` mặc định 10000 và chỉ nhận 1000–30000 ms. Response stream giữ HTTP status, safe headers và `X-Request-ID`; cache bị tắt. Upstream/config/timeout failure trả 503 `CATALOG_UNAVAILABLE` đã sanitize, không fallback mock. Browser client parse success/error envelopes bằng Zod trước khi UI sử dụng.

Verification 006.1 ngày 01/10/2026: **6 behavior tests mới, full 8 web tests**, ESLint và strict typecheck pass; production build compile/type/static generation pass. Actual smoke dùng PostgreSQL tạm đã migrate/import 202 records, Uvicorn và Next dev thật: 8 categories, search ChatGPT total 1, detail HTTPS, invalid tools/category query giữ 422 + request ID, route ngoài allowlist 404, upstream dừng trả sanitized 503. Temporary DB/services/build cache đã xóa; development catalog không đổi, không gọi Gemini hoặc source URLs.

## Frontend UI foundation — TASK-006.2

App shell dùng toàn bộ semantic color tokens cho dark/light, lưu preference `Tối / Sáng / Theo hệ thống` và chạy bootstrap script trong `<head>` trước paint. Desktop từ 1280px dùng sidebar 216px; viewport nhỏ hơn dùng sticky header và Radix Dialog drawer có focus trap, Escape và focus return. Navigation liên kết hai route đang hoạt động `/` và `/explorer`; current route có marker + `aria-current`. Skip link, header/nav/main landmarks, locale vi/en, hit target 44px, reduced-motion và forced-colors states nằm trong cùng shell. Lucide là icon family duy nhất, stroke 1.75; icon trang trí dùng `aria-hidden`.

Verification 006.2 ngày 01/10/2026: **3 behavior tests mới, full 10 web tests**, ESLint, strict typecheck và production build pass. Browser smoke thật chứng minh stored light theme đã áp dụng ở frame đầu, System đổi dark→light theo OS, locale/theme dùng keyboard, drawer trap/restore focus và skip link focus main. Reflow 320px không overflow; breakpoint 1279px dùng header/drawer và 1280px dùng sidebar; drawer controls đều cao 44px. Axe desktop và mobile đóng drawer báo 0 violations/0 incomplete. Không gọi Catalog API, database, Gemini hoặc source URL.

## Frontend Home discovery — TASK-006.3

Home gọi `GET /api/catalog/categories` và `GET /api/catalog/tools?page=1&page_size=6&sort=name` qua typed same-origin client. Search trim input rồi điều hướng `/explorer?q=...`; category dùng `/explorer?category=...`. ToolCard chỉ đọc `ToolSummary`: monogram, description tối đa hai dòng, tối đa hai category + `+N`, pricing label theo verification status và detail URL bằng UUID. Không hiển thị popularity, rating, logo, giá tiền hoặc result count không có trong response.

Categories và tools có loading, empty và sanitized error riêng; lỗi giữ `request_id` trong disclosure và retry đúng section, không fallback mock. Home sinh destination URL cho Explorer đã hoạt động; `/tools/[tool_id]` vẫn thuộc 006.6 nên detail link hiện chưa có UI.

Verification 006.3 ngày 01/10/2026: **3 behavior tests mới, full 13 web tests**, ESLint, strict typecheck và production build pass. Actual Chromium + PostgreSQL tạm đã migrate/import 202 records: 8 categories; 6 cards Adobe Firefly/ChatGPT/Claude/Cursor/ElevenLabs/Gemini; exact request `page=1&page_size=6&sort=name`; loading skeleton 6 cards; vi→en; search Unicode URL; upstream dừng hiện hai sanitized errors/request IDs, restart + retry phục hồi 8/6. Mobile 360px một cột, không overflow; axe 0 violations/0 incomplete. Temporary DB/services/build cache đã xóa; development catalog không đổi, không gọi Gemini hoặc source URLs.

## Frontend Explorer orchestration — TASK-006.4

`/explorer` dùng typed URL state cho `q`, `category`, `platform`, `pricing_model`, `api_available`, `open_source`, `sort` và `page`; request Catalog luôn cố định `page_size=20`. Query và filter change reset page; relevance chỉ tồn tại khi q khác rỗng, còn mặc định không query là name. Search trim + Unicode NFC, debounce 300 ms sau `compositionend` bằng history replace; Enter push ngay và không phát sinh debounce trễ. Back/forward dựng lại input/applied state từ URL.

Mỗi URL/retry có request key riêng. Effect hủy request cũ bằng `AbortController` và sequence guard ngăn promise cũ ghi đè kết quả mới kể cả transport không chịu abort. Explorer có active shell route, result total từ API, sort name/updated/relevance hợp lệ, ToolCard grid, pagination, loading/empty/error + retry. Filter controls/chips/drawer và giữ old grid khi refresh thuộc 006.5; direct filter URLs đã gọi đúng Catalog contract.

Verification 006.4 ngày 02/10/2026: **6 behavior cases mới, full 19 web tests**, ESLint, strict typecheck và production build pass. Actual Chromium + PostgreSQL seeded 15 tools: default 15 results, exact request `sort=name&page=1&page_size=20`; search ChatGPT debounce dùng replace và trả 1 result; Enter sang Claude ngay; back phục hồi URL/input/result ChatGPT; direct category/API URL áp state; relevance chỉ hiện khi có q. Mobile 360px không overflow, empty state thật và axe 0 violations/0 incomplete. Abort khi đổi URL được quan sát và regression test chứng minh response cũ không render. Services/build cache tạm đã xóa; không gọi Gemini hoặc source URLs.

## Frontend Explorer interactions — TASK-006.5

Desktop dùng filter rail áp dụng ngay; mobile/tablet dùng Radix draft drawer với Apply/Cancel/Escape, reset draft và focus return. Applied chips có accessible name theo keyword, xóa từng filter bằng keyboard; count trên nút không tính q/sort/page. Category multi-select dùng OR trong nhóm; các nhóm dùng AND. Chọn “Tất cả” xóa boolean parameter thay vì gửi false; filter false vẫn là lựa chọn riêng. Grid responsive 3/2/1 cột, pagination giữ total/page từ API và không có horizontal overflow ở 360px.

Refresh giữ grid cũ với aria-busy=true và live status cho tới khi request mới hoàn tất. Initial load dùng skeleton; empty state xóa cả search/filter; lỗi 422 có reset về Explorer mặc định; HTTP error giữ query cùng request ID và retry đúng request. Không có client-side filtering hoặc preview count từ dữ liệu cũ.

Verification 006.5 ngày 03/10/2026: **6 behavior cases mới, full 25 web tests**, ESLint, strict typecheck và production build pass. Seeded FastAPI/Next/Chromium smoke dùng 15 tools: desktop filter category trả 2 results; refresh category + platform giữ 2 cards cũ trong lúc aria-busy, rồi empty; invalid category 422 reset về 15 results. Mobile 360px chứng minh Cancel bỏ draft, Apply commit một lần, focus trả nút “Bộ lọc”, chip/count đúng, 2 cards và không overflow. Axe mobile/desktop báo 0 violations/0 incomplete; settled browser không có console/page errors. Không gọi Gemini hoặc source URLs.

Kiểm thử TASK-004 trên Windows có cache cũ bị ACL có thể dùng các lệnh đã chạy sau (DATABASE_URL trỏ DB local; tests tạo rồi xóa database tạm, không seed vào database chính):

```powershell
.venv/Scripts/python.exe -m ruff check --no-cache apps/api
.venv/Scripts/python.exe -m ruff format --check --no-cache apps/api
.venv/Scripts/python.exe -m mypy --cache-dir .cache/mypy-task004
.venv/Scripts/python.exe -m pytest -p no:cacheprovider -m "not integration and not live"
.venv/Scripts/python.exe -m pytest -p no:cacheprovider -m integration
```

## Curated format — TASK-005.1

[Format và metadata ownership](docs/architecture/DATA_MODEL.md#8-curated-json-format--task-0051) được triển khai bằng Pydantic strict trong `apps/api/src/ai_atlas_api/curated_models.py`. `data/curated/taxonomy.json` có 8 categories và 15 capability definitions với UUID cố định; không chứa synthetic tools hoặc tool claims chưa xác minh. JSON Schema lấy qua `CuratedCatalog.model_json_schema()`.

Đọc/validate vocabulary hiện có từ repo root (không ghi DB hoặc gọi API):

```powershell
.venv/Scripts/python.exe -X utf8 -c "import sys; from pathlib import Path; sys.path.insert(0, 'apps/api/src'); from ai_atlas_api.curated_models import CuratedCatalog; catalog = CuratedCatalog.model_validate_json(Path('data/curated/taxonomy.json').read_bytes()); print('schema_version=', catalog.schema_version, 'categories=', len(catalog.categories), 'capabilities=', len(catalog.capabilities), 'tools=', len(catalog.tools))"
.venv/Scripts/python.exe -m pytest -p no:cacheprovider apps/api/tests/unit/test_curated_models.py
```

TASK-005.1..005.6 và TASK-005 tổng đã Done; xem operating guide bên dưới. Schema parsing 005.1, semantic validation 005.2, dry-run/diff 005.3, atomic import 005.4 và curated seed 15 tools 005.5 đã tách rõ. Seed chưa tự động import vào development DB. Unit/fixtures synthetic tách khỏi curated data. Verification 005.1: 60 schema cases và schema/vocabulary smoke pass; evidence đầy đủ trong backlog. Không gọi Gemini.

## Curated semantic validation — TASK-005.2

`apps/api/src/ai_atlas_api/curated_validation.py` kiểm tra whole-batch references/uniqueness, source syntax, TTL/time bounds, publication/identity và capability/model relations. `curated_snapshot.py` đọc DB ở chế độ read-only để bảo toàn fact/evidence ownership và chặn nguồn cũ chứng minh value/revision mới. Chi tiết [validation contract](docs/architecture/DATA_MODEL.md#9-semantic-import-validation--task-0052).

Kiểm tra taxonomy với catalog rỗng (file validation, không ghi DB/fetch URL):

```powershell
.venv/Scripts/python.exe -X utf8 -c "import sys; from pathlib import Path; from datetime import UTC, datetime; sys.path.insert(0, 'apps/api/src'); from ai_atlas_api.curated_models import CuratedCatalog; from ai_atlas_api.curated_validation import validate_catalog; catalog = CuratedCatalog.model_validate_json(Path('data/curated/taxonomy.json').read_bytes()); validate_catalog([catalog], now=datetime.now(UTC)); print('semantic taxonomy validation passed')"
.venv/Scripts/python.exe -m pytest -p no:cacheprovider apps/api/tests/unit/test_curated_validation.py
# DATABASE_URL theo DB local; integration tạo/xóa DB tạm, không ghi vào catalog chính.
.venv/Scripts/python.exe -m pytest -p no:cacheprovider apps/api/tests/integration/test_curated_snapshot.py
```

Validation cho updates vào DB phải cung cấp snapshot DB đích; lỗi đọc DB không được fallback catalog rỗng. Validator không chứng minh nguồn chính thức/truy cập được, không tự fetch hoặc downgrade verified stale. Verification 005.2: 76 semantic unit cases + 6 DB cases; full 185 unit tests và 52 integration tests; Ruff/mypy pass. Smoke dùng taxonomy file thật và DB history tạm đã chặn missing FK, relation false, identity hết hạn, credentials/source reuse; evidence mới cho phép proposal hợp lệ mà stored DB value/revision giữ nguyên. DB smoke tạm đã xóa; không gọi Gemini. TASK-005.1..005.6 và TASK-005 tổng Done; schema/validation/dry-run/import và seed 15 tools đã có, end-to-end API verification thuộc 005.6.

## Curated CLI dry-run — TASK-005.3

CLI validate cả batch trên snapshot DB đích rồi báo thêm/sửa/không đổi và field names thay đổi, không ghi DB hoặc fetch nguồn. [Diff/exit-code contract](docs/architecture/DATA_MODEL.md#10-curated-dry-run-và-diff--task-0053); source authenticity vẫn do curator xác minh thủ công.

Từ repo root, DB đã migrate; DATABASE_URL có thể lấy từ .env. Ví dụ local Compose đang dùng cổng fallback 55432:

```powershell
$env:PYTHONPATH = "apps/api/src"
$env:DATABASE_URL = "postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:55432/ai_atlas"
.venv/Scripts/python.exe -m ai_atlas_api.curated_cli dry-run data/curated/taxonomy.json
.venv/Scripts/python.exe -m ai_atlas_api.curated_cli dry-run --format json data/curated/taxonomy.json
$LASTEXITCODE
```

Có thể truyền nhiều files sau dry-run/format; references resolve toàn batch, không phụ thuộc thứ tự taxonomy/tools files. Chỉ nhận regular files tối đa 8 MiB/file và 32 MiB/batch; duplicate JSON keys bị từ chối. Không có --database-url; write action `import` được mô tả ở TASK-005.4 bên dưới.

- Exit **0**: valid, dù có changes; **2**: arguments/input/validation invalid; **3**: DB thiếu/unavailable; **4**: lỗi CLI/config khác, sanitized INTERNAL_ERROR.
- JSON stdout có status/as_of/summary/changes/errors. Rows tách 5 entity types + facts/evidence, chỉ UUID/parent_id/status/changed_fields, không in raw data/source/credentials. Argument syntax errors ở stderr, không JSON stdout. Có lỗi thì không trả partial diff.
- Summary chỉ đếm incoming records. Omitted entities/facts/evidence không có deletion action; tool join arrays là proposed complete sets. Tool metadata/joins và child fact/evidence thay đổi được báo riêng. Notes và server-owned revisions/search/embedding fields không thuộc diff.

Chạy riêng regression cases mới với DATABASE_URL của role dev/test có quyền tạo DB/role và apply migrations (fixtures tự xóa DB/SELECT-only role tạm):

```powershell
$testTemp = Join-Path ".cache" ("pytest-curated-" + [guid]::NewGuid().ToString("N"))
.venv/Scripts/python.exe -m pytest --basetemp $testTemp -p no:cacheprovider apps/api/tests/unit/test_curated_cli.py apps/api/tests/integration/test_curated_dry_run_db.py
```

Dùng path --basetemp mới cho mỗi lần chạy vì pytest có thể xóa nội dung path được chỉ định; không trỏ vào thư mục chứa công việc khác.


Verification 005.3: **19 unit + 16 DB/CLI cases mới**, full **204 unit + 68 integration tests**, Ruff/format/Mypy pass. CLI taxonomy thật báo 23 added, 0 updated, 0 unchanged trên DB local hiện chưa seed. Smoke riêng chạy SELECT-only role: unchanged re-import, old evidence/new value reject, evidence mới cho phép diff; exit 0/2/3/4 và fingerprint DB (timestamps/revisions/joins/history) giữ nguyên. DB/role/input smoke tạm đã xóa; không gọi Gemini. Windows pytest default temp có ACL deny: verification dùng --basetemp với path mới trong .cache; không xóa cache/user temp có sẵn.

TASK-005 và TASK-006 đã Done. Atomic importer, curated seed 15 tools và Discover UI đã có; tiếp theo TASK-007 — automated E2E Journey A. Chưa có historical restore command hoặc embedding rebuild.

## Atomic curated import — TASK-005.4

`import` dùng cùng parser/validator/diff của dry-run, nhưng re-read snapshot và validate lại trong một SERIALIZABLE transaction có advisory lock rồi mới upsert. **Lệnh này ghi DB được cấu hình**; luôn review dry-run trên đúng DATABASE_URL trước:

```powershell
$env:PYTHONPATH = "apps/api/src"
$env:DATABASE_URL = "postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:55432/ai_atlas"
.venv/Scripts/python.exe -m ai_atlas_api.curated_cli dry-run --format json data/curated/taxonomy.json data/curated/tools.json
if ($LASTEXITCODE -eq 0) {
  .venv/Scripts/python.exe -m ai_atlas_api.curated_cli import --format json data/curated/taxonomy.json data/curated/tools.json
}
```

Truyền tất cả taxonomy/tool files của batch trong cùng command; thứ tự files không ảnh hưởng references/diff. Exit/output contract giống dry-run: 0 valid và đã commit, 2 input/semantic invalid, 3 DB/lock/statement unavailable, 4 sanitized CLI/config error. Có lỗi thì changes/summary rỗng và transaction rollback. Không có --database-url.

- Re-import unchanged không UPDATE timestamps hoặc bump revisions; omitted rows không bị xóa. Incoming tool relation arrays là complete sets và được replace nếu thay đổi.
- Tool metadata/relations đổi: tool revision +1 đúng một lần, xóa embedding và reindex search. Category/capability label đổi cũng cập nhật linked tools. Fact value/status đổi: fact revision +1; evidence mới gắn revision mới, nguồn cũ giữ lịch sử. Add evidence không đổi claim không bump revision.
- Search projection: name A, description/tags B, category slug+name và capability key+name C với PostgreSQL simple config. Import không tạo embedding mới; TASK-008 chịu trách nhiệm rebuild.
- Source authenticity vẫn do curator xác minh; importer không fetch URLs hoặc gọi Gemini. Referenced capability key/model slug không được rename vì sẽ phá fact namespaces.

Regression riêng (fixtures tạo/xóa database tạm; lock-timeout case mất khoảng 5 giây):

```powershell
$testTemp = Join-Path ".cache" ("pytest-import-" + [guid]::NewGuid().ToString("N"))
.venv/Scripts/python.exe -m pytest --basetemp $testTemp -p no:cacheprovider apps/api/tests/unit/test_curated_cli.py apps/api/tests/integration/test_curated_import_db.py
```

Verification 005.4: **1 unit + 7 DB/import cases mới**, full **205 unit + 75 integration tests**, Ruff/format/Mypy pass. Runtime smoke ngoài pytest import taxonomy thật + synthetic temporary published tool: initial 29 added; unchanged re-import không update; content change 1 added/2 updated/26 unchanged, tool/fact revisions tăng đúng một, joins/search thay atomically, embedding bị xóa, evidence revisions [1,2] còn đủ; re-import giữ exact DB fingerprint; invalid FK exit 2 và không đổi transaction. Temporary DB/input đã xóa; configured development catalog không bị import, không fetch source hoặc gọi paid API.

TASK-005 và TASK-006 đã Done. Atomic importer, curated seed 15 tools và Discover UI đã có; tiếp theo TASK-007 — automated E2E Journey A. Chưa có historical restore command hoặc embedding rebuild.

## Curated seed — TASK-005.5

`data/curated/tools.json` chứa 15 published tools có nguồn chính thức: ChatGPT, Claude, Gemini, GitHub Copilot, Cursor, Midjourney, Adobe Firefly, Runway, ElevenLabs, Otter.ai, Perplexity, NotebookLM, Zapier, n8n và Langflow. Seed có 14 providers, phủ đủ 8 categories và 10 capability keys; không khai báo models/model usage.

Mỗi tool có verified identity + verified capability evidence. Pricing, platforms, API, open-source, deployment và offline được ghi explicit unknown cho từng tool; không suy claim từ marketing. 30 evidence records được review ngày 30/09/2026 và hết freshness ngày 29/12/2026 15:00Z; cần curator kiểm tra lại trước khi import sau mốc đó. Chi tiết [seed contract](docs/architecture/DATA_MODEL.md#12-curated-seed--task-0055).

Dry-run/import cả vocabulary và tools:

```powershell
$env:PYTHONPATH = "apps/api/src"
$env:DATABASE_URL = "postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:55432/ai_atlas"
.venv/Scripts/python.exe -m ai_atlas_api.curated_cli dry-run --format json data/curated/taxonomy.json data/curated/tools.json
if ($LASTEXITCODE -eq 0) {
  .venv/Scripts/python.exe -m ai_atlas_api.curated_cli import --format json data/curated/taxonomy.json data/curated/tools.json
}
```

Verification 005.5: 3 seed acceptance tests; full **208 unit + 75 integration tests**, Ruff/format/Mypy pass. Temporary-DB smoke: dry-run/import đều 202 added; persisted 15 published tools, 14 providers, 30 evidence, 90 explicit unknown facts, 8 categories và 10 capabilities. Temporary DB đã xóa; development catalog không bị import, không gọi source URLs hoặc paid API.

TASK-005 và TASK-006 đã Done. Atomic importer, curated seed 15 tools và Discover UI đã có; tiếp theo TASK-007 — automated E2E Journey A. Chưa có historical restore command hoặc embedding rebuild.

## Curated operating verification — TASK-005.6

[Hướng dẫn Windows, commands và output evidence](docs/operations/CURATED_CATALOG.md) bao gồm dry-run/import/re-import, API smoke, xử lý freshness/import failure. Regression tại `apps/api/tests/integration/test_curated_pipeline.py` tự tạo/xóa DB tạm và chạy Uvicorn/HTTP thật. 9 cases mới pass; full 208 unit + 84 integration tests, Ruff/format/Mypy pass ngày 01/10/2026. Không cần Gemini key, không fetch URL, không auto-refresh evidence hoặc historical restore. Development catalog không được tự seed.

## Tool detail — TASK-006.6

`/tools/[tool_id]` hiển thị grouped facts, pricing/conditions, sources và summary rail. Nguồn có domain, checked_at/expires_at theo UTC; null/unknown và unverified/stale không trở thành verified false. `conditions: []` khác null. Official link chỉ HTTPS, mở tab mới với noopener/noreferrer. Page initial dùng server-only Catalog transport, retry dùng BFF; absent/archived/invalid ID trả public 404. Không có Save/Builder controls hoặc mock fallback.

Sau khi import seed và chạy API theo operating guide, đặt `API_BASE_URL` trong terminal chạy web. Ví dụ smoke thủ công từ repo root:

```powershell
$env:API_BASE_URL = 'http://127.0.0.1:8000'
.\scripts\pnpm.ps1 --filter @ai-atlas/web dev
```

Mở `/explorer?q=ChatGPT&pricing_model=unknown`, chọn chi tiết, mở nguồn bằng Enter, đổi vi/en rồi quay lại Explorer: q/filter phải giữ nguyên. Direct `/tools/<UUID>` quay về Explorer mặc định; `/tools/not-a-uuid` hoặc UUID archived hiển thị 404, không có metadata private. Kiểm tra ở desktop và 360px. Không cần mở source URL hoặc gọi Gemini để kiểm UI.

Checks từ repo root:

```powershell
.\scripts\pnpm.ps1 --filter @ai-atlas/web lint
.\scripts\pnpm.ps1 --filter @ai-atlas/web typecheck
.\scripts\pnpm.ps1 --filter @ai-atlas/web test
.\scripts\pnpm.ps1 --filter @ai-atlas/web build
```

Ngày 04/10/2026: full 33 tests, lint/typecheck/build pass. Actual smoke với PostgreSQL tạm + 202 imported records, Uvicorn8006, Next production3006 và Chromium: HTTP200/404, return URL, en/vi, sources, keyboard và 360/320px reflow pass; screenshots đã kiểm trực quan. DB/services tạm đã dọn. Kiểm thử toàn diện Discover/a11y ở 006.7; automated Journey A E2E ở TASK-007.

## Discover hardening — TASK-006.7

Ngày 05/10/2026: sửa footer che keyboard focus trong mobile filter drawer; locale switch giữ URL/filter/page/draft và error state. Full 35 web tests, lint/typecheck/build pass. Seeded browser smoke và 79 axe scans không có violations; 3 state results cần manual review đã được kiểm, không phải chứng nhận WCAG.

[Operating guide](docs/operations/DISCOVER_VERIFICATION.md) có commands Windows, evidence và giới hạn. Hai scripts local opt-in: [matrix audit](scripts/audit-discover.cjs) và [drawer focus regression](scripts/check-discover-focus.cjs). TASK-006 hoàn tất; TASK-007.1 đã cung cấp automated real-stack E2E foundation cho Journey A.

## Discover E2E foundation — TASK-007.1

Yêu cầu: Node/pnpm theo workspace, Python environment đã sync và PostgreSQL local cho phép role cấu hình tạo/xóa database. Runner không dùng development database, Gemini key hay network đến official sources. Với Compose mặc định đang chạy trên cổng `55432`:

```powershell
$env:E2E_DATABASE_ADMIN_URL = 'postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:55432/ai_atlas'
.\scripts\pnpm.ps1 test:e2e:discover
```

Nếu PostgreSQL ở `127.0.0.1:5432` với credentials mặc định thì bỏ biến trên. Có thể đặt `E2E_API_PORT`, `E2E_WEB_PORT`, `E2E_BASE_URL` và `E2E_STARTUP_TIMEOUT_MS`; mặc định runner tự chọn hai cổng loopback chưa dùng. `E2E_BASE_URL` phải trỏ đúng origin web đã chọn.

Mỗi lượt tạo database `ai_atlas_e2e_<random>`, chạy migrations, import `data/curated/taxonomy.json` + `data/curated/tools.json`, xác nhận summary `202 records/15 tools`, build/start Next production và start FastAPI rồi mới chạy Chromium. Readiness có timeout; process, database và `.next-e2e` luôn được dọn. Run pass xóa thư mục run; run fail giữ logs, Playwright trace/screenshot tại `.cache/discover-e2e/<run-id>/` để điều tra. Không commit artifacts.

Evidence 06/10/2026 trên Windows: command trên pass `1` Playwright smoke test qua API/BFF/UI thật với default port allocation và với `E2E_BASE_URL` cấu hình; seed đúng `202 records/15 tools`. Success hậu kiểm có `0` database `ai_atlas_e2e_%`, không còn `.next-e2e`, artifact directory rỗng. Forced API startup failure trả exit khác `0`, giữ `api.log`, đồng thời vẫn xóa database/build output; artifact kiểm chứng đã được dọn. Frontend lint/E2E typecheck/35 tests/production build và backend Ruff/format/mypy/208 unit tests pass. Đây là foundation smoke; Journey A happy path thuộc 007.2, negative paths và CI gate thuộc 007.3–007.4.

## Journey A happy path — TASK-007.2

`e2e/discover-journey.spec.ts` chạy cùng foundation test trên real stack. Hai cases vi/en dùng accessible role/name, đi từ Home qua search và category/pricing filters đến canonical Explorer URL, kiểm đúng ChatGPT result, provider/facts/status/evidence dates, quay lại giữ search/filters/sort/page và mở lại detail.

Official `https://chatgpt.com/` link được kiểm `target="_blank"`, `noopener noreferrer`, popup có `window.opener === null`. Playwright intercept request bằng HTML cục bộ nên test không fetch official source. Evidence 07/10/2026 trên Windows/Chromium: `test:e2e:discover` pass `3` cases gồm foundation + Journey A vi/en; isolated production build pass và runner dọn database/services/`.next-e2e`/success artifacts. E2E cũng giữ regression cho English singular `1 result`.

## Journey A negative paths và recovery — TASK-007.3

Ngày 08/10/2026: thêm 5 cases real empty/reset, invalid category 422/reset, public 404 không lộ archived metadata, controlled 503/retry giữ query và delayed old-request recovery. Archived fixture chỉ nằm trong E2E database tạm, tách curated files; không gọi Gemini hoặc official source. ESLint bỏ qua generated `.next-e2e` output.

Cùng command `test:e2e:discover` pass **8/8 cases** trong 11.6s; isolated production build, root lint/typecheck, **35 Vitest tests** và Ruff/format/mypy cho DB helper pass. Xem [operating guide](docs/operations/DISCOVER_VERIFICATION.md) để tái hiện. TASK-007 vẫn In progress; 007.4 đã thêm CI gate, tiếp theo **007.5 — full regression và bàn giao TASK-007**.

## Discover E2E CI gate — TASK-007.4

Job `Discover E2E` trong `.github/workflows/ci.yml` chạy trên mọi pull request và push vào `develop`/`main`. Job cài dependencies khóa bằng pnpm/uv, Chromium system dependencies, dựng PostgreSQL Compose disposable rồi gọi cùng `test:e2e:discover` command. Job timeout 25 phút, E2E step timeout 15 phút; Playwright giữ `retries: 0`, lỗi không `continue-on-error`.

Khi fail, `actions/upload-artifact@v4` upload toàn bộ hidden `.cache/discover-e2e/` trong 7 ngày, gồm service logs, screenshot, trace và error context nếu harness đã chạy. `if: always()` xóa Compose volume và `.next-e2e`. Workflow không đọc secrets hoặc truyền Gemini key; harness buộc live AI off và official link được Playwright fulfill cục bộ.

Evidence 09/10/2026: actionlint 1.7.12 pass; local CI-mode run (`CI=true`) pass **8/8 cases** trong 11.9s cùng isolated production build. Forced deterministic assertion failure trả exit `1`, giữ `api.log`, `web.log`, screenshot, trace và error context; runner vẫn xóa database/process/build output. Root lint/typecheck và **35/35 Vitest** pass. GitHub-hosted execution và artifact upload chỉ quan sát được sau commit/push; task không push repository.
