# MCP 探针配置示例模板

这个文件提供在各大 AI 客户端中手动注册本地 MCP 探针服务（`minecraft_mcp.py`）的静态 JSON 配置模板。

---

## 1. Cline / Roo Code / Roo Cline
在您项目根目录的 `.vscode/cline_mcp_settings.json`（如果没有则新建）中填入：

```json
{
  "mcpServers": {
    "minecraft-mcp": {
      "command": "python",
      "args": [
        "/ABS/PATH/TO/PROJECT/.agents/mcp/minecraft_mcp.py"
      ]
    }
  }
}
```
*(注意：请将 `/ABS/PATH/TO/PROJECT/` 替换为项目实际所在的绝对路径)*

---

## 2. Cursor (Settings -> Features -> MCP)
1. 点击 `+ Add New MCP Server`
2. 填写参数：
   - **Name**: `minecraft-mcp`
   - **Type**: `command`
   - **Command**: `python "/ABS/PATH/TO/PROJECT/.agents/mcp/minecraft_mcp.py"`

---

## 3. Claude Code (命令行全局注册)
在命令行中运行：
```bash
claude mcp add minecraft-mcp python "/ABS/PATH/TO/PROJECT/.agents/mcp/minecraft_mcp.py"
```

---

## 4. Grok Build / 其他兼容客户端
- **协议**: stdio JSON-RPC
- **启动指令**: `python "/ABS/PATH/TO/PROJECT/.agents/mcp/minecraft_mcp.py"`
