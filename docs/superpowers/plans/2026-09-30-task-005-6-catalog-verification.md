# TASK-005.6 — Curated catalog verification

> **For agentic workers:** Use superpowers:executing-plans to execute the checklist inline.

**Goal:** Chứng minh pipeline curated files → CLI → PostgreSQL → HTTP API và ghi hướng dẫn Windows tái hiện được.

**Architecture:** Dùng database PostgreSQL tạm có tên UUID, migrations hiện có và CLI subprocess thật. Chạy Uvicorn riêng trên loopback, kiểm tra bằng HTTP; luôn dừng process và xóa đúng database do test tạo.

**Tech Stack:** Python 3.11, pytest, psycopg, httpx, Uvicorn, PowerShell.

**Spec:** TASK-005.6 trong `docs/planning/TASKS.md` và yêu cầu chi tiết của chủ dự án ngày 30/09/2026.

## Constraints

- Thực hiện trên develop theo chỉ dẫn đã có; không commit/push/deploy.
- Không sửa seed, thêm tools, fetch URL, gọi Gemini, embeddings hoặc historical restore.
- 202 records = 14 providers + 8 categories + 15 capability definitions + 15 tools + 120 facts + 30 evidence; 0 models.
- Dùng clock thật cho CLI/API; evidence hết freshness phải báo lỗi, không tự dịch timestamps.

## Review focus

- Dry-run không ghi DB: so sánh fingerprint toàn bộ catalog tables.
- Re-import không đổi timestamps/revisions/joins/evidence: fingerprint trước/sau giống nhau.
- Validation reject không thay thế bằng chứng rollback: thêm DB trigger gây lỗi sau earlier writes.
- Unknown không match boolean false/free: kiểm tra HTTP filters và detail null/unknown.
- Không lẫn synthetic seed: exact public IDs và draft/archived sentinels riêng trong DB tạm.

## Task 1 — Verification

**Files:** `apps/api/tests/integration/test_curated_pipeline.py`.
**Consumes:** CLI `dry-run`/`import`, curated JSON hiện có, migrations, `/api/v1/categories`, `/api/v1/tools`, `/api/v1/tools/{id}`.
**Produces:** Regression end-to-end có stdout evidence, chạy bằng pytest integration.

- [x] Dry-run sạch: 202/0/0, errors rỗng, DB fingerprint không đổi.
- [x] Import: counts đúng, 15 published tools, 90 unknown facts, 10 used capabilities.
- [x] Re-import + dry-run sau import: 0/0/202, exact fingerprint không đổi.
- [x] Sai FK/source/fact type: exit 2, không partial records; lỗi DB giữa writes rollback toàn bộ.
- [x] Uvicorn/HTTP thật: categories, pagination/search/filters/detail/provenance/unknown; draft/archived 404 và không nằm trong list/search.
- [x] Chạy targeted test, full unit/integration, Ruff/format/Mypy; sửa implementation nếu có regression chứng minh lỗi.

## Task 2 — Operating guide và evidence

**Files:** `docs/operations/CURATED_CATALOG.md`, `README.md`, `docs/planning/TASKS.md`, stale current-state references trong API contract.
**Consumes:** Kết quả Task 1.
**Produces:** Commands Windows, output thực tế, xử lý freshness/error và trạng thái backlog đúng.

- [x] Ghi setup, migration, dry-run/import/re-import, API/smoke và cleanup DB tạm.
- [x] Phân biệt rollback transaction, validation reject và historical restore; ghi exit codes/freshness/manual review.
- [x] Kiểm tra commands/links/diff, review và ghi evidence; chỉ đánh dấu 005.6/TASK-005 Done sau khi pass.

## Execution notes

Chủ dự án đã yêu cầu thực hiện đầy đủ task với acceptance criteria cụ thể; tiếp tục inline, không thêm vòng xin duyệt kế hoạch. Chỉ thêm verification/tests/docs trừ khi phát hiện lỗi implementation. Các test acceptance mới kiểm tra behavior đã có nên không kỳ vọng RED nếu implementation đúng; mọi fix production phải có reproducer trước.


## Kết quả ngày 01/10/2026

9 acceptance cases pass; full 208 unit + 84 integration tests pass; Ruff check/format và Mypy (16 source files) pass. Local markdown targets, 7 PowerShell blocks và git diff whitespace đã kiểm tra. Không còn DB tạm của pipeline; Uvicorn được fixture terminate/wait; giữ container DB có sẵn.

Review độc lập không có blocking findings. Đã làm rõ hướng dẫn refresh: thêm evidence-only không bump fact revision, nhưng đổi last_verified_at sẽ bump tool revision. Checklist hoàn tất sau review. Source authenticity vẫn thuộc manual curation; historical restore và synthetic discriminator ngoài scope. Không phát hiện lỗi production implementation.

Điều chỉnh test trong quá trình xác minh: ban đầu đổi description làm batch bị chặn đúng bởi identity validator trước khi tới DB trigger; đổi sang tag update hợp lệ để kiểm write-stage rollback. Sequence witness xác nhận earlier provider write đã xảy ra, rồi fingerprint chứng minh rollback toàn bộ.
