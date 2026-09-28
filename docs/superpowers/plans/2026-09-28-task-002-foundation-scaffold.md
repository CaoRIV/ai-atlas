# TASK-002 Foundation Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Tạo một foundation có thể tái lập trên Windows và CI: Next.js web, FastAPI API, PostgreSQL/pgvector, Gemini adapter thật và các lệnh lint/type/test/build/health thực sự chạy được.

**Architecture:** Giữ web và API là hai host processes; Docker Compose chỉ chạy PostgreSQL/pgvector để phù hợp máy khoảng 8GB RAM. API dùng application factory, settings fail-closed và DB readiness probe không gọi Gemini. Runtime chỉ có Gemini adapter thật qua Google Gen AI SDK; unit/CI inject transport/response fixtures, còn live smoke là opt-in và phát sinh chi phí Gemini thật.

**Tech Stack:** Node.js 22 LTS, Corepack + pnpm workspace, Next.js 16, React 19, TypeScript strict, Tailwind CSS 4, Vitest; Python 3.11, uv, FastAPI, Pydantic Settings, psycopg 3, Google Gen AI SDK 2.23.0, pytest; PostgreSQL 17 + pgvector 0.8.6; Docker Compose; GitHub Actions.

**Spec:** `docs/planning/TASKS.md` TASK-002; `docs/architecture/SYSTEM_ARCHITECTURE.md` sections 7–8; `docs/architecture/API_DESIGN.md` health contract; `docs/planning/BASELINE_REVIEW.md` handoff.

## Global Constraints

- Frontend/backend chạy trên host; Compose chỉ chạy DB mặc định.
- Runtime provider duy nhất là Gemini; unit/CI không gọi Gemini và không nhận API key, bằng cách inject transport vào cùng adapter.
- Secrets chỉ qua environment; không có biến secret với prefix public của Next.js.
- TypeScript strict, Python type hints, Pydantic tại trust boundaries, JSON snake_case.
- Health live không chạm DB; health ready kiểm tra DB và extension `vector`, không lộ credentials/version chi tiết.
- Pin direct dependencies trong manifests và toàn bộ dependency graph bằng `pnpm-lock.yaml`/`uv.lock`.
- UI shell ban đầu có locale `vi`/`en`, nhưng journey UI đầy đủ thuộc các task frontend sau.
- Không implement catalog schema, auth flow, recommendation orchestration hoặc business endpoints trong TASK-002; Gemini SDK adapter thật và opt-in live smoke thuộc scope foundation.
- Không tự commit; AGENTS.md yêu cầu chỉ commit khi task yêu cầu. Người dùng đã xin commit name riêng cho TASK-001, chưa yêu cầu commit TASK-002.

## Review Focus

- Thiếu `DATABASE_URL` phải làm readiness trả 503 có mã ổn định, không crash process hoặc lộ config.
- DB chạy nhưng chưa có extension `vector` phải trả readiness 503; Compose init phải tạo extension trên DB sạch.
- API health phải khởi động khi chưa cấu hình Gemini key; khởi tạo/call Gemini adapter phải fail closed nếu thiếu key.
- Live smoke phải opt-in, thực hiện tối đa một minimal generation và một embedding request, rồi báo model/usage mà không log prompt/key.
- Secret placeholders không được xuất hiện trong client bundle hoặc biến `NEXT_PUBLIC_*`.
- Setup/check scripts phải chạy từ PowerShell trên Windows và báo rõ dependency bị thiếu thay vì tiếp tục nửa chừng.

---

### Task 1: Root workspace, pinned tooling và environment contract

**Files:**
- Create: `.gitignore`, `.editorconfig`, `.env.example`, `.node-version`, `package.json`, `pnpm-workspace.yaml`, `pyproject.toml`
- Create after dependency resolution: `pnpm-lock.yaml`, `uv.lock`
- Create: `scripts/setup.ps1`, `scripts/check.ps1`

**Interfaces:**
- Produces: root commands `pnpm lint`, `pnpm typecheck`, `pnpm test`, `pnpm build`; Python groups resolved by `uv sync --all-groups`; documented environment names consumed by API/Compose.

- [x] Verify registry sources and pin Node 22 LTS, pnpm, Next/React/TypeScript/Tailwind/Vitest, Python 3.11, FastAPI/Pydantic/psycopg/pytest versions in manifests.
- [x] Add root workspace/config files and environment placeholders for database, OIDC, Gemini model keys, `EMBEDDING_DIM=1536`, `GEMINI_API_KEY`, and `RUN_LIVE_AI_TESTS=0`.
- [x] Implement `scripts/setup.ps1` to validate Node/Python/Docker, enable the pinned pnpm via Corepack, install lockfiles, and copy `.env.example` only when `.env` is absent.
- [x] Implement `scripts/check.ps1` to run the same lint/type/test/build sequence documented for CI.
- [x] Run setup from PowerShell; record actual versions and any host-specific limitation in README evidence.

### Task 2: FastAPI health boundary and real Gemini adapter (TDD)

**Files:**
- Create: `apps/api/src/ai_atlas_api/__init__.py`, `config.py`, `main.py`
- Create: `apps/api/src/ai_atlas_api/db.py`, `health.py`
- Create: `apps/api/src/ai_atlas_api/providers/base.py`, `gemini.py`, `__init__.py`
- Create: `apps/api/tests/test_health.py`, `test_gemini_provider.py`, `test_config.py`, `live/test_gemini_live.py`

**Interfaces:**
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`; `GET /health/live`; `GET /health/ready`; async `check_database_ready(database_url: str | None) -> ReadinessResult`; `GeminiProvider` wrapping `gemini-3.5-flash-lite` and `gemini-embedding-2` with injected Google Gen AI client/transport.

- [x] Write failing config tests proving health/settings load without API key, Gemini provider construction rejects a missing key, and secrets are excluded from public/debug serialization.
- [x] Run focused config tests and confirm expected failure because settings/app code is absent.
- [x] Implement strict settings with explicit Gemini model/dimension values and fail-closed provider construction; rerun focused tests to green.
- [x] Write failing health tests for live 200, ready 503 on missing/failed DB, and ready 200 only when DB plus `vector` extension are available.
- [x] Run health tests and confirm expected route/function failures.
- [x] Implement application factory, DB probe with bounded connection timeout, stable response models and 503 behavior; rerun health tests.
- [x] Write failing Gemini adapter contract tests using an injected transport/client fixture for structured JSON generation, configured-dimensional embeddings, normalized usage/errors, model IDs and no network access. Deadline enforcement remains in TASK-015.
- [x] Implement the minimal Gemini adapter against `google-genai==2.23.0`; rerun focused tests plus full `uv run pytest` without `GEMINI_API_KEY`.
- [x] Add a separately marked live smoke test that is skipped unless `RUN_LIVE_AI_TESTS=1` and `GEMINI_API_KEY` exist; cap it to one tiny generation and one tiny embedding call and report sanitized model/usage.
- [x] Run Ruff lint/format check and mypy strict checks for API code.

### Task 3: Next.js web shell and health endpoint (TDD)

**Files:**
- Create: `apps/web/package.json`, `tsconfig.json`, `next.config.ts`, `postcss.config.mjs`, `eslint.config.mjs`, `vitest.config.ts`, `vitest.setup.ts`
- Create: `apps/web/app/layout.tsx`, `page.tsx`, `globals.css`, `api/health/route.ts`
- Create: `apps/web/app/api/health/route.test.ts`, `app/page.test.tsx`

**Interfaces:**
- Produces: Next.js app build; `GET /api/health` returning `{status:"ok"}`; minimal bilingual foundation shell with semantic HTML and no backend/API secrets.

- [x] Write failing tests for web health JSON/status and accessible English/Vietnamese foundation copy.
- [x] Run `pnpm --filter @ai-atlas/web test` and confirm failure because routes/components are absent.
- [x] Implement minimal App Router shell, health route, Tailwind import and locale-ready copy boundary; rerun tests.
- [x] Run web ESLint, `tsc --noEmit`, unit tests and production build.
- [x] Inspect build output/env usage to confirm no server secrets use `NEXT_PUBLIC_*`.

### Task 4: PostgreSQL/pgvector Compose and clean-DB integration test

**Files:**
- Create: `compose.yaml`, `infra/postgres/init/001_extensions.sql`
- Create: `apps/api/tests/integration/test_database_readiness.py`
- Modify: `.env.example`

**Interfaces:**
- Produces: service `db` on configurable localhost port; healthcheck; named volume; `CREATE EXTENSION IF NOT EXISTS vector`; readiness integration test using the API's real DB probe.

- [x] Write the integration test requiring a real clean Postgres and asserting both connectivity and `vector` availability.
- [x] Run it without Compose and confirm the expected connection failure/skip gate is explicit.
- [x] Add Compose using pinned `pgvector/pgvector:0.8.6-pg17-bookworm`, low-memory Postgres settings, healthcheck, named volume and init SQL.
- [x] Start Compose with a clean project-scoped volume; wait for healthy; run the integration test to green.
- [x] Verify `docker compose config` and query `SELECT extversion FROM pg_extension WHERE extname='vector'` without logging credentials.
- [x] Stop services without deleting the named volume; document the separate recoverable reset command and its scope.

### Task 5: CI, reproducible README và task closure

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`, `docs/planning/DECISIONS.md`, `docs/planning/TASKS.md`

**Interfaces:**
- Produces: CI jobs for locked web checks/build and locked API lint/type/unit tests, plus DB integration against pinned pgvector; Windows quickstart and exact commands actually run.

- [x] Add CI with pinned action major versions, Node/Python/uv/pnpm setup, frozen lockfiles, cache, transport-isolated Gemini contract tests and DB integration; never inject paid keys or enable live markers.
- [x] Run the full local equivalent: frozen installs, Compose config/up, API lint/type/unit/integration, web lint/type/test/build, and HTTP smoke for web/API/DB readiness.
- [x] Update README with verified Windows commands, ports, expected health responses, troubleshooting for Docker/npm path, reset semantics and known limits.
- [x] Change ADR-009 to Accepted only if measured topology works; record actual environment and results.
- [x] Mark TASK-002 Done only when every acceptance item has fresh evidence; otherwise leave In progress/Blocked with the exact failing command.
  - Completed on 28/09/2026: clean `scripts/setup.ps1`, DB integration/HTTP health và billed `uv run pytest -m live -s` pass. Reverified on 29/09/2026 after removing generated caches with stale ACL: `scripts/check.ps1` pass trực tiếp tại `D:\ai-atlas`. Sanitized live evidence: `gemini-3.5-flash-lite` dùng 9 input, 11 output và 20 total tokens; `gemini-embedding-2` trả D=1536. Không log prompt/key.
- [x] Run `git diff --check`, secret-pattern scan, Markdown local-link check, and `git status --short`; inspect every changed file before handoff.

## Self-review

- Coverage: web/API/DB health, Gemini adapter, injected-transport contracts, opt-in live smoke, secrets, pinned versions, Windows setup, CI and ADR/backlog evidence each map to a task.
- Boundaries: catalog migrations/auth/live Gemini are intentionally excluded and remain in their owning tasks.
- Shared interfaces: root scripts call package/API commands defined in Tasks 2–3; readiness integration consumes Task 2's DB probe and Task 4's Compose DB; CI consumes all commands and lockfiles.
- Risks: local npm is broken, so Corepack/pnpm is explicit; Docker config warning must be tested rather than ignored; Node host version differs from pinned LTS and will be recorded if not upgraded.
