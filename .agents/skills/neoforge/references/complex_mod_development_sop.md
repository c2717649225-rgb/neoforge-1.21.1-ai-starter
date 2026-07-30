---
status: verified
pin_minecraft: 1.21.1
pin_neo: 21.1.x
last_verified: 2026-07-30
---
# 复杂/大型模组开发与移植通用 7 阶段 SOP (Complex Mod Stepped Pipeline)

> [!IMPORTANT]
> **物理规则**：为防止 AI 在处理大型/复杂模组（如包含大量物品/方块、BlockEntity、实体、GUI、能力或世界生成）时由于上下文过载导致**偷工减料、丢三落四或写空方法**，必须遵循本 7 阶段步进 SOP。

---

## 🎯 阶段 0：开局需求评估与动态剪枝 (Scope Intake & Dynamic Pruning)

在开始写码前，AI 必须根据目标模组的真实功能，明确标记每个 Phase 为 `Active`（激活）或 `Skipped`（剪枝跳过）：

| 阶段 | 涵盖功能 | 剪枝跳过条件 (Skipped Condition) |
| --- | --- | --- |
| **Phase 1** | 物品/方块/页签注册、语言包与纹理贴图 | 必然激活 (Active) |
| **Phase 2** | 自定义 RecipeType/Serializer、掉落表、Tags | 无自定义配方或特殊掉落表时可剪枝 |
| **Phase 3** | Data Components (1.21.1) 与 BlockEntity 持久化 | 无数据组件与无 BlockEntity 状态存盘时可剪枝 |
| **Phase 4** | FE/Fluid/ItemHandler Capabilities & Mixins | 无能量/流体/槽位接线且无 Mixin 底层切面时可剪枝 |
| **Phase 5** | 弹道实体、NPC/Boss 实体、EntityRenderer 与 AI Goal | **无自定义实体或无投掷物时必须显式剪枝跳过** |
| **Phase 6** | 矿石生成、Jigsaw 结构遗迹、Biomes 配置 | **无世界生成或无自然结构时必须显式剪枝跳过** |
| **Phase 7** | Menu GUI、C2S/S2C Payload 网络同步与 GameTest | 无复杂 UI 菜单与无联机同步时可简化 |

---

## 🚀 7 阶段步进 SOP 详细执行流程

### Phase 1: 基础骨架与资源先行 (Foundation & Assets First)
1. 先建立包结构，将贴图与资源文件原样迁移至 `src/main/resources/assets/<modid>/textures/`；
2. 完成 `DeferredRegister` 对 Item/Block/CreativeTab 的声明与注册；
3. 执行 `python .agents/run.py .agents/gates/pipeline.py --profile fast` 验证 L2.5 资源对账；
4. **Git Commit**: `feat(phase1): foundation & assets for <modid>`

### Phase 2: 配方树与数据生成 (Custom Recipe Systems & DataGen)
1. 编写自定义 `RecipeType` 与 `RecipeSerializer`（若有）；
2. 继承 `RecipeProvider` 与 `LootTableProvider` 完成 DataGen Provider 写码（拒绝空实现）；
3. 执行 `./gradlew runData` 验证 JSON 物理产出；
4. **Git Commit**: `feat(phase2): custom recipes & datagen for <modid>`

### Phase 3: 数据组件与持久化 (Data Components & BlockEntity)
1. 注册 1.21.1 `DataComponentType`（禁止 1.20.x NBT `getOrCreateTag`）；
2. 编写 `BlockEntity` / `SavedData` 的 `loadAdditional` 和 `saveAdditional` 读写路径；
3. 静态门禁防范：确认静态块/字段中无 eager `.get()` 延迟解包隐患；
4. **Git Commit**: `feat(phase3): data components & persistence for <modid>`

### Phase 4: 能力对接与底层切面 (Capabilities & Mixins)
1. 注册 FE 能量 (`Capabilities.EnergyStorage.BLOCK`)、流体与 `IItemHandler`；
2. 如有 Mixin 切面，完成注入并在沙盒中自检方法签名；
3. **Git Commit**: `feat(phase4): capabilities & mixins for <modid>`

### Phase 5: 实体、投掷物与 AI 行为 (Entities, Projectiles & Mob AI)
1. 注册 `EntityType` 与对应的弹道/Boss 实体类；
2. 在 `Dist.CLIENT` 侧注册 `EntityRenderer` 与 `EntityModel`；
3. 编写 `GoalSelector` AI 寻找逻辑；
4. **Git Commit**: `feat(phase5): entities & ai for <modid>`

### Phase 6: 世界生成与结构集 (Worldgen & Structures)
1. 配置 `PlacedFeature` 矿石/植物生成数据；
2. 编写 Jigsaw 结构代码（使用 1.21.1 最新 11 参数 `JigsawPlacement.addPieces` 签名）；
3. **Git Commit**: `feat(phase6): worldgen & structures for <modid>`

### Phase 7: UI 界面、网络同步与验收 (Menu, Screen, Payloads & GameTest)
1. 实现 `AbstractContainerMenu` 并在服务端挂载 `DataSlot` 同步属性；
2. 注册 `CustomPacketPayload` 与 `PayloadRegistrar` 组装 C2S/S2C 字节流；
3. 编写针对核心逻辑的 `@GameTest`；
4. **全量过关**: `python .agents/run.py .agents/gates/pipeline.py --profile fast`（或 `--profile major`）；
5. **Git Commit**: `feat(phase7): ui, network & gametest for <modid>`
