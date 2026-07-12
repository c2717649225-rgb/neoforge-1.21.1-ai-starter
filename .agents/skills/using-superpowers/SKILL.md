---
name: using-superpowers
description: Use when starting Major feature development or refactoring conversations - establishes how to find and use skills, while allowing minor/trivial tasks to bypass brainstorming.
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.

*例外：本项目中的 Minor 业务开发（添加配方、普通物品/方块、修复编译错、数值微调等非核心大重构）与纯概念咨询，100% 豁免此规则。此场景下，请直接加载并阅读 neoforge 领域 Skill 开始写码，严禁进行 brainstorming 与写 TDD 假测试。*
</EXTREMELY-IMPORTANT>

## The Rule

**Invoke relevant or requested skills BEFORE any response or action** — including clarifying questions, exploring the codebase, or checking files. If it turns out wrong for the situation, you don't have to use it.

**Before entering plan mode (or writing implementation plans via writing-plans) for Major features:** if you haven't already brainstormed, invoke the brainstorming skill first. Minor tasks can directly write implementation plans without brainstorming.

Then announce "Using [skill] to [purpose]" and follow the skill exactly. If it has a checklist, create a todo per item.

## Skill Priority

Minecraft 模组开发任务中，领域/实现技能具有绝对的最高优先级（1. `neoforge` + `workspace_setup` + `verification` 为一等公民核心必读），其余辅助/过程性技能在 Major 核心设计、多任务或复杂调试时按需调用。

- "Let's build a Custom Machine (Major)" -> superpowers:brainstorming first, then implementation skills.
- "Add a simple Item/Recipe (Minor) or Fix compilation" -> Skip brainstorming/systematic-debugging, load neoforge directly.

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Minor/Trivial questions are exempted. For Major tasks, invoke the skill. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Minor tasks are exempted. Major tasks must not bypass. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Platform Adaptation

If your harness appears here, read its reference file for special instructions:

- Codex: `references/codex-tools.md`
- Pi: `references/pi-tools.md`
- Antigravity: `references/antigravity-tools.md`

## User Instructions

User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills, which in turn override default behavior. Only skip skill workflows or instructions when your human partner has explicitly told you to.
