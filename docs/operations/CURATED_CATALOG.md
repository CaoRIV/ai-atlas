# Vận hành curated catalog

Pipeline: curated JSON → strict/semantic validation → dry-run → atomic import → Catalog API. Chạy từ repo root bằng PowerShell trên Windows. Contracts: [data model](../architecture/DATA_MODEL.md#10-curated-dry-run-và-diff--task-0053), [API](../architecture/API_DESIGN.md#2-catalog-routes).

Importer **không tự fetch URL, không gọi Gemini và không tự refresh evidence**. Không cần Gemini key. Nguồn chính thức và nội dung claim do curator xác minh thủ công. Không có historical restore command; rollback bên dưới là rollback transaction khi import lỗi.

## 1. Chuẩn bị

Sau [setup của repo](../../README.md#chạy-local-trên-windows), mở Docker Desktop và dùng PostgreSQL local đã healthy. Ví dụ cổng 55432:

```powershell
Set-Location D:\ai-atlas
$env:POSTGRES_PORT = '55432'
docker compose up --detach --wait db
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL chưa sẵn sàng' }
$env:PYTHONPATH = 'apps/api/src'
$env:DATABASE_URL = 'postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:55432/ai_atlas'
```

Connection trên là cấu hình local của Compose, không dùng cho production. `DATABASE_URL` environment ưu tiên hơn `.env`. Migrations và import ghi vào database đã chọn; kiểm tra host/port/database trước khi chạy, không in connection secret vào log.

## 2. Xác minh toàn pipeline trên database sạch tạm

Đây là đường chạy đầy đủ acceptance của TASK-005.6, không import vào catalog development. Role kết nối cần quyền `CREATEDB` và quyền apply migrations/extension trong DB tạm (role local Compose đáp ứng).

```powershell
$testTemp = Join-Path '.cache' ('pytest-curated-e2e-' + [guid]::NewGuid().ToString('N'))
.venv/Scripts/python.exe -m pytest -p no:cacheprovider --basetemp $testTemp `
  apps/api/tests/integration/test_curated_pipeline.py -q -s
if ($LASTEXITCODE -ne 0) { throw 'Curated verification failed; xem lỗi phía trên' }
```

Test tự tạo database tên `ai_atlas_pipeline_<uuid>`, migrate, chạy CLI bằng subprocess và Uvicorn thật trên cổng loopback tự chọn. Kết thúc mỗi test, fixture dừng process và xóa đúng DB tạm, kể cả khi assertion fail. Không dùng `docker compose down --volumes`. Dùng `--basetemp` mới mỗi lượt; pytest có thể xóa path này, nên không trỏ vào thư mục có dữ liệu cần giữ. Nếu tiến trình bị kill cứng/mất điện, kiểm tra DB tạm còn sót trước khi xóa thủ công; không xóa bằng wildcard.

**Phải có 9 passed, không có skipped.** Thiếu biến môi trường `DATABASE_URL` sẽ skip; skip không chứng minh acceptance. CLI/API dùng clock thật: nếu nguồn đã hết freshness, test phải fail và curator phải review lại seed, không sửa clock/timestamps để làm xanh test. Test này cũng được thu thập bởi CI integration hiện có; seed hết hạn có thể làm CI fail có chủ đích.

Output evidence ghi nhận ngày **01/10/2026 (Asia/Saigon)**, Windows, Python 3.11.14, PostgreSQL 17.11/pgvector 0.8.6 local Compose 55432:

```text
dry-run: added=202 updated=0 unchanged=0; database unchanged
import counts: {"capabilities": 15, "categories": 8, "evidence": 30, "models": 0, "providers": 14, "tool_embeddings": 0, "tool_facts": 120, "tools": 15}
re-import: added=0 updated=0 unchanged=202; exact catalog fingerprint unchanged
HTTP: categories=8; pages=3x5; search/filters/empty/422 pass; details=15; provenance/unknown pass; draft/archived hidden
invalid fk (clean): exit=2; catalog unchanged
invalid fk (seeded): exit=2; catalog unchanged
invalid source (clean): exit=2; catalog unchanged
invalid source (seeded): exit=2; catalog unchanged
invalid fact_type (clean): exit=2; catalog unchanged
invalid fact_type (seeded): exit=2; catalog unchanged
mid-transaction failure (clean): exit=3; all earlier writes rolled back
mid-transaction failure (seeded): exit=3; all earlier writes rolled back
9 passed
```

Checks toàn backend trong cùng lượt: **208 unit tests, 84 integration tests**, Ruff check/format và Mypy (16 source files) pass. Lệnh tái hiện (giữ `DATABASE_URL` ở mục 1):

```powershell
.venv/Scripts/python.exe -m ruff check --no-cache apps/api
.venv/Scripts/python.exe -m ruff format --check --no-cache apps/api
.venv/Scripts/python.exe -m mypy --cache-dir .cache/mypy-task0056
$unitTemp = Join-Path '.cache' ('pytest-unit-' + [guid]::NewGuid().ToString('N'))
.venv/Scripts/python.exe -m pytest -p no:cacheprovider --basetemp $unitTemp -m 'not integration and not live' -q
$dbTemp = Join-Path '.cache' ('pytest-integration-' + [guid]::NewGuid().ToString('N'))
.venv/Scripts/python.exe -m pytest -p no:cacheprovider --basetemp $dbTemp -m integration -q
```

Đọc exit/result của từng lệnh; một lệnh sau pass không thay thế lỗi trước đó. Đây là kết quả local, không phải tuyên bố đã chạy GitHub Actions. Sau verification không còn database `ai_atlas_pipeline_*`; subprocess Uvicorn đã được fixture dừng và chờ kết thúc. Container DB vốn đang chạy được giữ nguyên.

Counts là **202 incoming records**: 14 providers + 8 categories + 15 capability definitions + 15 tools + 120 facts + 30 evidence. Joins không được đếm riêng trong CLI summary. 15 tools đều published; 90 facts explicit unknown; relations dùng 10/15 capability definitions. Không có models hoặc embeddings.

Fingerprint SHA-256 lấy toàn bộ columns/rows của providers, models, categories, capabilities, tools, ba bảng tool joins, tool_facts, evidence và tool_embeddings. Vì vậy kiểm tra re-import bao gồm timestamps, revisions, search projection và không nhân đôi evidence, không chỉ so counts.

Lỗi FK/source/type được kiểm trên cả DB sạch và đã seed. Type lỗi bị chặn trước transaction; semantic lỗi bị chặn trước writes. Hai test DB-trigger riêng gây lỗi sau provider write; sequence witness ngoài rollback chứng minh trigger đã thấy write đó, rồi exact catalog fingerprint phải trở về trạng thái ban đầu. Đây là bằng chứng transaction rollback thực sự, không phải historical restore.

Synthetic sentinels chỉ được thêm vào DB tạm dưới trạng thái draft/archived; list/search không chứa chúng và detail trả 404. Public IDs phải khớp chính xác 15 IDs trong seed. API không có cờ synthetic hoặc bộ lọc suy đoán từ tên: không đưa fixtures vào curated files và không publish synthetic data.

## 3. Dry-run, import và re-import vào DB được chọn

Phần này **ghi vào `DATABASE_URL` đã chọn**, khác với verification tự tạo DB tạm. Dùng development DB khi muốn xem seed qua API local. Migrate trước:

```powershell
.venv/Scripts/python.exe apps/api/src/ai_atlas_api/migrations.py up
if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }

$dryJson = .venv/Scripts/python.exe -m ai_atlas_api.curated_cli dry-run --format json `
  data/curated/taxonomy.json data/curated/tools.json
if ($LASTEXITCODE -ne 0) { $dryJson; throw 'Dry-run failed; không import' }
$dry = $dryJson | ConvertFrom-Json
$dry.summary
$dry.changes | Format-Table entity, id, status, changed_fields
```

Review diff trước khi thực hiện block import sau. Trên DB sạch, expected `added=202 updated=0 unchanged=0`. Trên DB đã có seed, counts phụ thuộc trạng thái hiện tại; không xóa DB để ép counts về 202.

```powershell
$importJson = .venv/Scripts/python.exe -m ai_atlas_api.curated_cli import --format json `
  data/curated/taxonomy.json data/curated/tools.json
if ($LASTEXITCODE -ne 0) { $importJson; throw 'Import failed' }
($importJson | ConvertFrom-Json).summary

$repeatJson = .venv/Scripts/python.exe -m ai_atlas_api.curated_cli import --format json `
  data/curated/taxonomy.json data/curated/tools.json
if ($LASTEXITCODE -ne 0) { $repeatJson; throw 'Re-import failed' }
$repeat = $repeatJson | ConvertFrom-Json
$repeat.summary
if ($repeat.summary.added -ne 0 -or $repeat.summary.updated -ne 0 -or `
    $repeat.summary.unchanged -ne 202) { throw 'Re-import không unchanged như mong đợi' }
```

Re-import cùng batch ngay sau import phải là `0/0/202` nếu không có concurrent edits hoặc freshness boundary. `as_of` trong report thay đổi là bình thường; timestamps/revisions trong DB không được đổi. Records omitted được giữ, tool relation arrays là complete sets. Import revalidate dưới lock trong transaction; dry-run không giữ lock cho command import sau đó.

## 4. Chạy API và smoke thủ công

Terminal A, từ repo root, đặt cùng `PYTHONPATH`/`DATABASE_URL` đã import rồi chạy:

```powershell
.venv/Scripts/python.exe -m uvicorn ai_atlas_api.main:app --host 127.0.0.1 --port 8000
```

Terminal B:

```powershell
$base = 'http://127.0.0.1:8000'
Invoke-RestMethod "$base/health/ready"
$categories = Invoke-RestMethod "$base/api/v1/categories"
$categories.data | Format-Table slug, name
$list = Invoke-RestMethod "$base/api/v1/tools?page=1&page_size=5"
$list.pagination
$search = Invoke-RestMethod "$base/api/v1/tools?q=ChatGPT"
$toolId = $search.data[0].id
$detail = Invoke-RestMethod "$base/api/v1/tools/$toolId"
$detail.data | Select-Object name, official_url, last_verified_at, revision
$detail.data.facts | Format-Table key, value, verification_status
$detail.data.evidence | Format-Table fact_key, source_url, checked_at, expires_at
Invoke-RestMethod "$base/api/v1/tools?category=coding-development&pricing_model=unknown"
Invoke-RestMethod "$base/api/v1/tools?api_available=false"
Invoke-RestMethod "$base/api/v1/tools?page=4&page_size=5"
```

Với seed hiện tại: 8 categories; total=15/page_size=5; ChatGPT có official URL và 2 sources; pricing/API/platform/open-source/deployment/offline null/unknown. Filter `api_available=false` trả 0, giống `true`, vì unknown không được diễn giải thành false. Trang 4 rỗng. Bộ kiểm tự động ở mục 2 xác nhận cả 15 details, exact source/date/evidence và error states, không cần đọc output thủ công để đoán pass.

Ctrl+C ở terminal A để dừng Uvicorn. Chỉ dừng container nếu không còn dùng: `docker compose down` giữ volume. Không cần dừng Docker container đang được task khác sử dụng.

## 5. Import failure và freshness

| Exit | Xử lý |
|---|---|
| 0 | Kiểm `status=valid` và summary; dry-run chưa ghi, import đã commit |
| 2 | Xem errors.field/code; sửa JSON/type, stable IDs/FK, nguồn hoặc evidence; chạy lại dry-run trước import |
| 3 | Kiểm DB healthy, migrations, quyền và lock contention; chờ writer khác xong rồi dry-run lại. Không tăng timeout hoặc bỏ validator tùy tiện |
| 4 | Lỗi config/CLI nội bộ; giữ report sanitized, kiểm cấu hình và regression tests; không coi là thành công |

Report lỗi có summary zeros/changes rỗng không phải là một successful no-op. Batch lỗi không commit partial records. Nếu mất kết nối ngay tại commit và client không nhận được kết quả, kiểm lại DB bằng dry-run; không đoán outcome từ lỗi mạng. Re-import batch unchanged là idempotent sau khi xác định DB đã sẵn sàng.

Freshness: `checked_at <= now < expires_at`, tối đa 30 ngày cho pricing và 90 ngày cho các fact khác. Seed ngày 30/09/2026 hết freshness vào **29/12/2026 15:00 UTC**. Không chỉnh dates chỉ để vượt validator.

Khi cần refresh:

1. Curator mở nguồn chính thức, xác minh lại claim và nội dung; giữ stable tool/fact UUID.
2. Thêm evidence với UUID mới, checked_at thực tế, expires_at trong TTL và metadata review. Existing evidence UUID/content bất biến; history cũ không bị ghi đè. Cập nhật last_verified_at sau review thực tế.
3. Nếu đổi value/status cần evidence mới cho fact revision mới; chỉ thêm nguồn cho claim/status không đổi thì không bump **fact revision**. Tool revision cũng giữ nguyên nếu tool metadata/relations không đổi; cập nhật `last_verified_at` ở bước 2 là thay đổi metadata nên tăng tool revision. Dry-run trên DB đích rồi review/import batch.
4. Nếu chưa xác minh được, không giữ claim dưới nhãn verified bằng cách gia hạn giả. Có thể dùng unverified hoặc null/unknown đúng schema; phải bỏ capability/model relations không còn verified true. Published tool cần identity verified fresh; nếu không đáp ứng, chuyển draft/archived tường minh. Identity metadata/value phải đồng nhất.

API hạ fact hết hạn thành unverified, nguồn cũ vẫn hiển thị ngày để minh bạch; không tự ghi lại DB hay tự archive tool. Importer không tự downgrade hoặc fetch nguồn. Synthetic fixtures, historical restore, embeddings và AI recommendations nằm ngoài quy trình này.
