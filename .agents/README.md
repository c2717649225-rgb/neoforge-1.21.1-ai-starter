# .agents AI 辅助开发增强包 (Developer Guide)

这是一个专门为 Minecraft 1.21.1 + NeoForge 21.1.x 模组开发定制的通用 AI 辅助套件（AI SDK）。它包含跨客户端心智红线规约、领域技能参考库以及基于 Model Context Protocol (MCP) 的原版/依赖源码高速探针工具。

---

## 🚀 1. ⏱️ 5 分钟 Onboarding Checklist (核心接入契约)

拷贝本包到模组工程根目录（与 `build.gradle` / `gradle.properties` 同级）后，请**必须**依次执行以下步骤：

- [ ] **步骤一：确认 AI 客户端已加载全局红线**
  - **如何加载**：确保当前 AI 客户端已读取到并遵循了 [`.agents/AGENTS.md`](./AGENTS.md)。以当前客户端官方文档为准，目标是成功加载该规则。常见客户端配置如下：
    - **Cursor**：将 `.agents/AGENTS.md` 的内容拷贝至根目录的 `.cursorrules` 文件中，或在新版客户端 `.cursor/rules/` 目录下添加配置以常驻读取。
    - **Claude Code**：在启动时使用规则加载配置（或将其内容添加为常驻提示词）。
    - **Cline / Roo Code**：在项目根目录创建 `.clinerules` 并以链接或直接复制形式加载。
    - **Aider**：在项目根目录创建 `.aider.conf.yml` 或规则参数并映射加载本红线。
    - **其他客户端（包括 Grok）**：在配置中将 `.agents/AGENTS.md` 注册为该项目的常驻系统提示词（Project Rules）。

- [ ] **步骤二：注册并激活 MCP 源码探针 (MANDATORY / REQUIRED)**
  - 本探针直接为 AI 提供了检索 Minecraft 原版与 NeoForge 源码的接口。**如果不注册 MCP 探针，AI 将由于无法检索真源码而自动停工。**
  - **注册路径**：`/ABS/PATH/TO/PROJECT/.agents/mcp/minecraft_mcp.py`
  - **客户端配置表**：
    - **OpenCode**：项目已置有 `opencode.json`，在 OpenCode 内确认 `minecraft-mcp` 插件已启用。
    - **Cursor / Claude Code / Cline / Aider**：在您对应客户端的全局或项目 MCP 配置文件（如 `mcpServers.json` / `cline_mcp_settings.json`）中添加以下服务器定义：
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
      *(注意：请将 `args` 中的路径修改为您本地当前项目 `minecraft_mcp.py` 的真实绝对物理路径)*。
    - **其他支持 MCP 的客户端（包括 Grok）**：按客户端 MCP 配置面板，注册指向本地 `/ABS/PATH/TO/PROJECT/.agents/mcp/minecraft_mcp.py` 的探针命令。

- [ ] **步骤三：执行一键工作区初始化**
  - 在聊天框中向 AI 助手下达指令：`“帮我初始化一下这个工作区”`，AI 会自动跑脚本重构包结构和 Mod ID（见下文第 3 节说明）。

- [ ] **步骤四：跑通一次本地编译自检**
  - 在终端中运行一次 `python .agents/skills/workspace_setup/scripts/compile_and_repair.py`，验证本地编译环境完全通过。

---

## 2. 🔌 探针注册验证

配置好 MCP 后，可让 AI 在聊天框中运行：
> `search_class Block` 或 `read_class net.minecraft.world.level.block.Block`
如果能成功搜索并读取到原版 `Block` 类源码，说明探针已 100% 接入成功。

---

## 3. 🚀 一键初始化新项目说明 (由 AI 执行)

当您将 `.agents` 文件夹拷贝进一个新的 NeoForge 模组项目时，您**不需要手动执行复杂的改名或重构操作**。

只需在聊天框中直接向 AI 助手下达指令：

> **“帮我初始化一下这个工作区”**

AI 会自动通过终端调用 [`.agents/skills/workspace_setup/scripts/init_workspace.py`](./skills/workspace_setup/scripts/init_workspace.py) 脚本。该脚本会在 10 毫秒内**以 100% 确定性**为您自动执行以下任务：
1. 从新项目的 `gradle.properties` 中自动读取真实的 `mod_id` 和主包名。
2. 将 `src/main/resources/assets/examplemod` 等物理文件夹自动重命名为您的真实 `mod_id` 命名空间。
3. 自动生成对应的 `yourmod.mixins.json` 并解禁 `neoforge.mods.toml` 里的 mixins 模板占位符。
4. 自动修改主类（Main Class）中的 `MODID` 字符串常量及相关注释。
5. 自动同步更新 `.agents/AGENTS.md` 顶部的参考元数据。

---

## 📂 目录结构说明

*   [`AGENTS.md`](./AGENTS.md)：**面向 AI 的常驻红线规约**。
*   [`agent_workflow.md`](./agent_workflow.md)：双 Agent 协同与自检时序工作流说明。
*   [`mcp/`](./mcp/)：包含 MCP 探针代码 `minecraft_mcp.py` 以及快速缓存。
*   [`skills/`](./skills/)：包含 NeoForge API 示例、高维架构设计（SOLID）、项目一键重构引擎 `init_workspace.py` 以及配置/网络 Payload 的官方推荐模板。
