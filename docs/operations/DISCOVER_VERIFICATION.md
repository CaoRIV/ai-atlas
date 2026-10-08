# Discover — verification và E2E operation

Phạm vi: Home → Explorer → tool detail hiện có, hai locale `vi/en`, hai theme `dark/light`, keyboard và responsive states. Không thêm feature, không gọi Gemini hoặc fetch source URLs. TASK-007.1 đã tự động hóa real-stack foundation; TASK-007.2 đã tự động hóa Journey A happy path vi/en. TASK-007.3 đã tự động hóa negative/publication paths và race recovery. CI gate thuộc 007.4.

## Lỗi đã sửa

Footer sticky của filter drawer che control đang focus: trong viewport 360×800, pricing select ở y=690–734 trong khi footer bắt đầu y=667. Tab vẫn nằm trong dialog nhưng người dùng không thấy control được chọn.

Drawer hiện giữ header/actions bên ngoài vùng scroll, chỉ fields scroll với `min-height: 0` và padding cho focus ring. Regression browser kiểm 40 lần Tab/Shift+Tab, hit-test control đang focus và trả focus về trigger bằng Escape, tại 320/360/768/1024px trong cả vi/en. Bản trước fail tại pricing; bản sau pass 8 combinations.

## Automated real-stack foundation — TASK-007.1

Yêu cầu: Node/pnpm theo workspace, Python environment đã sync và PostgreSQL local. Role trong admin URL phải có quyền tạo/xóa database; không dùng production credentials. Runner không đọc Gemini key và tests không mở official source URL.

```powershell
# Khi Compose dùng cổng host 55432:
$env:E2E_DATABASE_ADMIN_URL = 'postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:55432/ai_atlas'
.\scripts\pnpm.ps1 test:e2e:discover
```

Nếu PostgreSQL ở `127.0.0.1:5432` với credentials mặc định thì không cần đặt admin URL. Optional overrides: `E2E_API_PORT`, `E2E_WEB_PORT`, `E2E_BASE_URL`, `E2E_STARTUP_TIMEOUT_MS`, `E2E_ARTIFACT_ROOT`. Không đặt ports thì runner chọn hai loopback ports riêng; custom `E2E_BASE_URL` phải khớp web origin.

Runner tạo database `ai_atlas_e2e_<random>`, migrate, import curated seed và từ chối chạy nếu summary khác `202 records/15 tools`. Sau đó helper thêm một archived fixture riêng từ `e2e/fixtures/archived-tool.json` vào database tạm (không nằm trong 202 curated records); public catalog vẫn có 15 tools. Runner build Next production vào `.next-e2e`, start FastAPI/Next, chờ `/health/ready` và web readiness với timeout rồi chạy Chromium. `SIGINT`, `SIGTERM`, startup/test failure và success đều đi qua teardown: đóng process tree, xóa database tạm và build output. Success xóa run directory; failure giữ `api.log`, `web.log`, Playwright trace/screenshot tại `.cache/discover-e2e/<run-id>/`. Artifacts bị gitignore và không chứa raw prompt/token vì flow không gọi AI.

Evidence 06/10/2026, Windows/Chromium: smoke real-stack pass `1` test với auto ports và với `E2E_BASE_URL`; seed đúng `202 records/15 tools`. Sau success không còn database `ai_atlas_e2e_%`, `.next-e2e` hay run artifact. Forced API bind failure trả exit khác `0`, giữ `api.log`, vẫn xóa database/build output; artifact kiểm chứng đã được dọn. Frontend ESLint, web + E2E strict typecheck, 35 Vitest cases và isolated production build pass; backend Ruff check/format, mypy và 208 unit cases pass. Smoke xác nhận API/BFF/UI và detail-link contract; không thay thế Journey A cases của 007.2/007.3.

## Journey A happy path — TASK-007.2

Cùng command `test:e2e:discover` chạy thêm `e2e/discover-journey.spec.ts`. Mỗi locale bắt đầu từ Home, tìm ChatGPT, chọn category `chatting-assistants` và pricing `unknown`, rồi kiểm canonical URL `/explorer?q=ChatGPT&category=chatting-assistants&pricing_model=unknown` cùng đúng một result. Detail phải có OpenAI, capability/status, unknown pricing và evidence checked/expires; Back phải giữ search, filters, effective sort và page 1.

Official link phải là `https://chatgpt.com/`, `_blank`, `noopener noreferrer`; test cài route interception trước click, xác nhận popup URL, nội dung cục bộ và `window.opener === null`. Không có request nào đi ra official host. Test dùng role/name; chỉ dùng URL và attribute cho contract mà accessibility tree không biểu diễn.

Evidence 07/10/2026, Windows/Chromium: real stack với curated seed `202 records/15 tools` pass `3` cases (`1` foundation, Journey A vi + en) trong `19.4s`; isolated production build, root ESLint/strict typecheck và 35 Vitest cases pass. Runner đã dọn database, services, `.next-e2e` và success artifacts. Browser smoke riêng ở 1366×900 đã kiểm trực quan Home, filtered Explorer, expanded evidence detail và back-state; English count defect `1 results` được sửa thành `1 result`. Backend không đổi nên không chạy lại suite backend của TASK-005.6.

## Negative/publication paths và race recovery — TASK-007.3

Cùng command `test:e2e:discover` chạy `e2e/discover-recovery.spec.ts` với 5 cases:

- Query ChatGPT + API=false trả real 200/empty; reset bỏ search/filter và phục hồi 15 tools.
- Category không tồn tại trả real 422; UI giữ request ID, reset về catalog.
- Archived fixture thật bị loại khỏi list/search, detail API trả 404; archived UUID, absent UUID và malformed ID đều trả public HTML 404, không lộ private name/slug/description/official URL trong HTML hoặc DOM. Malformed ID ở backend API vẫn theo contract 422; page UI map sang 404.
- Chỉ request tools đầu tiên được intercept thành BFF 503. UI giữ search/category/pricing/sort trong URL và request ID; Retry gọi cùng URL tới real backend, phục hồi ChatGPT và xóa error.
- Response ChatGPT lấy bằng `route.fetch()` từ backend thật được giữ bằng promise gate. Trong lúc chờ vẫn thấy Gemini cũ; search Claude trả result mới, request ChatGPT bị abort. Sau release response cũ, URL/card vẫn là Claude và không hiện error. Không dùng sleep để đoán thứ tự. Đây là browser cancellation recovery; existing unit tests kiểm sequence guard với late promise độc lập với abort.

Fixture được seed sau import bằng helper chỉ nhận local admin URL + tên `ai_atlas_e2e_<16 hex>`; connection override database bằng tên tạm. Helper kiểm row archived tồn tại để không nhầm archived với absent. Không fetch URL `.invalid` trong fixture. Teardown xóa database cùng fixture cả khi suite fail.

Evidence 08/10/2026, Windows/Chromium: **8/8 E2E cases pass trong 11.6s**, isolated production build pass; root lint, strict typecheck (gồm E2E), **35/35 Vitest** và Ruff/format/mypy DB helper pass. First run phát hiện locator alert trùng Next route announcer; đã scope bằng Results region. Parallel lint/E2E phát hiện generated `.next-e2e` chưa được ignore; đã thêm ignore và chạy lại lint pass. Không thay đổi backend application hay UI behavior; backend suite 208 unit/84 integration không chạy lại. Hậu kiểm 0 temporary databases, services và `.next-e2e` đã dọn; success artifacts được xóa. TASK-007.4–007.5 vẫn Todo.

Artifacts của first failed run được giữ tại `.cache/discover-e2e/fa5a2f1128527f07/` để điều tra locator; optional cleanup bị execution policy chặn. Database tạm của run đó đã được runner xóa. Compose DB đã trả về trạng thái stopped sau verification.

## Manual TASK-006.7 commands

Từ repo root, chạy riêng từng command và kiểm exit code:

```powershell
.\scripts\pnpm.ps1 --filter @ai-atlas/web lint
.\scripts\pnpm.ps1 --filter @ai-atlas/web typecheck
.\scripts\pnpm.ps1 --filter @ai-atlas/web test
.\scripts\pnpm.ps1 --filter @ai-atlas/web build
```

Chuẩn bị database đã migrate/import theo [curated operating guide](CURATED_CATALOG.md). Role/DB dùng cho audit nên là local test; không dùng production. Chạy API trong terminal riêng:

```powershell
$env:PYTHONPATH = 'apps/api/src'
$env:DATABASE_URL = 'postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:55432/ai_atlas'
.venv/Scripts/python.exe -m uvicorn ai_atlas_api.main:app --host 127.0.0.1 --port 8000
```

Terminal web, đặt server-only origin trước khi start:

```powershell
$env:API_BASE_URL = 'http://127.0.0.1:8000'
.\scripts\pnpm.ps1 --filter @ai-atlas/web exec next start --hostname 127.0.0.1 --port 3000
```

Audit scripts cần Node và Playwright/Chromium + axe-core cài sẵn trên máy; chúng không cài dependencies hay sửa DB. Nếu packages resolve được từ repo thì có thể bỏ `PLAYWRIGHT_MODULE`/`AXE_CORE_MODULE`. Nếu browser là bản do Playwright tương ứng quản lý thì bỏ `CHROMIUM_EXECUTABLE`. Ví dụ paths của runtime đã dùng trên máy kiểm chứng (thay đường dẫn nếu máy khác):

```powershell
$env:DISCOVER_BASE_URL = 'http://127.0.0.1:3000'
$env:PLAYWRIGHT_MODULE = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'
$env:CHROMIUM_EXECUTABLE = Join-Path $env:LOCALAPPDATA 'ms-playwright/chromium-1228/chrome-win64/chrome.exe'
$env:AXE_CORE_MODULE = Join-Path (Get-Location) 'node_modules/.pnpm/axe-core@4.13.0/node_modules/axe-core'
node scripts/audit-discover.cjs
node scripts/check-discover-focus.cjs
```

`audit-discover.cjs` chỉ nhận local host, dùng browser context mới và tool đầu tiên từ API thật. Audit 3 pages × 6 widths × 2 locales × 2 themes = **72 scans**. Lưu report gồm axe violations/incomplete, reflow và page errors cùng screenshots vào `.cache/discover-audit/`. Exit khác 0 nếu không seed, route lỗi, overflow hoặc axe violations. **Incomplete vẫn cần review thủ công**, không được đọc “PASS” như chứng nhận accessibility.

`check-discover-focus.cjs` kiểm riêng drawer trên local seed (8 categories). Browser mới nên không ảnh hưởng locale/theme preference của browser người dùng. Seed thay số categories cần tăng số Tab để vẫn đi hết mọi control. Cả hai scripts luôn đóng browser khi lỗi; không tự stop web/API do operator chạy. Dừng bằng Ctrl+C trong terminals khi xong, không xóa DB volume.

## Evidence ngày 05/10/2026

Môi trường: Windows, Next production build, Playwright 1.62.1, axe-core 4.13.0. Audit thực tế dùng PostgreSQL tạm riêng, migrations + import **202 records/15 tools**, FastAPI8006 và Next3006; không sửa development catalog. Database và processes tạm đã được cleanup sau mỗi lượt.

| Kiểm tra | Kết quả |
|---|---|
| ESLint / strict typecheck / production build | Pass |
| Vitest | 35 tests pass; 2 mới cho locale/draft/error preservation |
| Home/Explorer/detail: 320, 360, 768, 1024, 1366, 1920px; vi/en; dark/light | 72 axe scans, 0 violations, không horizontal overflow hoặc page errors |
| Drawer en/vi, mở evidence, empty, 422, 404, forced-colors + reduced-motion | 7 state scans, 0 violations |
| Locale switch khi drawer đang mở (storage event từ tab thứ hai) | Giữ draft categories/API=false, applied URL và query |
| Modal keyboard | Full Tab/Shift+Tab cycle, focus visible/trapped; Escape trả focus về trigger; 8 combinations pass sau fix |
| Home → Explorer → detail → Explorer | Dữ liệu thật; query/pricing filter giữ nguyên; nguồn có checked/expires; official HTTPS link an toàn |
| Skip link / native evidence disclosure | Enter đến main; Enter mở nguồn và dates |
| Reduced motion | Drawer animation còn 0.01ms; không chạy animation dài |
| Forced colors | Canvas trắng/text đen, outline/control boundaries vẫn nhìn được; đã xem screenshot viewport |
| Archived và invalid ID | HTTP404, không có nội dung private |

Axe có **3 state results cần manual review**: hai modal scans có `aria-hidden-focus`; forced-colors modal có `aria-hidden-focus` và `color-contrast`. Background được Radix ẩn khi dialog mở; đã kiểm Tab/Shift+Tab không thoát và Escape phục hồi focus. High-contrast được kiểm dưới Chromium forced-colors (computed Canvas trắng/text đen) cùng screenshot; không suy từ theme RGB thông thường. Không suppress rule hoặc biến incomplete thành pass tự động.

Matrix 72 scans không có incomplete. Screenshots desktop/mobile đã kiểm trực quan. Không đo NVDA/screen-reader compatibility toàn diện, không kiểm mọi palette Windows hoặc browser khác; không tuyên bố chứng nhận WCAG. Những giới hạn này không thay thế các checks đã nêu.

## Checklist vận hành trước khi đổi Discover UI

1. Đổi locale tại Home, Explorer và detail: giữ route/query/filter/page; đổi lúc modal mở phải giữ draft. Error/empty/loading labels và request ID phải vẫn đúng.
2. Tab tới skip link, search, sort, filters/chips/pagination; mở drawer, đi hết controls theo hai chiều và Escape. Focus không bị footer/header che.
3. Kiểm empty (`api_available=false` với seed hiện tại), 422 (category không tồn tại), 404 và API unavailable/retry; không dùng fallback catalog giả.
4. Chạy matrix audit, đọc cả violations và incomplete; kiểm screenshots, reduced motion và forced colors. Không tự approve visual changes chỉ vì tests xanh.
5. Chạy frontend checks và `test:e2e:discover`. Negative/publication paths cùng race recovery đã có ở TASK-007.3; CI gate tiếp theo thuộc 007.4.
