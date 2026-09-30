# AI Atlas — Discover, Compare & Build Your AI Stack

> Discover AI. Build your stack.

AI Atlas là nền tảng khám phá AI tools và xây dựng AI stack theo mục tiêu, thiết bị và ngân sách của người dùng. Sản phẩm kết nối một thư viện được biên tập với hệ thống đề xuất có căn cứ, giúp trả lời: có công cụ nào, công cụ nào phù hợp và chúng kết hợp thành quy trình như thế nào?

**Trạng thái ngày 30/09/2026:** TASK-001..004 và subtasks 005.1..005.5 đã Done; TASK-005 tổng vẫn In progress. Foundation có Next.js shell song ngữ, FastAPI health/readiness, PostgreSQL + pgvector bằng Compose, Gemini adapter thật và CI không gọi dịch vụ trả phí. Catalog API đã có categories/list/detail, keyword search, filters, pagination và provenance. Curated schema/validation/dry-run/atomic import đã hoạt động; seed có 15 published tools, 14 providers, 30 official-source evidence và unknown facts minh bạch. Full 208 unit + 75 DB integration tests, Ruff/Mypy và actual seed import smoke pass. 005.6 end-to-end API verification và Explorer UI chưa hoàn tất.

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

Chạy API và web trong hai terminal:

```powershell
uv run uvicorn ai_atlas_api.main:app --app-dir apps/api/src --reload --port 8000
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

TASK-002 đã Done ngày 28/09/2026 sau clean setup/offline/DB/HTTP checks và billed live smoke. TASK-003 Done ngày 29/09/2026; TASK-004 Done ngày 30/09/2026 sau catalog contract tests trên DB thật. TASK-005 (curated import + seed) là bước tiếp theo của Discover slice; TASK-016 cũng đủ dependency. Không dán key vào chat hoặc commit. Trạng thái và evidence đầy đủ nằm trong [backlog](docs/planning/TASKS.md).

## Catalog API

Sau khi apply migrations và khởi động API, xem OpenAPI tại `http://127.0.0.1:8000/openapi.json` hoặc Swagger UI tại `http://127.0.0.1:8000/docs`. Public routes:

- `GET /api/v1/categories`
- `GET /api/v1/tools?q=keyword&category=coding-development&api_available=true&page=1&page_size=20`
- `GET /api/v1/tools/{tool_id}` (UUID)

Database chưa có curated seed thì list trả rỗng; category slug chưa tồn tại trả 422. TASK-005 sẽ tạo 8 categories và 15 tools có nguồn. Filter true/false chỉ nhận facts verified với evidence cùng revision còn hạn; detail hiển thị stale facts dưới trạng thái unverified. Query key lạ hoặc parameter lặp trả 422, draft/archived detail trả 404, DB chưa sẵn sàng trả 503. Chi tiết response và filters ở [API contract](docs/architecture/API_DESIGN.md).

Review fixes TASK-004: model relation chỉ hiển thị khi model-use fact verified fresh và value true; fact verified false vẫn giữ nguồn nhưng không công bố model. HTTP error envelope giữ exception headers, gồm `Allow: GET` cho 405, cùng request ID. Hai regression cases, 49 unit tests, 46 integration tests và smoke HTTP thật đã pass; evidence trong backlog. TASK-005 hiện In progress; 005.1 đã Done, importer/seed tools chưa triển khai.

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

TASK-005.1..005.5 đã Done; TASK-005 tổng vẫn In progress. Schema parsing 005.1, semantic validation 005.2, dry-run/diff 005.3, atomic import 005.4 và curated seed 15 tools 005.5 đã tách rõ. Seed chưa tự động import vào development DB. Unit/fixtures synthetic tách khỏi curated data. Verification 005.1: 60 schema cases và schema/vocabulary smoke pass; evidence đầy đủ trong backlog. Không gọi Gemini.

## Curated semantic validation — TASK-005.2

`apps/api/src/ai_atlas_api/curated_validation.py` kiểm tra whole-batch references/uniqueness, source syntax, TTL/time bounds, publication/identity và capability/model relations. `curated_snapshot.py` đọc DB ở chế độ read-only để bảo toàn fact/evidence ownership và chặn nguồn cũ chứng minh value/revision mới. Chi tiết [validation contract](docs/architecture/DATA_MODEL.md#9-semantic-import-validation--task-0052).

Kiểm tra taxonomy với catalog rỗng (file validation, không ghi DB/fetch URL):

```powershell
.venv/Scripts/python.exe -X utf8 -c "import sys; from pathlib import Path; from datetime import UTC, datetime; sys.path.insert(0, 'apps/api/src'); from ai_atlas_api.curated_models import CuratedCatalog; from ai_atlas_api.curated_validation import validate_catalog; catalog = CuratedCatalog.model_validate_json(Path('data/curated/taxonomy.json').read_bytes()); validate_catalog([catalog], now=datetime.now(UTC)); print('semantic taxonomy validation passed')"
.venv/Scripts/python.exe -m pytest -p no:cacheprovider apps/api/tests/unit/test_curated_validation.py
# DATABASE_URL theo DB local; integration tạo/xóa DB tạm, không ghi vào catalog chính.
.venv/Scripts/python.exe -m pytest -p no:cacheprovider apps/api/tests/integration/test_curated_snapshot.py
```

Validation cho updates vào DB phải cung cấp snapshot DB đích; lỗi đọc DB không được fallback catalog rỗng. Validator không chứng minh nguồn chính thức/truy cập được, không tự fetch hoặc downgrade verified stale. Verification 005.2: 76 semantic unit cases + 6 DB cases; full 185 unit tests và 52 integration tests; Ruff/mypy pass. Smoke dùng taxonomy file thật và DB history tạm đã chặn missing FK, relation false, identity hết hạn, credentials/source reuse; evidence mới cho phép proposal hợp lệ mà stored DB value/revision giữ nguyên. DB smoke tạm đã xóa; không gọi Gemini. TASK-005.1..005.5 Done, TASK-005 tổng In progress; schema/validation/dry-run/import và seed 15 tools đã có, end-to-end API verification thuộc 005.6.

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

TASK-005.1..005.5 Done; TASK-005 tổng In progress. Atomic import/revisions/history/search projection và curated seed 15 tools đã có; tiếp theo **005.6 — end-to-end importer/Catalog API verification**. Chưa có frontend Explorer.

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

TASK-005.1..005.5 Done; TASK-005 tổng In progress. Atomic importer và curated seed 15 tools đã có; tiếp theo **005.6 — end-to-end importer/Catalog API verification**. Chưa có historical restore command hoặc embedding rebuild.

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

TASK-005.1..005.5 Done; TASK-005 tổng In progress. Tiếp theo **005.6 — end-to-end importer/Catalog API verification và operating guide**.

