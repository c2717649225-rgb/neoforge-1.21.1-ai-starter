# NeoForge 1.21.1 AI Starter

[![Build](https://github.com/c2717649225-rgb/neoforge-1.21.1-ai-starter/actions/workflows/build.yml/badge.svg)](https://github.com/c2717649225-rgb/neoforge-1.21.1-ai-starter/actions/workflows/build.yml)
[![Minecraft](https://img.shields.io/badge/Minecraft-1.21.1-green)](https://www.minecraft.net/)
[![NeoForge](https://img.shields.io/badge/NeoForge-21.1.x-orange)](https://neoforged.net/)
[![Java](https://img.shields.io/badge/Java-21-blue)](https://adoptium.net/)

## 这个项目是干什么的？

这是一个面向 **Minecraft Java 版 1.21.1 + NeoForge** 的**开箱即用开发起点**。  
你 clone / 使用本模板之后，会同时得到：

1. 一套 **1.21.1 NeoForge 模组工程模板**（能编译、能跑客户端）；  
2. 一个 **`.agents` 文件夹**：内含工具、skills、MCP 探针等，用来帮助 AI 按统一红线写代码、查源码、做编译自检。

它**明确分成两部分**：

| 部分 | 是什么 | 包含什么 |
|------|--------|----------|
| **① `.agents/`** | **AI 辅助开发工具包**（可单独理解，也可拷到其他 NeoForge 1.21.1 工程复用） | 开发红线（`AGENTS.md`）、NeoForge 技能与参考文档、本地源码 MCP 探针、工作区初始化与编译自愈脚本等，一系列帮助 AI 开发模组的能力 |
| **② 除 `.agents` 以外的工程** | **1.21.1 NeoForge 模组开发模板**（标准 Gradle / NeoForge 脚手架） | `src/`、`build.gradle`、`gradle.properties`、`gradlew`、示例模组 `tutorialmod` 等——负责「能编译、能跑客户端」的模组工程本身 |

```text
neoforge-1.21.1-ai-starter/
├── .agents/          ← ① AI 工具包（红线、skills、MCP、自检脚本）
├── src/              ← ② 模组模板源码
├── build.gradle      ← ② 构建与依赖
├── gradle.properties ← ② 模组元数据（mod_id 等）
├── gradlew*          ← ② Gradle 包装器
└── README.md         ← 本说明（GitHub 首页介绍）
```

- 开**新模组**：以整仓为模板 → 改 `gradle.properties` → 跑初始化 → 接 MCP → 写业务代码。  
- 只要 **AI 能力**：也可把 `.agents/` 拷进已有 1.21.1 NeoForge 项目（目标版本需一致）。  
- 仓库内最小示例骨架为 `tutorialmod`，不是最终玩法，只是可编译的 starter。

> **GitHub 语言统计**会偏 Python / JS（`.agents` 工具链），模组本体与构建仍是 **Java + Gradle**。

---

## 两部分各自提供什么

### ① `.agents`（AI 工具包）

| 能力 | 说明 |
|------|------|
| **开发红线** | 1.21.1 硬约束（Data Components、客户端隔离、网络线程等） |
| **技能与参考** | NeoForge 常见系统的写法索引与示例 |
| **源码 MCP 探针** | 检索本机 Gradle 缓存中的 Minecraft / NeoForge 源码（AI 侧建议必接） |
| **工作区初始化** | 按 `gradle.properties` 一键对齐包名、资源命名空间、mixins 等 |
| **编译网关** | `compile_and_repair.py`；注册/DataGen 变更可加 `--with-data` |

### ② 模组模板（工程其余部分）

| 能力 | 说明 |
|------|------|
| **MDK 骨架** | NeoForge 21.1.x + Java 21，可 `compileJava` / `runClient` |
| **示例模组** | `tutorialmod` 最小入口与资源命名空间 |
| **标准构建** | Gradle Wrapper、CI 构建工作流 |

---

## `.agents` 目录说明（点开查看）

> 以下使用 GitHub 可折叠区块。默认收起，需要时点标题展开。

<details>
<summary><strong>总览：目录树</strong></summary>

```text
.agents/
├── AGENTS.md              # AI 开发红线（宪法，请加载到客户端）
├── README.md              # 工具包接入说明（MCP Checklist 等）
├── VERSION                # 工具包版本与目标 MC / NeoForge
├── agent_workflow.md      # Implementer / Reviewer 协同与自检流程
├── init_workspace.py      # 一键初始化入口（转发到 workspace_setup 脚本）
├── mcp/
│   └── minecraft_mcp.py   # 本地源码 MCP 探针（检索 Gradle 缓存里的 MC/Neo 源码）
└── skills/                # 按任务选用的技能包（每个子目录一份 SKILL.md）
    ├── neoforge/          # ★ 核心：1.21.1 NeoForge 写法与 references
    ├── workspace_setup/   # 改名/初始化 + 编译自愈脚本
    └── …                  # 流程类 skills（计划、调试、评审等）
```

本地生成、**不入库**（见根 `.gitignore`）：`mcp/mcp_jar_cache.json`、各类 `__pycache__/`。

</details>

<details>
<summary><strong>根文件与脚本</strong></summary>

| 路径 | 作用 |
|------|------|
| [`AGENTS.md`](.agents/AGENTS.md) | **全局红线**：Data Components、客户端隔离、网络线程、DataGen 例外、MCP 门禁、编译分级等。AI 客户端应加载此文件。 |
| [`README.md`](.agents/README.md) | **给人看的接入指南**：5 分钟 Onboarding、如何注册 MCP。 |
| [`VERSION`](.agents/VERSION) | 工具包版本号与锚定平台（当前 1.0.0 / MC 1.21.1 / Neo 21.1.x）。 |
| [`agent_workflow.md`](.agents/agent_workflow.md) | 双角色流程说明（Implementer 实现 / Reviewer 审查 + 本地编译网关），不绑定具体商业模型名。 |
| [`init_workspace.py`](.agents/init_workspace.py) | **一键初始化入口**。根据 `gradle.properties` 对齐包名、资源命名空间、mixins 等（内部调用 `skills/workspace_setup/scripts/init_workspace.py`）。 |

常用命令：

```bash
python .agents/init_workspace.py
python .agents/skills/workspace_setup/scripts/compile_and_repair.py
python .agents/skills/workspace_setup/scripts/compile_and_repair.py --with-data
```

</details>

<details>
<summary><strong>mcp/ — 源码探针（Required）</strong></summary>

| 路径 | 作用 |
|------|------|
| [`mcp/minecraft_mcp.py`](.agents/mcp/minecraft_mcp.py) | 零依赖 MCP 服务：在 AI 客户端中注册后，可对本地 `~/.gradle` 缓存与项目源码做 `search_class` / `grep_source` / `read_class` 等，减少瞎编 1.20 API。 |

- **接入方式**：见 [`.agents/README.md`](.agents/README.md)。  
- **缓存** `mcp_jar_cache.json` 首次运行后生成，仅本机使用，已 gitignore。  
- 红线要求：MCP 未就绪时 AI 应停工，不得凭记忆交付依赖原版/NeoForge 细节的代码。

</details>

<details>
<summary><strong>skills/ — 技能包总表</strong></summary>

每个子目录一般有一份 `SKILL.md`：描述「何时用、怎么做」。AI 按任务匹配加载，无需你手动全读。

#### 模组领域（优先）

| 技能目录 | 作用 |
|----------|------|
| **`neoforge/`** | **核心**。1.21.1 NeoForge 约束表、注册/组件/网络等骨架（`{{MOD_GROUP}}` 等占位）、`references/` 专题文档、`examples/` 示例；并规定 compile / `--with-data` 自检。 |
| **`workspace_setup/`** | 模组改名/初始化工作流；`scripts/init_workspace.py`、`compile_and_repair.py`；多 worktree 禁止并行重构。 |

#### 工程流程（通用）

| 技能目录 | 作用 |
|----------|------|
| **`using-superpowers/`** | 元技能：有适用 skill 时必须先读再执行。 |
| **`brainstorming/`** | 需求澄清与方案设计（含可选可视化 companion 脚本）。 |
| **`writing-plans/`** | 把规格写成可执行的分步实现计划。 |
| **`executing-plans/`** | 按计划落地；角色抽象为 Implementer / Reviewer。 |
| **`subagent-driven-development/`** | 多子代理分工实现 + 任务级审查（含辅助脚本）。 |
| **`dispatching-parallel-agents/`** | 多个独立任务并行派生子代理时的用法。 |
| **`test-driven-development/`** | 先测后写；反模式说明见同目录文档。 |
| **`systematic-debugging/`** | 系统化排错（根因、等待条件、防回归等）。 |
| **`verification-before-completion/`** | 声称完成前必须有编译/验证证据。 |
| **`requesting-code-review/`** | 发起代码审查时的检查清单与 reviewer 提示。 |
| **`receiving-code-review/`** | 收到审查意见时如何核实再改，避免盲从。 |
| **`finishing-a-development-branch/`** | 功能做完后如何收尾（合并/PR/清理选项）。 |
| **`using-git-worktrees/`** | 用 git worktree 隔离功能分支时的约定。 |
| **`task_monitor/`** | 长任务（如下载、Gradle）的监控与卡死处理思路。 |
| **`writing-skills/`** | 如何编写/改进本仓库的 skill 本身（维护工具包用）。 |

</details>

<details>
<summary><strong>skills/neoforge/ — 再展开一点</strong></summary>

| 路径 | 作用 |
|------|------|
| `SKILL.md` | 总入口：1.21.1 弃用对照、Few-shot 骨架、reference 索引、自检命令。 |
| `references/*.md` | **按主题的权威写法**（约 40 篇）：如 data_components、network_payloads、custom_entities、mixins、DataGen、Capabilities 等。写功能时 AI 应先读对应页再写代码。 |
| `examples/*.md` | 更完整的示例蓝图：注册、创造标签、DataGen、配方标签、多加载器解耦等。 |

示例包名在文档里可能是 `tutorialmod` 或占位符；写入工程前必须按当前 `gradle.properties` 替换。

</details>

<details>
<summary><strong>skills/workspace_setup/scripts/ — 脚本</strong></summary>

| 脚本 | 作用 |
|------|------|
| `init_workspace.py` | 读 `gradle.properties`，重构资源命名空间、主类 MODID、mixins、同步 `.agents/AGENTS.md` 元数据等。 |
| `compile_and_repair.py` | 默认 `gradlew compileJava`；加 `--with-data` 时再跑 `runData`。失败时尽量解析 Java 报错行并打印上下文，供 AI 自愈。 |

</details>

---

## 环境要求

- **JDK 21**（`JAVA_HOME` 或 PATH 可用，`java -version` 能看到 21）
- **Python 3**（运行 init / MCP / 自检脚本）
- Git；首次构建会下载依赖，需足够磁盘与网络

---

## 模组开发起手四步

### 第一步：配置元数据

编辑根目录 `gradle.properties`：

```properties
mod_id=yourmod
mod_name=Your Mod Name
mod_group_id=com.yourpackage.yourmod
```

### 第二步：一键初始化

在 AI 聊天中发送：

> 帮我初始化一下这个工作区

或在终端执行：

```bash
python .agents/init_workspace.py
```

将按 `gradle.properties` 对齐 Java 包、资源命名空间、主类常量与 mixins 等。

### 第三步：注册源码 MCP（Required）

将本地探针注册到你使用的 AI 客户端（MCP 配置）：

- 脚本路径：`.agents/mcp/minecraft_mcp.py`
- 配置方式见 [`.agents/README.md`](.agents/README.md)

未注册时，AI 不得凭记忆猜测原版 / NeoForge API。

### 第四步：编译自检

首次验证环境，以及之后每次修改 Java：

```bash
python .agents/skills/workspace_setup/scripts/compile_and_repair.py
```

涉及注册项或 DataGen Provider 变更时：

```bash
python .agents/skills/workspace_setup/scripts/compile_and_repair.py --with-data
```

可选：

```bash
./gradlew runClient
```

---

## 文档索引

| 文档 | 用途 |
|------|------|
| [`.agents/AGENTS.md`](.agents/AGENTS.md) | AI 全局红线（请让客户端加载） |
| [`.agents/README.md`](.agents/README.md) | MCP 接入与 5 分钟 Checklist |
| [`AGENTS.md`](AGENTS.md) | 根指针（指向 `.agents/AGENTS.md`） |
| [`.agents/VERSION`](.agents/VERSION) | 工具包版本与目标平台 |

---

## 许可

- 仓库模板（含基于 [NeoForged MDK](https://github.com/neoforged/MDK) 的脚手架文件）以根目录 [`LICENSE`](LICENSE)（MIT）提供；MDK 原文说明见 [`TEMPLATE_LICENSE.txt`](TEMPLATE_LICENSE.txt)。
- 你基于本模板做出的**具体模组**，请在 `gradle.properties` 的 `mod_license` 中自行声明发布许可。

---

## English

**NeoForge 1.21.1 AI Starter** is a ready-to-use starting point for Minecraft **1.21.1 + NeoForge 21.1.x**. The repo has **two parts**:

| Part | Role |
|------|------|
| **`.agents/`** | AI-assisted modding toolkit (rules, skills/refs, local source MCP probe, init + compile-and-repair scripts). Can be copied into other 1.21.1 NeoForge projects. |
| **Everything else** | Mod development template (Gradle/NeoForge scaffold, `src/`, `tutorialmod` starter). |

**Quick start**

1. Edit `mod_id` / `mod_name` / `mod_group_id` in `gradle.properties`
2. Run `python .agents/init_workspace.py`
3. Register `.agents/mcp/minecraft_mcp.py` as an MCP server in your AI client ([guide](.agents/README.md))
4. Run `python .agents/skills/workspace_setup/scripts/compile_and_repair.py`

Requires **JDK 21** and **Python 3**. GitHub language stats are skewed by tooling scripts under `.agents/`; the mod itself is Java.
