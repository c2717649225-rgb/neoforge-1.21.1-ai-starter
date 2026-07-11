# TutorialMod 1.21.1 NeoForge Starter Template

开箱即用的 Minecraft **1.21.1 + NeoForge 21.1.x** 模组脚手架。
内置 `.agents` AI 运行时（红线、源码 MCP 探针、编译自检等）。

**环境要求：** JDK 21（`JAVA_HOME` 或 PATH 可用）。

---

## 模组开发起手四步

### 第一步：配置元数据

编辑 `gradle.properties`：
- `mod_id=yourmod`
- `mod_name=Your Mod Name`
- `mod_group_id=com.yourpackage.yourmod`

### 第二步：一键初始化

AI 发送：`帮我初始化一下这个工作区`

或终端：
```bash
python .agents/init_workspace.py
```

### 第三步：注册源码 MCP（Required）

脚本：`.agents/mcp/minecraft_mcp.py`

具体配置方式与多端接入配置表见 [**.agents/README.md 指南**](.agents/README.md)。

### 第四步：编译自检

首次验证，以及之后每次修改 Java：
```bash
python .agents/skills/workspace_setup/scripts/compile_and_repair.py
```

注册项 / DataGen Provider 变更时：
```bash
python .agents/skills/workspace_setup/scripts/compile_and_repair.py --with-data
```

*(可选启动测试：`./gradlew runClient`)*

---

## 📂 核心文档索引

*   [**`.agents/AGENTS.md` (AI 全局红线宪法)**](.agents/AGENTS.md)
*   [**`.agents/README.md` (MCP 探针接入表与 5 分钟 Checklist)**](.agents/README.md)
