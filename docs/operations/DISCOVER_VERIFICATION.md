# Discover — verification và bàn giao TASK-006.7

Phạm vi: Home → Explorer → tool detail hiện có, hai locale `vi/en`, hai theme `dark/light`, keyboard và responsive states. Không thêm feature, không gọi Gemini hoặc fetch source URLs. Automated Journey A E2E/CI thuộc TASK-007; các scripts dưới đây là audit local opt-in, cần API và curated seed thật.

## Lỗi đã sửa

Footer sticky của filter drawer che control đang focus: trong viewport 360×800, pricing select ở y=690–734 trong khi footer bắt đầu y=667. Tab vẫn nằm trong dialog nhưng người dùng không thấy control được chọn.

Drawer hiện giữ header/actions bên ngoài vùng scroll, chỉ fields scroll với `min-height: 0` và padding cho focus ring. Regression browser kiểm 40 lần Tab/Shift+Tab, hit-test control đang focus và trả focus về trigger bằng Escape, tại 320/360/768/1024px trong cả vi/en. Bản trước fail tại pricing; bản sau pass 8 combinations.

## Commands

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
5. Chạy frontend checks. TASK-007 tiếp tục xây automated E2E Journey A và error-path coverage trong CI.
