# MCP 探针注册权威配置指引

> [!IMPORTANT]
> **请勿在此手动复制并填写绝对路径占位符！**
> 为了防止由于手动拼写或不同操作系统（Windows/Mac/Linux）下的 Python 环境变量冲突导致 MCP 探针拉起失败，请**一律通过运行本地自省脚本获取当前环境的专属注册配置。**

---

## 🚀 自动生成你的多端配置 (0 门槛复制)

请在您的项目根目录下，直接打开终端运行以下指令：

```bash
python .agents/mcp/minecraft_mcp.py --help
```

### 🎁 运行后你将获得：
1. **自动定位并解析的物理绝对路径**
2. **当前 Python 环境的绝对执行文件路径**（自动替换为 `sys.executable`，彻底防范 Windows 商店广告或 python/python3 找不到的问题）
3. **Cursor、Cline (Roo Code)、Claude Code、Grok 专用的完美 JSON 配置块**

您可以直接在终端输出的高亮框线中复制配置进行一键贴入！

---

## ⚠️ 通用协议规范
*   **通信协议**：JSON-RPC 2.0 over Stdio
*   **分帧格式**：Newline-delimited JSON (每一行是一个独立的完整 JSON)。本探针目前暂不支持 LSP 规范下的 Content-Length 强制报头分帧。
*   **适用客户端**：Cursor, Cline, Roo Code, Claude Code, Grok Build 等 stdio MCP 宿主环境。
