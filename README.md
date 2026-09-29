# AI Atlas — Discover, Compare & Build Your AI Stack

> Discover AI. Build your stack.

AI Atlas là nền tảng khám phá AI tools và xây dựng AI stack theo mục tiêu, thiết bị và ngân sách của người dùng. Sản phẩm kết nối một thư viện được biên tập với hệ thống đề xuất có căn cứ, giúp trả lời: có công cụ nào, công cụ nào phù hợp và chúng kết hợp thành quy trình như thế nào?

**Trạng thái ngày 29/09/2026:** foundation scaffold đã chạy được: Next.js shell song ngữ, FastAPI health/readiness, PostgreSQL + pgvector bằng Compose, Gemini adapter thật và CI không gọi dịch vụ trả phí. TASK-003 đang In progress; subtask 003.1–003.4 đã bổ sung migration runner/catalog core, typed facts/evidence/capabilities/embeddings, users và private generation runs có ownership/accounting/TTL cùng persistence schema cho stacks/items/edges với snapshots, idempotency và composite-FK integrity; ADR-010 đã Accepted. Stack API, dữ liệu công cụ đã xác minh, authentication flow, recommendation feature và benchmark chưa được triển khai. Các chỉ tiêu sản phẩm trong tài liệu vẫn là mục tiêu nghiệm thu.

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

TASK-002 đã Done ngày 28/09/2026 sau khi clean setup/offline/DB/HTTP checks và billed live smoke đều pass. TASK-003 đang In progress; subtask 003.1–003.4 hoàn tất ngày 29/09/2026 với migration CLI/catalog core, typed facts/evidence/capabilities, embeddings D=1536, users/generation runs và stack persistence đã kiểm tra trên PostgreSQL 17/pgvector; ADR-010 Accepted. Chỉ còn subtask 003.5 indexes/full verification trước khi đóng TASK-003. Không dán key vào chat hoặc commit. Trạng thái và evidence đầy đủ nằm trong [backlog](docs/planning/TASKS.md).
