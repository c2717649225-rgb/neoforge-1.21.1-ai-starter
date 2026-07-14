# 模组开发项目规范 (Minecraft Modding Rules)

> [!IMPORTANT]
> **P0 为物理硬红线，违反可能直接导致游戏崩溃或存档损坏，必须优先遵守。P1 为推荐规范。**

---

## 📌 项目元数据自适应规范
- **默认参考**: Minecraft 1.21.1 + NeoForge 21.1.x，Mod ID: `tutorialmod`，Java 包命名空间同主入口。
- **真元数据源**: AI 助手在运行代码或生成资源前，**必须首先读取 `gradle.properties` 与 `neoforge.mods.toml` 动态获取当前项目的真实 Mod ID 与 Java 包命名空间**，根据这些元数据进行符号替换，禁止写死。

---

## 🚨 部分一：P0 级别 - 物理硬红线 (Hard Constraints)

1. **ItemStack NBT 禁用**：数据读写必须 100% 使用类型安全的 Data Components 框架。绝对禁止混用 1.20.x 的 NBT 读写（如 `getOrCreateTag`）。*后果：1.21.1 原版物理移除了 NBT 读写管线，混用会导致严重编译错误与物品栏损坏。*
2. **Record Codec 字段顺序一致性**：Codec 内部字段声明顺序必须与 Java Record 类构造器参数顺序 100% 绝对一致。*后果：防止反序列化时抛出 ClassCastException 触发游戏直接崩溃。*
3. **物理客户端隔离**：所有 Renderer、Model、Screen 相关类，必须隔离在标记了 `value = Dist.CLIENT` 的独立类中。通用逻辑绝对禁止直接引用客户端包下类。*后果：防止专用服务器启动时由于类验证失败崩溃。*
4. **网络 Payload 线程隔离**：Handler 默认运行在网络线程，任何涉及修改世界、玩家状态的操作，必须包裹在 `context.enqueueWork(...)` 中提交给主线程。*后果：避免多线程并发修改世界导致线程冲突闪退。*
5. **延迟解包安全**：类静态成员或静态初始化块（static block）中，绝对禁止直接对注册项调用 `.get()`（必须延迟在运行期或事件监听中访问）。*后果：防止在 Registry 注册事件调度前提前访问实例导致 NPE 直接崩溃。*
6. **事件总线订阅**：@EventBusSubscriber 一律省略 bus（由 IModBusEvent 等自动路由）；订阅监听方法必须 static。具体 Event 归属与订阅规范见 [event_system.md](skills/neoforge/references/event_system.md)。

---

## 🛠️ 部分二：P1 级别 - 工程开发规范 (Guidelines)

1. **资源生成与 DataGen**：配方、掉落表、模型、标签等 JSON 资源，必须通过 `DataProvider` 编写及自测脚本更新，严禁手动手写（汉化 `zh_cn.json` 与 metadata 配置除外）。目录执行严格单数（如 `loot_table`、`recipe`）。
2. **命名空间与标签**：跨模组通用标签必须使用 `c` 命名空间（如 `c:gems/ruby`），严禁使用 `forge` 或 `neoforge`。
3. **自测纠错优先**：任何代码修改或重构后，必须优先阅读编译报错，并运行终端门禁自测脚本，以编译器和自检输出为准。
4. **精确最小编辑**：修改已有源码时，只做精确、最小范围的补丁式编辑。检测到本地命名空间不一致时，优先调用初始化脚本重构，禁止手工碎片化重构。

---

## 🚀 部分三：按需加载与双 Agent 协作心智

1. **默认开发路径 (Primary Path)**：
   `AGENTS.md` -> 查阅 `neoforge/` (+ 按需 references) -> 实现写码 -> 运行 `compile_and_repair.py` 自检 -> 证据齐全向用户汇报。
2. **任务分级与免计划书豁免**：
   - **Minor 业务/简单修复**：100% 豁免设计与计划流程。允许直接写码并跑编译门禁，禁止空转。
   - **Major 变动（实体/网络/Mixin/大重构）**：建议在修改前先以短消息给出 Proposed Changes 方案，待确认后再开写。
3. **白名单技能限制**：
   AI 助理日常仅允许加载以下 4 个核心技能，其余所有过程型技能已被归档禁用，禁止加载：
   - `neoforge` (领域 API) / `workspace_setup` (重构与自检) / `systematic-debugging` (诊断) / `task_monitor` (监控)
4. **与外部协作提示词关系**：
   在双 Agent（如 Grok/Gemini）协作流程下，协作节奏以用户提示词与本文件红线为唯一依据，**不要**在仓库内强行叠加历史 superpowers 辅助链（如 writing-plans/SDD/CR 等）。
5. **门禁命令**：
   - 编译自检: `python .agents/skills/workspace_setup/scripts/compile_and_repair.py` (加 `--with-data` 生成 JSON 资源)
   - 工作区初始化与重构: `python .agents/skills/workspace_setup/scripts/init_workspace.py`
