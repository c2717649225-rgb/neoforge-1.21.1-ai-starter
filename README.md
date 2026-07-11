# NeoForge 1.21.1 AI Starter

[![Build](https://github.com/c2717649225-rgb/neoforge-1.21.1-ai-starter/actions/workflows/build.yml/badge.svg)](https://github.com/c2717649225-rgb/neoforge-1.21.1-ai-starter/actions/workflows/build.yml)
[![Minecraft](https://img.shields.io/badge/Minecraft-1.21.1-green)](https://www.minecraft.net/)
[![NeoForge](https://img.shields.io/badge/NeoForge-21.1.x-orange)](https://neoforged.net/)
[![Java](https://img.shields.io/badge/Java-21-blue)](https://adoptium.net/)

## 这个项目是干什么的？

这是一个面向 **Minecraft Java 版 1.21.1 + NeoForge** 的**开箱即用开发起点**：  
你 clone / 使用模板之后，就可以获得一个1.21.1neoforge的模组模板，以及一个包含了工具,skills,mcp等等能帮助ai开发模组的.agents文件夹,它能让按统一红线辅助写代码、查源码、编译自检。

它**明确分成两部分**：

| 部分 | 是什么 | 包含什么 |
|------|--------|----------|
| **① `.agents/`** | **AI 辅助开发工具包**（可单独理解、也可拷到其他 NeoForge 1.21.1 工程复用） | 开发红线（`AGENTS.md`）、NeoForge 技能与参考文档、本地源码 MCP 探针、工作区初始化与编译自愈脚本等一系列帮助ai开发模组的东西 |
| **② 除 `.agents` 以外的工程** | **1.21.1neoforge模组开发模板**（标准 Gradle / NeoForge 脚手架） | `src/`、`build.gradle`、`gradle.properties`、`gradlew`、示例模组 `tutorialmod` 等——负责「能编译、能跑客户端」的模组工程本身 |

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
