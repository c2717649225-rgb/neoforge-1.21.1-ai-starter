---
name: workspace_setup
description: 适用于用户请求项目初始化、工作区配置、修改模组名称、重命名 Mod ID（改名）或者重构包名与主类路径等场景。
---

# 项目初始化与重构工作流规约 (Workspace Setup Skill)

当用户请求初始化新项目模板或在开发中途修改 Mod ID（重构命名空间）时，您必须遵循本技能的执行流。

## 🚨 核心执行红线

1. **绝对禁止手工碎片化重构**：严禁手动重命名资源目录、手工对齐本地化键或用文本工具批量改写类常量。您必须调用重构脚本一键完成。
2. **强制运行重构脚本**：您必须运行以下命令，由确定性的 Python 引擎执行项目级命名空间与包重构：
   ```bash
   python .agents/skills/workspace_setup/scripts/init_workspace.py
   ```
3. **编译自检**：重构完成后，必须在向用户汇报前运行自测纠错脚本，验证重构后模组的完整编译状态：
   ```bash
   python .agents/skills/workspace_setup/scripts/compile_and_repair.py
   ```
4. **【并行重构红线】Worktree 共享冲突防御**：
   - 当同一个物理仓库存在多个活动 Git Worktree 时，**绝对禁止并行运行重构/初始化脚本（`init_workspace.py` 或大规模 rename 动作）**。
   - 重构必须保证**串行执行**，或者**仅指定唯一的 Worktree 作为重构入口**，防止公共配置文件或未提交元数据的突变破坏其他并行子智能体的编译上下文。


