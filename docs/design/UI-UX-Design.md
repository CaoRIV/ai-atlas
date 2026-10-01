# AI Atlas — UI/UX Design Specification

Ngày: 01/10/2026 · Phiên bản: 0.2 · Trạng thái: foundation shell TASK-006.2 đã triển khai và browser-audit; Discover feature screens chưa triển khai.

Tài liệu chuyển brief “Minimal Developer SaaS + AI-native Product + Data-rich Discovery Platform” thành quy tắc giao diện và hành vi cụ thể. Đối tượng ưu tiên là developers và sinh viên; thành công là người dùng tìm được tool, hiểu căn cứ của stack và quản lý được stack cá nhân.

Đây là file UI/UX duy nhất của dự án, đảm nhiệm nội dung `UI_UX_GUIDELINES.md` được đề cập trong brief. Không tạo thêm bản sao với tên khác. Phạm vi lần soạn này chỉ là tài liệu, không triển khai ứng dụng, cài thư viện hoặc thay backend contracts.

## 1. Nguồn sự thật và kết quả audit

Đọc [AGENTS](../../AGENTS.md), [README](../../README.md), [PRD](../product/PRD.md), [User flows](../product/USER_FLOWS.md), [Architecture](../architecture/SYSTEM_ARCHITECTURE.md), [Data model](../architecture/DATA_MODEL.md), [API](../architecture/API_DESIGN.md) và [AI spec](../architecture/AI_RECOMMENDATION.md) trước khi code.

Repository hiện có app shell responsive, semantic tokens hai theme, dark/light/system pre-paint, locale `vi/en`, accessible drawer, home foundation, Catalog BFF boundary và web health route. Chưa có Explorer/tool detail/Builder/My Stacks hoặc mockup baseline đã duyệt; các feature component/route còn lại dưới đây vẫn là thiết kế dự kiến. PRD/Accepted ADR và API contracts có ưu tiên cao hơn tài liệu này khi có xung đột; UI không tự mở rộng payload để phù hợp mockup.

### 1.1. Quyết định thiết kế

| ID | Quyết định | Lý do / phương án đã cân nhắc |
|---|---|---|
| UXD-001 | Một app shell, sidebar desktop + header gọn | Giữ ba hành trình dễ tìm; header-only tiết kiệm chiều ngang nhưng kém phân biệt discovery và workspace; dashboard nhiều panel gây phân tán |
| UXD-002 | Dark-first, light mode đầy đủ qua semantic tokens | Phù hợp developer workspace; không dùng bộ màu riêng tùy trang hoặc chỉ đảo màu tự động |
| UXD-003 | Builder là form có kết quả cấu trúc trên cùng trang | Người dùng nhìn rõ constraints và vai trò; chat UI khiến khó phân biệt dữ liệu đã xác minh; wizard extraction riêng chưa có API |
| UXD-004 | Card grid cho Explorer, danh sách rows cho My Stacks | Discovery cần scan mô tả; workspace cần title, trạng thái và thời gian. Chưa thêm toggle grid/list chưa được chứng minh cần |
| UXD-005 | Ordered workflow, không graph editor | Dễ đọc trên mobile, đúng MVP; edges không evidence phải hiện “Cần kiểm thử” |
| UXD-006 | UI English và tiếng Việt, giữ AI Atlas và technical identifiers | Chủ dự án chốt tại TASK-001/ADR-012; controls, labels, loading/empty/error và accessibility copy có đủ hai locale |

Linear, Vercel, Raycast và Hugging Face chỉ là tham chiếu về tính rõ ràng, mật độ và navigation trong brief; không coi đây là audit giao diện hiện hành của các sản phẩm đó, không sao chép branding/layout.

### UI language theo ADR-012

Dùng locale `en` và `vi`, mặc định `vi` khi chưa có preference. Selector `English / Tiếng Việt` trong app shell; lưu preference browser, không lưu secret. Đổi locale giữ route, filters, pagination và draft; cập nhật document lang và format ngày/số theo locale. Copy tiếng Việt bên dưới là bản tham chiếu, cần dictionary tiếng Anh tương ứng khi triển khai. Không dịch tool/model names, URLs, enum IDs, evidence hoặc nội dung do user/AI tạo. Error labels ánh xạ từ API error code; không phụ thuộc chuỗi message backend để đổi ngôn ngữ. Không thêm locale field vào API ở scope này. Kiểm tra cả hai locale ở 360px, keyboard và mọi trạng thái.

### 1.2. Điều chỉnh brief theo MVP hiện tại

| Gợi ý trong brief | Quyết định áp dụng |
|---|---|
| Popular categories / trending tools | Hiện “Danh mục” và “Công cụ trong thư viện”; không có popularity data để gọi trending hoặc hiển thị số người dùng |
| Product logo | API không có logo_url: dùng monogram chữ đầu + nền trung tính; chỉ thêm official assets khi có nguồn, quyền sử dụng và cách phân phối đã chốt |
| Capabilities trên tool card | ToolSummary chưa có capabilities: card không hiển thị field này, không gọi detail N lần để lấp card; detail/result mới hiển thị khi có dữ liệu |
| Related tools | Hoãn block riêng; category link dẫn về Explorer đã lọc, không gọi đó là recommendation similarity |
| Lưu riêng tool / favorites | Không có API favorites; không hiện nút bookmark. Thêm tool thực hiện trong editor của stack |
| Technical experience / preferred tools | Không có dedicated request fields; dùng preference `beginner_friendly` hoặc viết vào objective, không thêm field giả |
| Preview extraction trước generation | API trả đồng bộ một lần; hiển thị requirements khi nhận response, chỉnh form và gửi lại; không tạo bước “xác nhận extraction” giả |
| Multi-step progress, cancel job | Không có streaming/status/cancel endpoint; chỉ hiển thị pending chung, không phần trăm, không hứa hủy tính phí khi rời trang |
| Logo các tools trên My Stacks list | StackSummary chỉ có item_count; list hiển thị số thành phần, tool identities nằm trong detail |
| “Compare” và workflow editor | Chưa có navigation/button trong MVP; không dùng nút disabled trang trí cho tính năng tương lai |

## 2. Ngôn ngữ thị giác

Giao diện giống một bàn làm việc tra cứu kỹ thuật: nền phẳng, text rõ, đường phân chia tiết chế, một điểm nhấn tím cho hành động chính. Mật độ cao nằm ở cách căn hàng và nhóm metadata, không ở việc thu nhỏ chữ. Chỉ một primary action trong mỗi nhóm thao tác; khoảng trắng phân chia phần lớn, separators phân chia facts.

Không dùng full-screen hero, gradient tím dày, glow borders, glassmorphism toàn ứng dụng, ảnh AI trang trí, card lồng nhiều tầng hoặc chuyển động liên tục. Tool cards có border nhẹ, không cần shadow thường trực. Builder dùng nhãn vai trò và thứ tự để tạo bản sắc, không dùng hiệu ứng “AI đang suy nghĩ” giả.

## 3. Design tokens

Tokens dưới đây là nguồn màu duy nhất cho frontend tương lai. Ánh xạ vào CSS variables và Tailwind theme khi scaffold; không rải hex trong page components. `brand` phục vụ nhận diện, `action-*` phục vụ trạng thái tương tác, `status-*` phục vụ ý nghĩa.

### 3.1. Bảng màu cho hai themes

| Token | Dark | Light | Cách dùng |
|---|---|---|---|
| `bg-canvas` | `#0B0F19` | `#F7F8FC` | Nền ứng dụng |
| `bg-surface` | `#141A29` | `#FFFFFF` | Cards, panel, inputs |
| `bg-subtle` | `#1B2335` | `#F1F4F9` | Hover trung tính, nhóm metadata |
| `bg-overlay` | `#1B2335` | `#FFFFFF` | Dialog, menu, drawer |
| `border-subtle` | `#30384B` | `#DDE2EC` | Phân chia trang trí, không dùng làm dấu hiệu duy nhất của control |
| `border-control` | `#71809B` | `#768299` | Biên input/control cần nhận diện |
| `text-primary` | `#F8FAFC` | `#172033` | Heading và body |
| `text-secondary` | `#9CA3B5` | `#526075` | Metadata/helper vẫn cần đọc được |
| `text-placeholder` | `#9CA3B5` | `#526075` | Ví dụ trong input; không thay label |
| `brand` | `#7065F0` | `#7065F0` | Nhận diện, không mặc định làm nền chữ trắng |
| `action-primary` | `#6256DB` | `#6256DB` | Nền nút chính |
| `action-primary-hover` | `#574BC7` | `#574BC7` | Hover nút chính |
| `action-primary-pressed` | `#4E43B4` | `#4E43B4` | Pressed nút chính |
| `text-on-action` | `#FFFFFF` | `#FFFFFF` | Chữ nút primary/destructive |
| `text-accent` | `#A79FFF` | `#5E52CB` | Link/active label |
| `bg-selected` | `#292447` | `#EEEBFF` | Navigation/filter được chọn, đi cùng text-accent |
| `focus-ring` | `#A79FFF` | `#5E52CB` | Outline 2px, offset 2px |
| `status-success-text` | `#86EFAC` | `#166534` | Lưu thành công/fact có evidence |
| `status-success-bg` | `#123026` | `#EAF8EF` | Nền semantic badge |
| `status-warning-text` | `#FCD34D` | `#854D0E` | Partial/stale/cần làm rõ |
| `status-warning-bg` | `#342A16` | `#FFF6DF` | Nền semantic badge |
| `status-error-text` | `#FCA5A5` | `#B91C1C` | Lỗi/form validation |
| `status-error-bg` | `#371F29` | `#FEECEC` | Nền error banner |
| `status-info-text` | `#93C5FD` | `#1D4ED8` | Hướng dẫn/trạng thái thông tin |
| `status-info-bg` | `#172D49` | `#EBF3FF` | Nền info banner |
| `action-destructive` | `#B91C1C` | `#B91C1C` | Nút xác nhận xóa |
| `scrim` | `rgba(0,0,0,0.64)` | `rgba(15,23,42,0.40)` | Nền sau modal |

Chữ trắng trên brand `#7065F0` có contrast tính toán khoảng 4,37:1; trên action-primary `#6256DB` khoảng 5,42:1. Vì vậy brand không dùng làm nền nút chữ trắng nhỏ. Border-subtle không đủ thay thế focus-ring/border-control. Semantic colors luôn đi cùng icon và label; không tô cả recommendation thành màu xanh để hàm ý “tốt nhất”.

Theme control có ba lựa chọn “Tối / Sáng / Theo hệ thống”. Nếu chưa có preference, mặc định Tối theo brief. Lưu preference không nhạy cảm bằng cookie hoặc local storage; khởi tạo trước paint để tránh flash, không ghi analytics chứa dữ liệu người dùng. Khi chọn System mới theo thay đổi OS. Components dùng cùng token names trong cả themes; logo fallback và empty/error states cũng phải hỗ trợ light mode.

Disabled dùng bg-subtle + text-secondary + thuộc tính disabled/aria-disabled phù hợp, không chỉ giảm opacity khiến text khó đọc. Hover của action không được đổi ý nghĩa; destructive hover dùng cùng semantic family, phải kiểm contrast trước khi bổ sung token.

### 3.2. Typography

Chọn **Inter** cho UI và **Geist Mono** cho technical values; fallback `system-ui, sans-serif` và `ui-monospace, monospace`. Self-host font khi triển khai và kiểm tra dấu tiếng Việt; nếu chưa có assets dùng system fallback. Không phụ thuộc font tải thành công để layout hoạt động.

| Style | Size / line-height | Weight | Ứng dụng |
|---|---|---|---|
| Home headline | 40/48px desktop, 30/38px mobile | 600 | Một headline ngắn, tối đa khoảng 2 dòng ở desktop |
| Page title | 28/36px desktop, 24/32px mobile | 600 | Một H1/màn hình |
| Section title | 20/28px | 600 | H2, nhóm kết quả |
| Card title | 16/24px | 600 | Tool/stack title, cho wrap |
| Body | 14/22px | 400 | Description, rationale, facts |
| Input / long reading | 16/24px | 400 | Form, nội dung nhập trên mobile |
| Label / action | 14/20px | 500 | Labels, buttons |
| Metadata / badge | 12/18px | 400/500 | Ngày kiểm chứng, category, field phụ |
| Technical | 12–13/20px | 400 | Model ID, request ID; hỗ trợ wrap/copy |

Không dùng chữ dưới 12px. Body width khoảng 65–75 ký tự/dòng; rationale dài wrap đầy đủ. Card description có thể clamp 2 dòng vì có detail route; không clamp error/gaps/giá có điều kiện. Dates và số lượng dùng tabular numerals; tránh uppercase cả câu tiếng Việt.

### 3.3. Spacing, shape và motion

- Scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64px. Gap card 16px; card padding 20px desktop/16px mobile; major sections 32px/24px.
- Radius: 6px badge, 8px input/button, 12px card/dialog; pills chỉ cho filter chips. Không thay radius ngẫu nhiên theo trang.
- Controls: cao tối thiểu 44px; icon buttons có vùng hit 44×44px, icon 18–20px. Tool avatar 40×40px; detail avatar 56×56px.
- Shadow: card không shadow mặc định; overlay dùng `0 16px 48px rgba(0,0,0,0.24)` dark hoặc `0 12px 32px rgba(15,23,42,0.12)` light.
- Layers: base 0, sticky shell 20, dropdown 30, scrim 40, dialog/drawer 50, toast 60. Không để dropdown sau backdrop.
- Motion: hover/focus 120ms, expand/dialog 160–200ms, ease-out. Không stagger cards, floating decoration hoặc animation vô hạn ngoài loading cần thiết.
- `prefers-reduced-motion`: bỏ slide/scale/shimmer/spinner rotation, giữ text “Đang tải…” và static indicator. Không dùng motion để thay thông báo trạng thái.

## 4. Information architecture và app shell

| UI route dự kiến | Tên hiển thị | Auth | Mục tiêu |
|---|---|---|---|
| `/` | AI Atlas | Public | Chọn khám phá hoặc xây stack |
| `/explorer` | Khám phá | Public | Search/filter catalog |
| `/tools/[tool_id]` | Tool name | Public | Đọc facts và nguồn |
| `/builder` | Tạo AI Stack | Trước generation | Mô tả mục tiêu, xem structured result |
| `/my-stacks` | Stack của tôi | Có | Danh sách private stacks |
| `/my-stacks/new` | Tạo stack thủ công | Có | Title, purpose, items |
| `/my-stacks/[stack_id]` | Stack title | Có | Detail và edit mode trong cùng page |

Đây là routes frontend, không đổi paths `/api/v1`. Auth-before-Build vẫn phụ thuộc ADR-007 như PRD; thiết kế hiện dùng baseline đó. Người chưa login được soạn form trước, nút ghi “Đăng nhập để tạo stack”; không gửi AI request trước auth.

Desktop ≥1280px: sidebar 216px, header 56px, main padding 32px. Sidebar có brand về `/`, nhóm “Khám phá” gồm Khám phá/Tạo AI Stack, nhóm “Cá nhân” gồm Stack của tôi. Footer sidebar chỉ có tài khoản và theme khi phù hợp; không thêm workspace switcher, notifications hoặc billing.

Từ 768 đến 1279px: header chứa brand, search trigger, account, theme và nút menu; ba destinations nằm trong menu drawer để dành chiều rộng cho dữ liệu. Mobile <768px dùng cùng pattern, labels trong drawer luôn có text, current route có `aria-current=page`. Không dùng icon-only rail buộc đoán chức năng.

Global search là điều hướng về Explorer với `q`, không phải search private stacks hoặc command palette. Ở Explorer, search chính là input của page, không tạo hai input cạnh tranh. Ở mobile, search trigger mở form gọn trong header/dialog; Enter chuyển `/explorer?q=...`, không thêm autocomplete endpoint.

Account anonymous hiển thị “Đăng nhập”; authenticated hiển thị display_name hoặc “Tài khoản” và “Đăng xuất”. Không tạo trang profile/settings chưa có contract. Logo AI Atlas dùng wordmark text ban đầu; không cần asset tạo bằng AI.

## 5. Responsive layout

| Viewport | Content padding | Explorer | Builder / detail | Navigation |
|---|---|---|---|---|
| 320–767px | 16px | 1 cột; filter drawer | 1 cột theo thứ tự DOM | Header + drawer |
| 768–1023px | 24px | 2 cột nếu card ≥260px; filter drawer | 1 cột, inputs có thể 2 cột | Header + drawer |
| 1024–1279px | 24px | 2 cột + filter rail 200px | 2 cột nếu đủ chiều rộng | Header + drawer |
| ≥1280px | 32px | 2–3 cột + filter rail 200px; 4 cột chỉ nếu đủ ≥260px/card | Main + summary rail 280px | Sidebar 216px |

Content max-width 1440px trong vùng main; Builder max-width 1120px, detail 1120px; căn giữa trong vùng này. Grid co theo chiều rộng khả dụng, không dựa số cột cứng trên màn hình có sidebar. Vùng main tối thiểu 0 (`min-width:0`), URLs/IDs dài `overflow-wrap:anywhere`.

Ở 1366×768, người dùng thấy page title và search/form action đầu tiên mà không cuộn qua hero trang trí. Hero home là padding nội dung, không height 100vh. Ở mobile dialog dùng tối đa `calc(100dvh - 32px)`, body cuộn, footer không che input khi bàn phím bật. Sticky header/actions có scroll padding để focus và error không bị che; không cố định nút Save phía dưới nếu che nội dung.

## 6. Screen specifications

### 6.1. Home — `/`

**Mục đích:** phân biệt ngay hai đường đi, không trở thành landing page marketing dài.

Thứ tự nội dung: headline → value proposition → search → hai đường đi → categories → 6 tools đầu từ catalog → footer gọn. Copy đề xuất:

- H1: “Tìm công cụ AI. Xây stack phù hợp.”
- Supporting: “Khám phá công cụ theo nhu cầu và kết hợp thành quy trình có căn cứ.”
- Search label: “Bạn đang tìm công cụ nào?”; placeholder: “Tên công cụ hoặc tác vụ…”; submit “Tìm công cụ”.
- Primary link: “Tạo AI Stack”; secondary link: “Khám phá thư viện”.

Categories hiển thị các category từ API; chọn dẫn tới Explorer có filter. Tools dùng `GET /tools?page=1&page_size=6&sort=name`, không gắn nhãn phổ biến/nổi bật nếu không có selection data. API chưa sẵn sàng hiển thị skeleton/error block; không thay bằng tên/giá giả trên production. Không nêu “100+ tools” đến khi API total thật xác nhận.

Hero ≤ khoảng 320px ở desktop thông thường; không height cứng khi text zoom. Không testimonials, usage counters, sponsors hoặc logo wall không có dữ liệu.

### 6.2. AI Explorer — `/explorer`

Thứ tự: H1 + mô tả ngắn → Search → filter chips và results count → sort → grid → pagination. Desktop filters nằm rail bên trái grid; mobile/tablet nút “Bộ lọc (N)” mở drawer. N là số giá trị filter đã áp dụng, không tính q/sort/page.

```text
App shell
Khám phá công cụ AI
[Tìm theo tên hoặc tác vụ........................]
[Category ×] [Có API ×]  Xóa bộ lọc      N kết quả
Filters (desktop)  |  Sắp xếp [Tên A–Z]
                   |  Tool card   Tool card
                   |  Tool card   Tool card
                   |  [Trước]  Trang 1 / N  [Sau]
```

Search debounce 300ms sau khi composition tiếng Việt kết thúc; Enter gửi ngay. Mỗi lần đổi query/filter reset page=1, giữ sort nếu hợp lệ. Khi q trống bỏ relevance và trở về name. URL là nguồn applied state; back/forward khôi phục query/filters/page. Debounce dùng replace để không tạo lịch sử từng ký tự; áp filter/đổi page chủ động có thể push. Response cũ không được đè response mới.

Filters: categories multi-select OR; pricing/platform single-select; API/open-source mỗi nhóm “Tất cả / Có / Không”. “Tất cả” bỏ param, không gửi false. API/open-source false chỉ nghĩa fact false đã xác minh, không bao gồm unknown. Pricing có lựa chọn “Chưa xác minh”; chú thích filter này cũng gồm unknown/unverified/stale theo contract. Các nhóm kết hợp AND.

Desktop filter áp dụng ngay. Mobile drawer có draft selection: “Áp dụng” commit một lần, “Hủy” hoặc Escape bỏ draft; “Xóa lựa chọn” chỉ reset draft trong drawer. Sau áp dụng trả focus nút Bộ lọc và announce số kết quả khi response đến. Không hiển thị preview count từ dữ liệu chưa request. Applied chips xóa ngay một filter; “Xóa bộ lọc” giữ q, “Xóa tìm kiếm và bộ lọc” trong empty state xóa cả hai.

Sort chỉ có relevance khi q khác rỗng, name và updated; không rating/popularity. Pagination hiển thị total từ API, không suy số lượng từ trang hiện tại; mặc định 20/page theo API, grid hàng cuối có thể thiếu card. Không infinite scroll trong MVP.

**ToolCard:** monogram → name → description tối đa 2 dòng → tối đa 2 categories và “+N” dạng text → pricing label → link “Xem chi tiết”. Title/link detail có accessible name chứa tool name. Card container không nested link/button; không bắt mọi click text thành navigation. Heights đồng đều trong hàng bằng layout stretch, không cắt title tiếng Việt dài.

Price model labels: free “Miễn phí”, freemium “Có gói miễn phí”, paid “Trả phí”, usage_based “Theo mức dùng”, contact “Liên hệ”, unknown “Chưa xác minh giá”. Chỉ dùng label khẳng định khi verification_status verified; unverified có text “Cần xác minh giá”, không dùng màu xanh free. Không hiển thị số tiền ToolSummary chưa cung cấp.

**Nghiệm thu:** q/filters trong URL, keyboard chọn/xóa được; không match có reset rõ; 422 query sai có thông báo và cách reset; HTTP lỗi có retry giữ query; skeleton cùng kích thước grid tránh nhảy layout.

### 6.3. Tool detail — `/tools/[tool_id]`

Header: breadcrumb về Explorer, monogram, name/provider, description, categories và nút “Mở website chính thức”. Link official HTTPS có external icon và thông báo mở tab mới. Lưu query Explorer trong navigation state để quay lại đúng filters; nếu vào direct link thì về Explorer mặc định.

Main column: capabilities → pricing và điều kiện → integrations → technical metadata/models. Summary rail: platforms, API, open-source/license, ngày review record. Mỗi fact có status và evidence link tại chỗ; nguồn có domain + ngày kiểm tra, không chỉ nhãn “Verified” toàn tool.

Pricing có currency, billing basis, usage limits và ngày kiểm tra nếu dữ liệu có; không đổi monthly_min thành tổng ngân sách thực tế. Fact false hiển thị “Không hỗ trợ” khi verified; null “Chưa có dữ liệu”; stale “Cần xác minh lại” với ngày cũ. Ngày review record không đảm bảo mọi giá/capability còn hiệu lực.

Nguồn dài nằm trong disclosure “Xem nguồn” ngay dưới fact, dùng được bằng keyboard; không giấu bằng hover-only tooltip. Integration chưa có evidence không được tạo claim tương thích. Không có facts cho một nhóm thì hiện thông báo ngắn, không để khung trống lớn.

MVP không có nút Save tool. Có link phụ “Quản lý stack của tôi” để user thêm từ editor; không hứa đã chọn sẵn tool khi chưa có UI state đó. Archived/absent trả 404 public: “Không tìm thấy công cụ này” + về Explorer, không expose draft record.

### 6.4. AI Stack Builder — `/builder`

**Bố cục:** H1 “Tạo AI Stack” → mô tả ngắn → objective form → optional constraints → submit → result dưới form. Desktop có rail “Cách dùng” ngắn trước generation; khi có kết quả thay bằng summary constraints. Không dùng chat bubbles, transcript hoặc sidebar lịch sử chưa được API hỗ trợ.

Objective textarea 5–7 dòng, label “Bạn muốn hoàn thành việc gì?”, counter 10–4000 ký tự, ví dụ RAG PDF trên Windows 8GB. Một example button “Dùng ví dụ chatbot PDF” chỉ điền form, không tự gửi; khi form đã có nội dung phải hỏi trước thay thế.

Optional section “Thiết bị và yêu cầu” đóng mặc định; summary cho biết số điều kiện đã nhập. Không tự bật Windows/8GB chỉ vì đó là môi trường developer xây dự án.

| UI control | Request field | Hành vi |
|---|---|---|
| Hệ điều hành/nền tảng, có “Chưa chỉ định” | constraints.platform | Enum theo API; null khi chưa chọn |
| RAM (GB) | constraints.ram_gb | Number >0, ≤1024; bỏ trống là null |
| Cloud được phép / Chỉ local / Chưa chỉ định | constraints.deployment | Không coi web là offline Windows |
| Bắt buộc offline, Bắt buộc có API | offline_required, api_required | Bật gửi true; tắt nghĩa không bắt buộc, không phải yêu cầu false về tool |
| Ngân sách tối đa USD/tháng | budget_usd_month | ≥0; 0 là yêu cầu miễn phí cứng, bỏ trống là chưa đặt giới hạn |
| Mức sử dụng dự kiến | monthly_usage | Text ≤1000 chars, hiện khi có hard budget; thiếu có thể cần clarification |
| Ưu tiên gói miễn phí / Dễ bắt đầu / Open-source / Ít công cụ | preferences | Bốn enum có sẵn, không biến preference thành hard requirement |

Ngân sách tool của user khác cost nội bộ của LLM backend. Không hiển thị `usage.estimated_cost_usd` như giá mua stack, không xây billing UI.

Trước submit chỉ tóm tắt form user đã nhập; sau response mới có “Yêu cầu hệ thống hiểu” từ objective_summary, required_roles, hard_constraints và preferences. Có hai nhóm nhãn “Bắt buộc” và “Ưu tiên”, không dùng màu làm khác biệt duy nhất. Muốn sửa dùng nút “Điều chỉnh yêu cầu” đưa focus về form và gửi request mới; không có extraction endpoint riêng.

**Pending:** disable submit, giữ chiều rộng nút, text “Đang tạo đề xuất…”, `aria-busy` trên vùng kết quả. Có thể hiển thị elapsed time thực nếu cần, nhưng không chia phase giả hoặc phần trăm. Không có cancel job, auto-retry POST hay streaming giả. Rời trang không bảo đảm dừng request/chi phí; không hứa khôi phục result sau reload vì không có GET generation.

**Result order:** status + gaps/questions → requirement summary → role items → workflow → Save / Điều chỉnh yêu cầu. Item dùng role number, tool name từ detail/record, validated rationale, claims/evidence và link tool detail. Resolve tool names theo unique tool IDs có bounded concurrency/cache; khi detail lỗi giữ vai trò + thông báo metadata chưa tải, không bịa tên. Đây chỉ dành result tối đa 20 items, không áp dụng N detail requests cho Explorer grid.

| Result status | Tiêu đề / hành vi | Save |
|---|---|---|
| complete | “Đã tìm được công cụ cho các vai trò”; hiển thị cảnh báo compatibility nếu có | Có, không gọi “tối ưu” hay “đã chạy thành công” |
| partial | “Stack còn thiếu thành phần”; gaps phía trên items, không giấu sau accordion | Có, label “Lưu stack chưa hoàn chỉnh” |
| no_match | “Chưa tìm được công cụ phù hợp”; lý do và link chỉnh constraints | Không |
| needs_clarification | “Cần làm rõ yêu cầu”; 1–3 câu hỏi, đưa user về form để bổ sung | Không |

Workflow hiển thị ordered list theo items, phía dưới mỗi bước liệt kê outgoing edges thật của response. Có thể dùng đường nối CSS đơn giản, nhưng không tự vẽ mũi tên giữa mọi cặp kế tiếp nếu API không có edge. Unverified edge ghi “Cần kiểm thử kết nối”; verified edge mở được evidence. Một item không có edge không cần sơ đồ. Mobile luôn đọc dọc, không graph ngang.

“Lưu stack” mở dialog nhập title 1–120 chars; gửi generation_id và title với Idempotency-Key; thành công điều hướng stack detail. Chưa lưu thì sửa thành phần bằng cách “Lưu rồi chỉnh sửa”; không âm thầm sửa validated result trong browser và gửi như generation gốc. Thiếu nguồn giá hiển thị cảnh báo cụ thể; không tự nới budget.

### 6.5. My Stacks — `/my-stacks`

H1 “Stack của tôi”, mô tả private, CTA “Tạo stack thủ công”, link “Tạo bằng AI”. List theo updated desc từ API. Mỗi row: title, purpose tối đa 2 dòng, item_count, validation_state, updated_at; created_at có thể secondary. Link “Mở stack” rõ, không avatar tools vì list endpoint chưa cung cấp items.

Không thêm search/sort selector/filter theo purpose khi API chưa hỗ trợ; purpose là field mô tả để tổ chức đơn giản, không có folders/projects/tags riêng. Pagination như Explorer. Empty state: “Bạn chưa lưu stack nào” + hai đường tạo; auth gate giữ destination nhưng không lộ stack data.

### 6.6. Saved stack detail và editor

View mode: title/purpose → status và warnings → items/roles → ordered workflow → timestamps. Toolbar “Chỉnh sửa”, secondary “Quay lại”, menu “Xóa stack”. Labels: generated “Tạo từ đề xuất AI”, manual “Tạo thủ công”, modified “Đã chỉnh sửa — cần kiểm chứng lại”. Generated không phải nhãn “verified” vĩnh viễn; snapshot partial/stale warnings vẫn hiển thị.

Edit mode trên cùng route: title/purpose fields, editable item rows, footer “Lưu thay đổi / Hủy”. Tool picker dùng catalog search trong dialog/drawer, mỗi result có nút “Chọn”; tải từ GET tools, chỉ published. Sau chọn nhập role, append position; một tool nhiều roles được phép. Không thêm picker filter theo capability chưa có API param.

Mỗi row có “Thay công cụ”, “Xóa thành phần”, “Lên”, “Xuống” bằng buttons; không cần drag-and-drop. Thay tool giữ item_id, preview warning claims/kết nối sẽ cần kiểm chứng. Xóa item hiện số edges bị ảnh hưởng, bỏ chúng khỏi draft; trước Save vẫn có thể Hủy toàn bộ draft. Reorder phải kiểm tra edges vẫn đi theo position tăng; nếu không, giải thích và yêu cầu sửa/xóa edges liên quan, không tự đảo hướng workflow.

Workflow chỉnh bằng form đơn giản nguồn/đích/mô tả, chỉ cho đích đứng sau nguồn; không canvas. Manual edge luôn chưa kiểm chứng. Client chỉ gửi editable fields theo PUT; không gửi claims/rationale/verified flags. Không gọi lại LLM khi user chỉ đổi tool.

Save dùng expected_version, thay local state bằng server canonical response. 409 version conflict giữ bản nháp; hiển thị bản server và draft để user áp dụng lại, không tự overwrite. 409 tool unavailable yêu cầu thay tool mới; item archived đã có giữ snapshot với warning. Nếu rời edit với dirty state, confirm bỏ thay đổi; không auto-save ngầm hoặc lưu lâu dài raw draft trong localStorage.

Xóa stack cần dialog có title cụ thể, text “Stack sẽ bị xóa khỏi tài khoản của bạn”, nút “Giữ lại” focus mặc định và nút destructive “Xóa stack”. Chỉ remove khỏi list sau server 204; không có Undo giả vì API chưa hỗ trợ restore.

## 7. Component inventory và behavior contracts

Radix Dialog `1.1.23` và Lucide React `1.49.0` đã được pin ở TASK-006.2: Radix sở hữu focus trap/Escape/focus return của drawer; Lucide là icon family duy nhất, stroke 1.75 và icons phụ decorative dùng `aria-hidden`. Chỉ thêm primitive mới khi feature screen thật cần; không thêm component library thứ hai để làm màn hình khác phong cách.

| Component dự kiến | Dùng ở đâu | States/contract |
|---|---|---|
| AppShell / Navigation | Mọi route | active route, drawer open, anonymous/authenticated |
| ThemeControl | Shell | dark/light/system, keyboard selection |
| SearchField | Home/Explorer/tool picker | value, pending, clear, submit; visible label |
| FilterPanel / FilterDrawer / FilterChip | Explorer | draft/applied, selected, reset; không dùng chung state mơ hồ |
| ToolCard | Home/Explorer | ToolSummary only; monogram fallback; detail link |
| FactRow / EvidenceDisclosure | Tool detail/result | verified/unverified/unknown/stale; text + source/date |
| StatusBadge / InlineNotice | Cross-page | semantic label + icon; no color-only status |
| ObjectiveForm / ConstraintFields | Builder | pristine/dirty/invalid/submitting; typed fields |
| RequirementSummary | Builder/result | hard/soft/missing từ dữ liệu thật |
| RecommendationItem / WorkflowList | Builder/stack | role/claims/evidence, edges verified/unverified |
| StackListRow / StackEditor / ToolPicker | My Stacks | loading/empty/dirty/conflict; owner scope từ API |
| Dialog / Drawer / ConfirmationDialog | Cross-page | focus trap/restore, Escape, pending mutation |
| Skeleton / EmptyState / ErrorState | Cross-page | size phù hợp, retry/contextual action |
| Pagination / Toast | Cross-page | first/last/loading; announcement không lấy focus |

Button variants: primary, secondary (surface + control border), ghost (text), destructive. Dùng anchor cho navigation và button cho action. Link hover có underline; selected navigation có marker/label ngoài màu. Không làm whole row click khi bên trong có menu/button nested.

Form validation chạy khi blur hoặc submit; không báo đỏ ngay khi user gõ ký tự đầu. Submit lỗi focus error summary, summary link tới field. Inline error nối bằng aria-describedby; server 422 map field path về form, lỗi không map được hiện banner. Enter trong textarea tạo dòng mới; không vô tình submit generation.

Toast chỉ cho feedback phụ “Đã lưu stack”; lỗi cần xử lý ở inline/banner và tồn tại đến khi giải quyết. Buttons đang gửi giữ label cụ thể, không nhảy layout; không thông báo thành công trước response. Không disabled action không giải thích: nếu quota/stale chặn, hiển thị lý do và đường tiếp theo ngay gần action.

## 8. Loading, empty, error và recovery

| Sự kiện | UI copy gợi ý | Recovery |
|---|---|---|
| Catalog lần đầu đang tải | Skeleton cards, nhãn “Đang tải công cụ…” | Chưa hiển thị count giả |
| Đổi filters đang tải | Giữ grid cũ có aria-busy, nhãn “Đang cập nhật…” | Không lẫn count cũ thành kết quả mới |
| Không có tool match | “Chưa có công cụ khớp với lựa chọn này.” | Xóa filters hoặc sửa q |
| API 401 | “Phiên đăng nhập đã hết hạn.” | Login-return; giữ draft trong session UI theo auth adapter |
| API 403 | “Tài khoản hiện không thể thực hiện thao tác này.” | Về discovery; không retry vô hạn |
| API 404 stack | “Không tìm thấy stack này.” | Về My Stacks; không tiết lộ owner khác |
| API 409 catalog/generation stale | “Dữ liệu đã thay đổi kể từ lần đề xuất.” | Generate lại hoặc tạo manual, không giữ nhãn kiểm chứng |
| API 409 edit conflict | “Stack đã được cập nhật ở nơi khác.” | Giữ draft, tải phiên bản mới, áp dụng lại có chủ đích |
| API 410 generation expired | “Kết quả này đã hết thời gian lưu.” | Generate lại hoặc manual; không hứa gọi GET để phục hồi |
| API 422 | “Kiểm tra lại thông tin đã nhập.” | Lỗi tại field + summary; giữ input |
| API 429 | “Bạn đã đạt giới hạn tạo stack.” | Dùng Retry-After thật khi có; không bịa giờ reset |
| API 502/503 | “Chưa thể tạo đề xuất lúc này.” | Retry thủ công; không thay bằng stack demo |
| API 504/network outcome không rõ | “Chưa nhận được kết quả.” | Giữ input, thông báo gửi lại có thể tính một lượt mới |
| Tool archived trong saved stack | “Công cụ này không còn trong thư viện công khai.” | Đọc snapshot, chọn thay thế; detail link public có thể unavailable |

Error details có disclosure “Mã yêu cầu” để copy request_id; không phô HTTP code, raw provider error hoặc tokens trong primary copy. Nếu clipboard bị từ chối vẫn hiển thị text có thể chọn. Network reconnect không tự submit mutation. Screen reader chỉ announce khi trạng thái thực thay đổi, không đọc spinner mỗi giây.

## 9. Accessibility và khả năng đọc

Mục tiêu áp dụng [WCAG 2.2](https://www.w3.org/TR/WCAG22/), không phải tuyên bố đã đạt chứng nhận. Baseline AA: text thường contrast ≥4,5:1, chữ lớn ≥3:1; thành phần UI thiết yếu ≥3:1; hỗ trợ keyboard, focus nhìn thấy và không bị che hoàn toàn. Reflow kiểm tra ở 320 CSS px. Target size AA có ngưỡng 24 CSS px kèm ngoại lệ; dự án chọn 44×44px cho controls để dễ chạm hơn. Nguồn: [contrast](https://www.w3.org/TR/WCAG22/#contrast-minimum), [non-text contrast](https://www.w3.org/TR/WCAG22/#non-text-contrast), [reflow](https://www.w3.org/TR/WCAG22/#reflow), [target size](https://www.w3.org/TR/WCAG22/#target-size-minimum).

Checklist triển khai riêng của AI Atlas:

- Có skip link, landmarks header/nav/main; H1 mỗi page, heading order hợp lý; `lang=vi`, không render metadata thành ảnh.
- Tab order theo DOM; không positive tabindex; route change chuyển focus tới H1 hợp lý. Back navigation không tự cuộn mất vị trí người dùng khi có thể phục hồi.
- Dialog/drawer có tên, focus trap và focus return; Escape đóng khi an toàn. Nếu mutation vẫn pending, dialog đóng không được diễn giải là server đã hủy.
- Input có label bền vững; placeholder chỉ ví dụ. Numeric fields có unit và lỗi cụ thể; required/optional ghi bằng text.
- Status/error không chỉ có icon/màu; loading/result count dùng live region phù hợp, không chuyển focus mỗi lần debounce.
- Zoom/text spacing không cắt labels, errors hoặc buttons; tool name/URL dài wrap. Không bắt horizontal scroll để đọc Builder.
- Tool logo cạnh name dùng alt rỗng nếu chỉ trang trí; icon-only action có accessible name. Evidence link nói rõ nguồn cho fact nào.
- Keyboard chọn tool, reorder items và sửa edges được; không cần drag, hover hoặc gesture nhiều ngón.
- Auth không chặn paste/password manager trong provider flow; kiểm tra experience của adapter thực tế khi triển khai.
- Kiểm tra Windows High Contrast/forced-colors để focus và selected state còn nhìn được; reduced motion giữ thông báo đầy đủ.

## 10. Data binding, mock và frontend boundaries

| UI | Data/API source | Điều không được giả định |
|---|---|---|
| Home/categories/cards | GET categories + GET tools | popularity, logos, ratings |
| Explorer | GET tools + documented filters | server autocomplete, sort theo lượt dùng |
| Tool detail | GET tools/{tool_id} | every fact verified hoặc complete pricing |
| Builder | POST stack-generations, result schema | intermediate phases, cancel/resume, GET result |
| Generated Save | POST stacks với generation_id/title | client-provided claims được server tin |
| Stack list | GET stacks | items/logos có sẵn trong summary |
| Stack editor | GET stack, GET tools, PUT stack | last-write-wins hoặc tự giữ verified status |
| Delete | DELETE stack + expected_version | restore/Undo endpoint |

UI state gồm draft, loading, selected filters, dialog, validation errors; business truth gồm hard constraints, evidence validity, ownership và result validation do backend quyết định. Không dùng client-only checks thay server checks. Nếu field không có trong response, omit hoặc ghi unknown đúng ngữ cảnh, không nội suy facts.

Mock chỉ dùng development/test adapters, typed theo API và gắn banner “Dữ liệu minh họa — chưa kết nối API” trong preview. Có fixtures cho đủ statuses, long Vietnamese names, stale evidence, archived tool và 2 users. Production không fallback sang mock khi backend lỗi. Không gọi LLM có phí trong visual/CI tests. Raw objective không vào URL, analytics, exception reports hoặc localStorage; draft giữ trong bộ nhớ/session UI giới hạn theo auth design, xóa khi logout và theo policy đã chốt.

## 11. Trình tự triển khai và kiểm chứng

Không thay thứ tự phụ thuộc trong [Tasks](../planning/TASKS.md) hoặc [Roadmap](../planning/ROADMAP.md). Các phase dưới đây là phần UI của những task đó, không phải backlog mới tự động được đánh dấu Done.

| Phase | Task hiện có | Deliverable UI | Acceptance |
|---|---|---|---|
| 1. Foundation | TASK-001/002 | Tokens hai themes, type scale, primitives, shell | Decisions rõ; theme/control states thống nhất, không flash sai theme |
| 2. Discover slice | TASK-006/007 | Home, Explorer, tool detail | API thật; URL filters, empty/error, evidence và mobile drawer pass |
| 3. Build slice | TASK-013/014, phụ thuộc TASK-010/011 | Form, requirement summary, result/workflow states | Không fake progress, đủ 4 statuses và lỗi kỹ thuật; schema fixtures rõ |
| 4. Auth + Save | TASK-016/019/020 | Login-return, list/editor, dialogs | Save/reload, ownership, stale/expired/conflict UX pass |
| 5. Refinement | TASK-024/026 | Responsive, accessibility, rendered visual review | Ba journeys trên final dataset; không còn lỗi UI chặn thao tác |

### 11.1. UI acceptance matrix

| ID | Liên kết PRD | Kiểm tra cần chạy khi có ứng dụng |
|---|---|---|
| UX-AC-01 | FR-013, NFR-009 | Cả themes có đủ default/hover/focus/error/disabled/selected states; text không mất contrast |
| UX-AC-02 | FR-002 | Search có dấu tiếng Việt, multi-category, back/forward, remove chip, clear/reset và sort hợp lệ |
| UX-AC-03 | FR-003 | Unknown/false/stale phân biệt; facts có nguồn/date; không fabricated prices/logos/ratings |
| UX-AC-04 | FR-004/007 | Budget 0 khác null; conflict trả clarification; sửa form không tự nới constraints |
| UX-AC-05 | FR-006/007 | Complete/partial/no_match/clarification render đúng; unverified edges luôn có nhãn; loading không progress giả |
| UX-AC-06 | FR-008/009 | Login-return giữ draft đúng session; save pending/success/error, idempotency; không lộ stack user khác |
| UX-AC-07 | FR-010 | Edit/reorder/delete, edge impact, modified label, expected_version conflict và cancel dirty draft |
| UX-AC-08 | FR-013, NFR-009 | Navigation/forms/dialogs hoàn thành bằng keyboard; screen reader hiểu labels/status/error; focus không bị sticky che |
| UX-AC-09 | FR-013 | Viewports 360×800, 768×1024, 1024×768, 1366×768, 1920×1080; thêm reflow 320px và zoom 200%/400% |
| UX-AC-10 | FR-007, NFR-004 | 401/403/404/409/410/422/429/502/503/504, slow network, empty data; không raw errors/secrets |

Component tests cho states và keyboard; integration cho URL/form binding; E2E ba journeys; accessibility automated checks kết hợp keyboard/screen reader review; screenshots desktop/mobile ở hai themes với fixtures cố định. Chỉ chạy lệnh lint/type/test thật có trong repo sau scaffold; không ghi lệnh hoặc kết quả giả. Screenshot baseline chỉ duyệt sau khi xem rendered pages, không tự chấp nhận toàn bộ diff.

### 11.2. Tình trạng và điểm còn mở

Hiện hoàn thành **spec thiết kế**, Catalog BFF boundary và foundation shell: responsive sidebar/header/drawer, active route, locale `vi/en`, dark/light/system không flash sai theme, keyboard/focus contract và semantic tokens. Component tests cùng browser smoke đã kiểm tra 320px reflow, breakpoint 1279/1280, controls 44px, first-frame theme và axe desktop/mobile không có violation. Chưa có Explorer/tool detail/Builder/My Stacks, mock assets hoặc visual regression baseline.

Cần chốt ở implementation: Auth0 Google Login UI theo ADR-007 và font assets khi feature screens cần. TASK-006.3–006.7, TASK-013 và TASK-019 vẫn phải kiểm tra copy/state en/vi trong từng journey; audit shell không thay chứng nhận accessibility cho các screens tương lai. Logo assets, featured/related sections và compact Explorer view chỉ bổ sung khi có dữ liệu hoặc yêu cầu rõ; không là blocker của MVP hiện tại. Mọi thay đổi fields/API phải cập nhật contract trước, không lách bằng hardcoded UI data.
