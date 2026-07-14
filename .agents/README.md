# .agents AI 辅助开发增强包 (Developer Guide)

这是一个专门为 Minecraft 1.21.1 + NeoForge 模组开发定制的通用 AI 辅助套件。

---

## 🚀 ⏱️ 5 分钟 Onboarding Checklist (核心接入)

1. **步骤一：挂载项目规则**
   将 [`.agents/AGENTS.md`](./AGENTS.md) 的内容注册为您当前使用的 AI 客户端的常驻项目规则 / 系统提示词（System Prompt）。

2. **步骤二：激活 MCP 源码探针**
   在 AI 客户端的 MCP 配置中注册探针（以提供游戏及依赖的源码检索能力）：
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
   *(请将 `args` 改为本机项目 `minecraft_mcp.py` 的绝对路径。)*

3. **步骤三：一键工作区初始化**
   向 AI 助手发送：`“帮我初始化一下这个工作区”`，AI 将自动调用 `init_workspace.py` 重构物理包命名空间。

4. **步骤四：跑通一次本地编译**
   在终端中运行 `python .agents/skills/workspace_setup/scripts/compile_and_repair.py`，验证本地编译通过。

---

## 📂 目录结构说明

*   [`AGENTS.md`](./AGENTS.md)：**面向 AI 的唯一硬红线规约**。
*   [`mcp/`](./mcp/)：包含 MCP 探针代码 `minecraft_mcp.py` 以及快速缓存。
*   [`skills/`](./skills/)：
    *   `neoforge/`：**一等领域知识库**。包含 NeoForge API 示例、高维架构设计（SOLID）以及配置/网络 Payload 模板。
    *   `workspace_setup/`：一键重构引擎 `init_workspace.py` 和 `compile_and_repair.py` 自测试。
    *   `systematic-debugging/`：错误排障与防御设计指引。
    *   `task_monitor/`：可选后台编译防超时监控。
*   [`_archive/`](./_archive/)：不用的过程型辅助技能（superpowers-optional）与 HTML 噪音（superpowers-noise）的归档备份目录。
