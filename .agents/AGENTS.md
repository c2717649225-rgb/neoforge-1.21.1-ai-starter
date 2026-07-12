# 模组开发项目规范 (Minecraft Modding Rules)

> [!IMPORTANT]
> **P0 为物理硬红线，违反可能直接导致游戏崩溃或存档损坏，必须优先遵守。P1 为推荐规范。**

---

## 📌 项目元数据自适应规范 (AI 生成代码的唯一基准)
- **目标平台**: Minecraft 1.21.1 + NeoForge 21.1.x (21.1.x 是 NeoForge 版本线，服务于 MC 1.21.1)
- **参考 Mod ID**: tutorialmod (已由初始化引擎自动对齐)
- **参考 Mod Name**: Tutorial Mod (已由初始化引擎自动对齐)
- **参考基类路径**: [TutorialMod.java](./src/main/java/com/tutorial/tutorialmod/TutorialMod.java)

> **动态读取项目元数据规范**：
> 以上参数仅为默认参考。AI 助手在运行代码、重构类名或生成资源前，**必须首先读取 `gradle.properties`（获取 `mod_id` 和 `mod_group_id`）及 `neoforge.mods.toml` 动态获取当前项目的真实 Mod ID、Mod 名称、入口主类及 Java 包命名空间**，根据这些元数据进行符号替换，严禁在生成任何代码、资源包路径（assets/data 命名空间）时做出写死元数据的假设。

---

## 🚨 部分一：P0 级别 - 物理硬红线 (Hard Constraints)

1. **ItemStack NBT 禁用**：
   - 自定义数据读取和持久化**必须 100% 使用类型安全的 Data Components 框架**，绝对禁止混用 1.20.x 的 NBT 读写（如 `getOrCreateTag` 等旧方法）。
   - *原理解释：1.21.1 原版物理移除了 NBT 读写管线，混用会导致严重编译错误与物品栏数据损坏。*
2. **Record Codec 字段顺序一致性**：
   - 在编写 `RecordCodecBuilder` 时，Codec 内部的字段声明顺序必须与 Java Record 类主构造器中的参数声明顺序 **100% 绝对一致**。
   - *原理解释：防序列化与反序列化时的 ClassCastException 崩溃，避免读档爆档。*
3. **物理客户端隔离**：
   - 所有渲染器（Renderer）、模型（Model）、界面（Screen）相关类，必须完全物理隔离在标记了 `value = Dist.CLIENT` 的独立类中。通用逻辑中直接引用 `net.minecraft.client` 命名空间下的类是禁止的。
   - *原理解释：防止专用服务器（Dedicated Server）启动时由于类验证失败闪退。*
4. **网络 Payload 线程隔离**：
   - 网络 Payload 的 Handler 默认运行在网络线程，任何涉及修改世界、玩家状态的操作，**必须**包裹在 `context.enqueueWork(...)` 中提交给游戏主线程运行。
   - *原理解释：避免多线程并发修改世界或实体数据导致线程冲突闪退。*
5. **延迟解包安全**：
   - 在类静态成员声明或静态初始化块（static block）中，**绝对禁止直接对注册项调用 `.get()`**（必须延迟在游戏运行期或事件监听中访问）。
   - *原理解释：防止在 Registry 注册事件调度前提前访问注册实例，触发 Registry not present NPE 直接闪退。*

---

## 🛠️ 部分二：P1 级别 - 工程开发规范 (Guidelines)

### 1. 资源生成与 DataGen
- 所有的静态配方（recipe）、掉落表（loot_table）、方块状态（blockstate）、模型（model）、标签（tags/block 与 tags/item）等 JSON 资源，**必须**使用 `DataProvider` 编写并通过自检脚本更新，严禁手动手写物理 JSON。
- **手写例外白名单**：允许手写 `zh_cn.json` / `en_us.json` 翻译、`pack.mcmeta`、`*.mixins.json`、`neoforge.mods.toml` 以及构建模板配置。

### 2. 目录单数规范
- 1.21.1 严格执行：掉落表为 `loot_table`，配方为 `recipe`，标签为 `tags/block` 与 `tags/item`，严禁使用旧版复数目录名。

### 3. 命名空间与标签
- 跨模组通用的物品/方块标签必须使用公认的 `c` 命名空间（如 `c:gems/ruby`），严禁使用 `forge` 或 `neoforge`。

### 4. 编译器优先与自测纠错
- **编译器优先原则：** `[AI SUGGESTION]` 仅供参考。在修复前必须优先阅读并理解原始编译报错内容。若建议与实际报错不符，必须忽略建议，以编译器输出为准。
- 每次对 Java 源码进行修改或重构后，在向用户汇报前在终端中运行 **`python .agents/skills/workspace_setup/scripts/compile_and_repair.py`** 自测脚本。若报错，AI 必须根据反馈环自主修复。

### 5. 导包与重构约束
- **绝对禁止手工碎片化重构**：当检测到本地命名空间不一致时，必须优先运行 **`python .agents/init_workspace.py`** 重构脚本。
- **类名自适应**：在查阅任何示例代码时，必须根据当前项目的真实包结构与主类名进行动态重构替换后再应用到源码中。
- **编辑原则：精确最小补丁**：修改已有源码时，必须做精确、最小范围的补丁式编辑，绝对禁止在没有用户明确要求的情况下整体重写已有文件。
- **Markdown 路径放行白名单**：除了项目运行必需的临时文件外，允许且仅允许新建或修改 `.agents/**`、`**/task.md`、`**/implementation_plan.md`、`**/walkthrough.md` 等开发计划与日志文件。
