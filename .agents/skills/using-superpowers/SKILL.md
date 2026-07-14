---
name: using-superpowers
description: >
  [索引·非默认强制] 本仓库技能目录说明。默认开发路径是 AGENTS + neoforge + compile_and_repair。仅在需要了解「还有哪些可选过程 skill」时阅读。禁止将其解释为每条消息必须先 invoke 全部 skill。
---

# 技能目录索引说明 (Skills Index)

> **[方案二 · 按需]**
> 本 skill **不是**默认开发路径的一部分。
> Minor / 编译修复 / 概念问答：**不要**加载本 skill。
> 仅在需要宏观查阅项目包含哪些辅助流程、或用户明确要求时按需阅读。

## 默认开发路径（本仓库）
1. 阅读项目唯一的硬红线宪法 `AGENTS.md`；
2. 阅读 `neoforge/SKILL.md` 领域技能，按场景按需打开 1～3 个 `references/*.md` API 设计参考；
3. 直接开始写码；
4. 运行 `python .agents/skills/workspace_setup/scripts/compile_and_repair.py` 编译自检验证；
5. 有物理文件或编译输出证据后，再向用户汇报完成。

## 过程型技能可选索引（仅 Major/用户显式点名时可选参考）

| 辅助过程技能 | 触发条件 | 技能文档路径 |
| :--- | :--- | :--- |
| **brainstorming** | 仅 Major 大机器/大重构设计时可选，用于理清逻辑 | `../brainstorming/SKILL.md` |
| **writing-plans** | 用户明确要求提供书面计划，或 Major 复杂任务拆解时 | `../writing-plans/SKILL.md` |
| **executing-plans** | 已有冻结计划且用户要求按任务逐项执行时 | `../executing-plans/SKILL.md` |
| **subagent-driven-development** | 多 subagent 并行且用户要求使用 SDD 时 | `../subagent-driven-development/SKILL.md` |
| **using-git-worktrees** | 破坏性大重构前，或用户要求隔离开发分支时 | `../using-git-worktrees/SKILL.md` |
| **finishing-a-development-branch** | 用户明确要求提供合入分支/清理菜单时 | `../finishing-a-development-branch/SKILL.md` |
| **requesting-code-review** | 用户明确要求对改动代码进行 CR 时 | `../requesting-code-review/SKILL.md` |
| **receiving-code-review** | 收到外部代码审查意见，评估修改细节时 | `../receiving-code-review/SKILL.md` |
| **systematic-debugging** | 遇到崩溃/诡异逻辑 bug，指导排障时 | `../systematic-debugging/SKILL.md` |
| **task_monitor** | 长时间 Gradle 编译，防编译任务冻结超时监控时 | `../task_monitor/SKILL.md` |

## 🚫 禁止
*   **禁止形式主义**：禁止在 Minor 任务/简单编译修复中加载 brainstorming + writing-plans + SDD 全套流水线。
*   **禁止为走流程而走流程**：本仓库无 GameTest 测试设施时，绝对禁止为了通过 TDD 而强写空壳测试。
*   **禁止写死工具名**：隔离时若仓库提供了特定的 worktree 脚本则优先遵循，不得假设固定工具名。
