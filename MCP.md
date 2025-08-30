# Model Context Protocol (MCP) Servers

## Tổng quan
MCP servers cung cấp khả năng mở rộng cho Claude Code, cho phép tích hợp với các công cụ và dịch vụ bên ngoài.

## Cấu hình

### File cấu hình
- **Global**: `C:\Users\quocn\.claude.json`
- **Local**: `D:\pcloud\code\ai\experts\.claude\settings.local.json`

### Cú pháp cấu hình cơ bản
```json
{
  "mcpServers": {
    "server-name": {
      "type": "stdio",
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {}
    }
  }
}
```

## MCP Servers đã cài đặt

### 1. Playwright MCP
**Mục đích**: Tự động hóa trình duyệt web

**Cài đặt**:
```bash
npm install -g @playwright/mcp@latest
```

**Cấu hình**:
```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "env": {}
    }
  }
}
```

**Các lệnh và cách sử dụng**:

#### Navigation & Basic Actions
```bash
# Mở trang web (localhost hoặc production)
mcp__playwright__browser_navigate --url "http://localhost:3000/login"
mcp__playwright__browser_navigate --url "https://example.com"

# Quay lại/tiến trang
mcp__playwright__browser_navigate_back
mcp__playwright__browser_navigate_forward

# Đóng browser
mcp__playwright__browser_close
```

#### Screenshots & Analysis
```bash
# Chụp màn hình để phân tích (lưu thành file PNG/JPEG)
mcp__playwright__browser_take_screenshot --filename "error-page.png"
mcp__playwright__browser_take_screenshot --fullPage true --filename "full-page.png"

# Accessibility snapshot để hiểu cấu trúc trang (text format)
mcp__playwright__browser_snapshot
# → Trả về cấu trúc YAML với các element references để tương tác
```

#### User Interactions
```bash
# Click elements (cần ref từ snapshot)
mcp__playwright__browser_click --element "Login button" --ref "e57"

# Nhập text
mcp__playwright__browser_type --element "Username field" --ref "e41" --text "admin"
mcp__playwright__browser_type --element "Password field" --ref "e42" --text "password123" --submit true

# Nhấn phím
mcp__playwright__browser_press_key --key "Enter"
mcp__playwright__browser_press_key --key "Escape"

# Hover
mcp__playwright__browser_hover --element "Menu item" --ref "e33"

# Dropdown selection
mcp__playwright__browser_select_option --element "Country dropdown" --ref "e44" --values ["Vietnam"]

# Upload file
mcp__playwright__browser_file_upload --paths ["/path/to/file.pdf"]

# Drag & drop
mcp__playwright__browser_drag --startElement "Item" --startRef "e10" --endElement "Target" --endRef "e20"
```

#### Advanced Features
```bash
# Chạy JavaScript trong browser
mcp__playwright__browser_evaluate --function "() => document.title"
mcp__playwright__browser_evaluate --function "(element) => element.click()" --ref "e33"

# Xem console logs (debugging)
mcp__playwright__browser_console_messages

# Xem network requests (API calls, resources)
mcp__playwright__browser_network_requests

# Xử lý popup/alert
mcp__playwright__browser_handle_dialog --accept true
mcp__playwright__browser_handle_dialog --accept false --promptText "cancel"

# Resize browser window
mcp__playwright__browser_resize --width 1920 --height 1080

# Đợi elements xuất hiện
mcp__playwright__browser_wait_for --text "Loading complete"
mcp__playwright__browser_wait_for --time 3
```

## MCP Servers khác có thể thêm

### Context7 (Upstash)
**Mục đích**: Cung cấp documentation cập nhật cho libraries

**Cài đặt**:
```bash
npm install -g @upstash/context7
```

**Cấu hình**:
```json
{
  "mcpServers": {
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": ["@upstash/context7"],
      "env": {}
    }
  }
}
```

### Filesystem MCP
**Mục đích**: Truy cập hệ thống file

**Cài đặt**:
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**Cấu hình**:
```json
{
  "mcpServers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"],
      "env": {}
    }
  }
}
```

### Git MCP
**Mục đích**: Tương tác với Git repositories

**Cài đặt**:
```bash
npm install -g @modelcontextprotocol/server-git
```

**Cấu hình**:
```json
{
  "mcpServers": {
    "git": {
      "type": "stdio",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-git", "--repository", "."],
      "env": {}
    }
  }
}
```

### Database MCP (SQLite)
**Mục đích**: Truy vấn database SQLite

**Cài đặt**:
```bash
npm install -g @modelcontextprotocol/server-sqlite
```

**Cấu hình**:
```json
{
  "mcpServers": {
    "sqlite": {
      "type": "stdio",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-sqlite", "--db-path", "/path/to/database.db"],
      "env": {}
    }
  }
}
```

### Web Search MCP
**Mục đích**: Tìm kiếm web

**Cài đặt**:
```bash
npm install -g @modelcontextprotocol/server-brave-search
```

**Cấu hình**:
```json
{
  "mcpServers": {
    "brave-search": {
      "type": "stdio",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-brave-search"],
      "env": {
        "BRAVE_API_KEY": "your-api-key"
      }
    }
  }
}
```

## Lệnh quản lý MCP

### Kiểm tra cấu hình
```bash
claude mcp list          # Liệt kê tất cả servers
claude mcp get <name>    # Xem cấu hình server cụ thể
claude mcp inspect       # Kiểm tra chi tiết
```

### Debug
```bash
claude doctor            # Kiểm tra tình trạng tổng thể
```

### Khởi động lại
```bash
# Khởi động lại Claude Code để áp dụng cấu hình mới
```

## Cấu hình mẫu hoàn chỉnh

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "env": {}
    },
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": ["@upstash/context7"],
      "env": {}
    },
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-filesystem", "D:\\pcloud\\code"],
      "env": {}
    },
    "git": {
      "type": "stdio",
      "command": "npx",
      "args": ["@modelcontextprotocol/server-git", "--repository", "."],
      "env": {}
    }
  }
}
```

## Workflow Development với Playwright MCP

### 1. Testing ứng dụng đang phát triển
```bash
# Bước 1: Navigate đến app local
mcp__playwright__browser_navigate --url "http://localhost:3000"

# Bước 2: Chụp màn hình để xem giao diện
mcp__playwright__browser_take_screenshot --filename "home-page.png"

# Bước 3: Lấy cấu trúc trang để tương tác
mcp__playwright__browser_snapshot

# Bước 4: Test login flow
mcp__playwright__browser_navigate --url "http://localhost:3000/login"
mcp__playwright__browser_type --element "Email input" --ref "e12" --text "test@example.com"
mcp__playwright__browser_type --element "Password input" --ref "e15" --text "testpass"
mcp__playwright__browser_click --element "Login button" --ref "e18"

# Bước 5: Verify kết quả
mcp__playwright__browser_snapshot
mcp__playwright__browser_take_screenshot --filename "after-login.png"
```

### 2. Debug lỗi UI
```bash
# Khi gặp lỗi, chụp màn hình ngay lập tức
mcp__playwright__browser_take_screenshot --filename "error-state.png"

# Xem console errors
mcp__playwright__browser_console_messages

# Xem network requests để check API failures
mcp__playwright__browser_network_requests

# Chạy JavaScript để inspect elements
mcp__playwright__browser_evaluate --function "() => document.querySelector('.error').textContent"
```

### 3. Test responsive design
```bash
# Mobile view
mcp__playwright__browser_resize --width 375 --height 667
mcp__playwright__browser_take_screenshot --filename "mobile-view.png"

# Tablet view
mcp__playwright__browser_resize --width 768 --height 1024
mcp__playwright__browser_take_screenshot --filename "tablet-view.png"

# Desktop view
mcp__playwright__browser_resize --width 1920 --height 1080
mcp__playwright__browser_take_screenshot --filename "desktop-view.png"
```

### 4. Form testing automation
```bash
# Test form validation
mcp__playwright__browser_navigate --url "http://localhost:3000/register"

# Submit empty form để test validation
mcp__playwright__browser_click --element "Submit button" --ref "e20"
mcp__playwright__browser_take_screenshot --filename "validation-errors.png"

# Fill form với invalid data
mcp__playwright__browser_type --element "Email field" --ref "e10" --text "invalid-email"
mcp__playwright__browser_click --element "Submit button" --ref "e20"
mcp__playwright__browser_take_screenshot --filename "invalid-email-error.png"

# Fill form với valid data
mcp__playwright__browser_type --element "Email field" --ref "e10" --text "valid@email.com"
mcp__playwright__browser_type --element "Name field" --ref "e12" --text "Test User"
mcp__playwright__browser_click --element "Submit button" --ref "e20"
mcp__playwright__browser_take_screenshot --filename "successful-submit.png"
```

## Phân tích Screenshot vs Snapshot

### Khi nào dùng `browser_take_screenshot`:
- **Phân tích giao diện**: Xem layout, colors, styling
- **Báo cáo bug**: Capture lỗi UI để gửi team
- **Document features**: Tạo screenshots cho documentation
- **Compare versions**: So sánh before/after changes
- **Responsive testing**: Kiểm tra trên different screen sizes

**Ví dụ sử dụng**:
```bash
# Capture error state để báo bug
"Tôi thấy button bị lỗi, hãy chụp màn hình current state"
→ mcp__playwright__browser_take_screenshot --filename "button-bug.png"

# So sánh responsive
"Chụp màn hình ở mobile và desktop để so sánh"
→ mcp__playwright__browser_resize --width 375 --height 667
→ mcp__playwright__browser_take_screenshot --filename "mobile.png"
→ mcp__playwright__browser_resize --width 1920 --height 1080  
→ mcp__playwright__browser_take_screenshot --filename "desktop.png"
```

### Khi nào dùng `browser_snapshot`:
- **Automation**: Cần element references để click, type, interact
- **Structure analysis**: Hiểu DOM structure và accessibility tree
- **Find elements**: Locate buttons, inputs, links để tương tác
- **Verify content**: Check text content, form states

**Ví dụ sử dụng**:
```bash
# Cần tương tác với form
"Tôi muốn fill form login"
→ mcp__playwright__browser_snapshot  # Lấy element refs
→ mcp__playwright__browser_type --element "Username" --ref "e41" --text "admin"
→ mcp__playwright__browser_type --element "Password" --ref "e43" --text "pass"
→ mcp__playwright__browser_click --element "Login btn" --ref "e45"

# Kiểm tra page content
"Check xem login có thành công không"
→ mcp__playwright__browser_snapshot  # Xem text content và elements hiện có
```

## Use Cases trong Development

### 1. **Automated Testing**
```bash
# Test complete user journey
mcp__playwright__browser_navigate --url "http://localhost:3000"
→ mcp__playwright__browser_snapshot
→ mcp__playwright__browser_click --element "Get Started" --ref "e10"
→ mcp__playwright__browser_type --element "Email" --ref "e15" --text "test@example.com"
→ mcp__playwright__browser_click --element "Subscribe" --ref "e18"
→ mcp__playwright__browser_wait_for --text "Thank you"
→ mcp__playwright__browser_take_screenshot --filename "success.png"
```

### 2. **Bug Reproduction**
```bash
# Reproduce reported bug
mcp__playwright__browser_navigate --url "http://localhost:3000/checkout"
→ mcp__playwright__browser_type --element "Card number" --ref "e20" --text "4111111111111111"
→ mcp__playwright__browser_click --element "Pay now" --ref "e25"
→ mcp__playwright__browser_take_screenshot --filename "payment-error.png"
→ mcp__playwright__browser_console_messages  # Check for JS errors
```

### 3. **Performance Testing**
```bash
# Check page load performance
mcp__playwright__browser_navigate --url "http://localhost:3000/heavy-page"
→ mcp__playwright__browser_network_requests  # Analyze network calls
→ mcp__playwright__browser_console_messages  # Check for performance warnings
→ mcp__playwright__browser_take_screenshot --filename "loaded-page.png"
```

## Troubleshooting

### Lỗi thường gặp:
1. **`net::ERR_CONNECTION_REFUSED`**: Dev server chưa chạy
2. **Element not found**: Cần chạy `browser_snapshot` trước để lấy refs
3. **Screenshot trống**: Page chưa load xong, dùng `browser_wait_for`
4. **Browser không mở**: Cần install browser với `npx playwright install`

### Debug tips:
```bash
# Always snapshot first để hiểu page structure
mcp__playwright__browser_snapshot

# Check console for errors
mcp__playwright__browser_console_messages

# Wait for dynamic content
mcp__playwright__browser_wait_for --text "Content loaded"

# Take screenshot để visual debug
mcp__playwright__browser_take_screenshot --filename "debug-state.png"
```

## Lưu ý
- Khởi động lại Claude Code sau khi thay đổi cấu hình
- Một số MCP servers cần API keys
- Kiểm tra logs nếu server không hoạt động
- Sử dụng `claude doctor` để debug
- **Screenshot**: Để phân tích visual, báo bugs, documentation
- **Snapshot**: Để automation, tương tác với elements
- Luôn chạy `browser_snapshot` trước khi tương tác với elements