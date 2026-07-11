# 模组开发项目规范 (Minecraft Modding Rules)

## 📌 项目元数据自适应规范 (AI 生成代码的唯一基准)
- **目标平台**: Minecraft 1.21.1 + NeoForge 21.1.x (21.1.x 是 NeoForge 版本线，服务于 MC 1.21.1)
- **参考 Mod ID**: tutorialmod (已由初始化引擎自动对齐)
- **参考 Mod Name**: Tutorial Mod (已由初始化引擎自动对齐)
- **参考基类路径**: [TutorialMod.java](./src/main/java/com/tutorial/tutorialmod/TutorialMod.java)

> [!IMPORTANT]
> **动态读取项目元数据规范**：
> 以上参数仅为默认参考。AI 助手在运行代码、重构类名或生成资源前，**必须首先读取 `gradle.properties`（获取 `mod_id` 和 `mod_group_id`）及 `neoforge.mods.toml` 动态获取当前项目的真实 Mod ID、Mod 名称、入口主类及 Java 包命名空间**，根据这些元数据进行符号替换，严禁在生成任何代码、资源包路径（assets/data 命名空间）时做出写死元数据的假设。

---

## 🚨 1.21.1 开发与构建硬性红线 (Core Constraints)

1. **【数据与 NBT 分流】**：
   - **物品（ItemStack）**：自定义数据读取和持久化**必须 100% 使用类型安全的 Data Components 框架**，绝对禁止混用 1.20.x 的 NBT 读写（如 `getOrCreateTag` 等旧方法）。
   - **世界存盘 / BlockEntity / 原版管线**：允许使用 `CompoundTag`，且必须遵循 1.21 的 `HolderLookup.Provider` 等现行 API。
   - **实体与玩家数据扩展**：纯 NeoForge 工程**首选且强制采用原生的 Data Attachments**，只有在与原版实体存盘管线交互时才允许使用 Mixin 并注入 `CompoundTag`。
2. **【爆档防线】Codec 顺序一致性**：在编写 `RecordCodecBuilder` 时，Codec 内部的字段声明顺序必须与 Java Record 类主构造器中的参数声明顺序 **100% 绝对一致**，防止读档时 ClassCastException 导致存档数据损坏。
3. **【崩溃防线】物理客户端隔离**：所有渲染器（Renderer）、模型（Model）、界面（Screen）相关类，必须完全物理隔离在标记了 `value = Dist.CLIENT` 的独立类中。严禁在通用逻辑中直接引用 `net.minecraft.client` 命名空间下的类，防止联机专用服务器（Dedicated Server）启动类验证崩溃。
4. **【网络红线】线程隔离安全**：网络 Payload 的 Handler 默认运行在网络线程，任何涉及修改世界、玩家状态的操作，**必须**包裹在 `context.enqueueWork(...)` 中提交给游戏主线程运行。
5. **【网络红线】协议版本协商**：所有网络数据包（CustomPacketPayload）必须显式附加版本信息进行协商（如 `.versioned("1.0.0")`）。
6. **【崩溃防线】延迟解包安全**：在类静态成员声明或静态初始化块中，**绝对禁止过早对注册项容器调用 `.get()`**，否则由于静态加载期在 Registry 注册事件调度之前，会导致 `NullPointerException` 或 `Registry not present` 直接导致游戏启动闪退。
7. **【资源生成红线】DataGen 驱动与例外**：
   - 所有的静态配方（recipe）、掉落表（loot_table）、方块状态（blockstate）、模型（model）、标签（tags/block 与 tags/item）等 JSON 资源，**必须**使用 `DataProvider` 编写并通过 `gradlew runData` 自动编译生成，严禁手动手写物理 JSON。
   - **手写例外白名单**：允许手写 `zh_cn.json` / `en_us.json` 翻译、`pack.mcmeta`、`*.mixins.json`、`neoforge.mods.toml` 以及构建模板配置。
8. **【目录单数规范】**：1.21.1 严格执行：掉落表为 `loot_table`，配方为 `recipe`，标签为 `tags/block` 与 `tags/item`，严禁使用旧版复数目录名。
9. **【命名空间规范】**：跨模组通用的物品/方块标签必须使用公认的 `c` 命名空间（如 `c:gems/ruby`），严禁使用 `forge` 或 `neoforge`。

---

## 🛠️ AI 行为与工作流规约 (AI Workflow & Output Rules)

1. **【MCP 注册必要门禁】**：
   - 凡涉及 Minecraft 原版或 NeoForge API、映射名、事件签名等底层信息，**必须优先通过本地 MCP 工具查询**（如 `search_class`、`grep_source` 等）。
   - **未就绪即停工**：若 MCP 工具不可用、未加载或调用失败，AI 助手**必须立即停止编写**依赖上述细节的代码，向用户输出错误提示，指引其去查阅 `.agents/README.md` 中的 MCP 客户端注册 Checklist，绝对禁止凭记忆猜测 API 交付代码。
2. **【自测流程】编译与数据生成自检**：
   - 每次对 Java 源码进行修改或重构后，**【必须】**在向用户汇报前在终端中运行并通过 **`python .agents/skills/workspace_setup/scripts/compile_and_repair.py`** 编译防御守护脚本。若报错，AI 必须根据报错日志的上下文反馈环自主修复，直至 100% 编译通过，严禁将未通过编译检查的代码交付。
   - **DataGen 分级运行**：默认运行自检脚本仅执行 `compileJava`。仅当新增或修改了注册项、DataGen Provider（数据提供者）时，才触发 `--with-data` 参数同步运行 `runData` 更新 JSON。
3. **【工作区自动初始化命令】**：
   - 当检测到本地资源目录命名空间（如还残留 `examplemod` 目录）与 `gradle.properties` 不一致，或者用户要求“初始化工作区”时，**【必须】**优先在终端中运行 **`python .agents/init_workspace.py`** 一键初始化存根脚本，严禁由 AI 手工碎片化执行改名与 TOML 文件重构。
4. **【导包与类名自适应红线】**：
   - 在查阅 `skills/` 目录下的任何代码示例时，**绝对禁止**直接复制示例中的 `package com.tutorial.tutorialmod...` 或 `import com.tutorial.tutorialmod.TutorialMod`。AI 必须根据当前项目的真实包结构与主类名进行**动态重构替换**后再应用到源码中。
5. **【语言与注释要求】**：
   - AI 回复与代码注释一律使用中文，适当添加简明扼要的中文代码注释。
   - 每次修改代码时，都必须简述修改原因及其底层工作原理。
6. **【代码整洁与 Markdown 放行白名单】**：
   - **禁止乱堆 md 文档**：除了项目运行必需的临时追踪文件和团队约定的计划路径外，绝对禁止在 `src/` 目录或发布树中新建说明文档。
   - **Markdown 路径放行白名单**：允许且仅允许新建或修改 `.agents/**`、`**/task.md`、`**/implementation_plan.md`、`**/walkthrough.md` 等开发计划与日志文件。
   - 必须在提交或保存代码前彻底清除无用的 Imports，保持代码干净整洁。单个 Java file 超过 500 行必须考虑拆分。
7. **【本地工具调用】**：
   - 需要深度研究代码时，积极调用现有的文件查看工具、全文搜索工具以及自定义的 `search_class`/`grep_source` 等 MCP 工具获取实时上下文。

---

## 🛡️ AI 行为与代码修改安全规约 (Safety & Refactoring Constraint)

1. **编辑原则：精确最小补丁**：
   - 修改已有源码时，**必须**做精确、最小范围的补丁式编辑。
   - **绝对禁止**在没有用户明确要求的情况下，整体重写已有文件。这会极易在覆盖过程中抹除已有的物品栏保存（Capability）、事件总线监听或 Mixin 的注册，从而引发“爆档”和崩溃。
2. **代码修改最小化原则**：
   - 只改需要改的代码，不要“顺便”重构、优化、重命名不相关的类或方法。
3. **语言与注释要求**：
   - 适当添加简练的中文核心逻辑注释，在静态定义或常规重写方法上绝对禁止留下多余的 `// TODO` 或者是废话注释。
