# Codex 大型移植实战审计与工具包改进方案

## 1. 背景

本方案基于以下真实 Codex 移植会话记录：

```text
C:\Users\cjm\.codex\sessions\2026\07\30\rollout-2026-07-30T11-41-54-019fb11d-47cd-7043-94e2-1c61c9cc7b4c.jsonl
```

该会话用于将 OpenModularTurrets 旧版模组移植至 Minecraft 1.21.1 + NeoForge 21.1.234。移植尚未全部结束，但日志已覆盖旧版语义审计、注册与 DataGen、BlockEntity、网络、菜单、GameTest、专用服务器、客户端渲染和资源烘焙等多个阶段，足以暴露工具包在大型移植场景中的真实优缺点。

本方案只讨论 `.agents` 工具包可控制的问题。Token 配额和用户成本管理不属于工具包职责。

## 2. 审计结论摘要

### 2.1 106.6M Token 不等于工具包文档体积

日志最终累计数据约为：

| 指标 | 数值 |
| --- | ---: |
| 总 Token | 106,682,262 |
| 输入 Token | 106,371,836 |
| 缓存输入 Token | 103,522,560 |
| 非缓存输入 Token | 约 2,849,276 |
| 普通输出 Token | 310,426 |
| 推理输出 Token | 66,074 |

约 97.3% 的输入属于缓存输入。该统计代表长会话在大量模型调用中反复携带已有上下文，并不代表 `.agents` 每次向模型注入了 106.6M 的新文档。

日志中 `.agents/AGENTS.md` 和 NeoForge `SKILL.md` 分别只被主动读取约 4 次和 5 次，完整专题 reference 的读取也仅集中于少数当前任务相关文件。因此，工具包文档不是本次上下文消耗的主要来源。

更明显的上下文来源是：

- 旧模组和新工程的大量源码读取；
- 编译、DataGen、GameTest、专服和客户端日志；
- 364 次工具调用产生的约 178 万字符输出；
- 多次单个工具输出达到约 4 万字符并被截断；
- 长会话历史在后续调用中被持续携带。

### 2.2 当前首要问题是门禁漏检，不是文档过长

真实移植中出现过以下情况：

- 合同门禁通过；
- Java 编译和静态检查通过；
- DataGen 通过；
- 资源对账 0 error / 0 warning；
- GameTest 全绿；
- 专用服务器成功启动；
- 客户端资源烘焙仍产生 226 条模型或纹理警告。

根因是旧版资源仍使用复数目录和引用：

```text
textures/blocks/
textures/items/
<modid>:blocks/...
<modid>:items/...
```

当前 `asset_gate.py` 只验证模型引用的 PNG 是否存在，没有验证这些路径是否会被 1.21.1 默认 block/item atlas 正确采集。因此资源存在时门禁会误判为通过。

## 3. 改进原则

1. 优先修复会让错误产品通过门禁的缺陷。
2. 文档负责预防，门禁负责强制，两者不能相互替代。
3. 不为同一职责建立第二套合同、索引或工作流。
4. 平台和客户端特定说明不得污染 NeoForge 领域规则。
5. 开发迭代和阶段收口使用不同粒度的验证方式。
6. 工具包只做可验证声明，避免“100%”“完美”“彻底解决”等宣传式措辞。

## 4. 第一优先级：修复真实漏检

### 4.1 增强旧式纹理路径检查

修改：

```text
.agents/gates/asset_gate.py
.agents/gates/test_gates.py
```

增加以下检测：

- 存在 `assets/<modid>/textures/blocks/`；
- 存在 `assets/<modid>/textures/items/`；
- 模型引用 `<modid>:blocks/...`；
- 模型引用 `<modid>:items/...`。

建议规则名：

```text
legacy_plural_texture_directory
legacy_plural_texture_reference
```

建议严重级别：

- 普通开发模式：至少 Warning；
- 严格资源模式或移植验收：Error；
- 需要提供目录和模型引用两类单元测试。

原因：该问题在所有现有门禁全绿后仍导致客户端资源失败，是日志证明的真实 L2.5 漏检。

### 4.2 补充移植路径规范

修改：

```text
.agents/skills/neoforge/references/complex_mod_development_sop.md
.agents/skills/neoforge/references/blockstates_models_datagen.md
```

增加明确迁移规则：

```text
textures/blocks/ -> textures/block/
textures/items/  -> textures/item/
```

迁移时还必须同步检查：

- DataGen 中的 `modLoc(...)`；
- 手写模型 JSON 的纹理引用；
- BER、粒子、GUI 和其他 Java `ResourceLocation`；
- DataGen 重新生成后的漂移；
- 客户端模型和 atlas 烘焙日志。

原因：只改门禁能够拦错，但不能帮助 AI 在移植第一阶段采用正确流程；只改文档则不能防止再次失守。

### 4.3 增加客户端资源烘焙验收

短期修改：

```text
.agents/skills/neoforge/references/quality_bar.md
```

增加人工验收项：涉及模型、BER、渲染器、粒子或纹理迁移时，必须至少进行一次客户端启动烟测，检查：

- missing texture；
- atlas stitch；
- model bake；
- renderer 和 model layer 注册；
- client-only 类加载；
- Mixin 客户端注入错误。

中期增加可选门禁：

```powershell
python .agents/run.py .agents/gates/compile_and_repair.py --with-client
```

建议行为：

1. 后台启动客户端；
2. 等待资源加载和模型烘焙完成标志；
3. 捕获上述错误特征；
4. 达到判定点后安全终止；
5. 不默认加入 `fast`；
6. `release` 在环境支持时强制执行；
7. 图形环境不可用时明确报告“未执行”，不得视为通过。

原因：L1、L2、L2.5、L3 和 L4 都不能证明客户端模型可以成功烘焙。

### 4.4 修正元数据真源描述

修改：

```text
.agents/AGENTS.md
.agents/skills/neoforge/SKILL.md
```

建议明确：

- `gradle.properties`：读取 `minecraft_version`、`neo_version`、`mod_id`、`mod_group_id`；
- `src/main/templates/META-INF/neoforge.mods.toml`：检查发布元数据和依赖范围；
- 实际 `@Mod` 主类：确认 Mod ID 与 Java package；
- 不假定 `neoforge.mods.toml` 位于项目根目录；
- 不声称 TOML 是 Java 包名的唯一真源。

原因：标准模板使用 `src/main/templates/META-INF/neoforge.mods.toml`，Java 包名由实际源码 package 和 `mod_group_id` 共同确认。原规则容易引发无效查找。

## 5. 第二优先级：优化工作流

### 5.1 删除默认 Git Commit 指令

修改：

```text
.agents/skills/neoforge/references/complex_mod_development_sop.md
```

删除每个 Phase 末尾的默认 `Git Commit` 指令。如确有必要，只保留：

> 仅在用户明确要求时创建阶段提交。

原因：工具包不应默认替用户提交代码；真实日志中 Codex 也没有执行这些指令，说明它们没有发挥作用，并可能与客户端 Git 安全规则冲突。

### 5.2 将多 Agent 编排移出 NeoForge reference

不要在 `complex_mod_development_sop.md` 增加客户端特定的 Subagent 指南。

如需记录，应放入：

```text
.agents/agent_workflow.md
```

仅保留平台中立规则：

- 只在客户端支持且上层规则允许时使用；
- 只读审计适合并行；
- 写入任务必须按文件所有权隔离；
- 多个 Agent 不得同时修改注册中心、主类或同一个 DataGen Provider；
- 主 Agent 统一执行最终门禁。

原因：Subagent 属于代理编排，不属于 NeoForge API 知识。放进 reference 会占用专题阅读额度，还可能与不同客户端的协作规则冲突。

### 5.3 区分迭代门禁与阶段收口门禁

在工作流文档中明确两种模式。

开发迭代期间，只运行受影响的最小门禁：

```powershell
python .agents/run.py .agents/gates/contract_gate.py --require
python .agents/run.py .agents/gates/compile_and_repair.py --with-static
python .agents/run.py .agents/gates/gametest_gate.py --require-tests --run
```

涉及注册或资源时再增加：

```powershell
python .agents/run.py .agents/gates/compile_and_repair.py --with-data --with-assets
```

阶段收口时只运行一次目标 profile：

```powershell
python .agents/run.py .agents/gates/pipeline.py --profile major
```

避免完整执行全部子门禁后，立即再运行 `fast` 重复编译和静态检查。

原因：日志中 `compile_and_repair.py`、`gametest_gate.py`、`contract_gate.py`、`pipeline.py` 和专服检查被多次执行。修复后的重跑多数必要，但“全套子门禁刚通过后再跑等价 profile”存在重复。

### 5.4 正确实现弃用 API 诊断

修改：

```text
.agents/gates/compile_and_repair.py
```

第一阶段：检测如下汇总提示时，仅报告“发现弃用 API，数量未知”：

```text
Note: ... uses or overrides a deprecated API
```

第二阶段：通过临时 Gradle init script 为 `JavaCompile` 注入：

```text
-Xlint:deprecation
-Xlint:removal
```

然后解析逐条 warning，输出文件和行号。不要为了工具包诊断永久修改宿主 `build.gradle`。

原因：javac 汇总 Note 无法提供可靠数量，工具包不应输出伪精确统计。

### 5.5 精确检查新版 EventBus 冗余参数

修改：

```text
.agents/gates/static_gate.py
.agents/gates/test_gates.py
```

新增：

```python
read_neo_version(project_root: Path)
```

规则：

- NeoForge 21.1.181+ 中发现 `bus = Bus.MOD` 或 `bus = EventBusSubscriber.Bus.MOD` 时输出 `eventbus_redundant_bus_param` Warning；
- NeoForge 21.1.0 至 21.1.180 不得提示冗余，因为 Mod Bus 事件仍需显式参数；
- 测试必须覆盖版本分界两侧。

原因：真实移植后期才清理旧式事件总线参数；门禁可提前提醒，但必须按精确小版本判断。

## 6. 第三优先级：避免文档和合同膨胀

### 6.1 不建立第二套移植合同

不建议新增一个没有 Schema 和 gate 的：

```text
porting_contract.template.json
```

建议改为：

```text
.agents/scaffolds/porting/porting_audit.template.md
```

只负责记录：

- `legacy_behavior`：旧版行为及源码位置；
- `modern_mapping`：1.21.1 实现映射；
- `known_deviations`：无法等价或主动修复的偏差；
- `source_assets`：资源来源、迁移清单与许可证信息。

机器验收和 GameTest 追踪继续使用现有：

```text
docs/features/*.contract.json
```

原因：独立移植合同会与 Major v2 合同、设计文档和阶段计划重复。没有 Schema 和 gate 的 JSON 也不具备真正的合同约束价值。

### 6.2 不把 PowerShell UTF-8 提示写进全局红线

仅在以下位置增加 Windows PowerShell 5.1 提示：

```text
.agents/README.md
.agents/agent_workflow.md
```

示例：

```powershell
Get-Content -Encoding UTF8 <file>
```

不要新增 `.encoding` 文件，也不要将该说明加入 `.agents/AGENTS.md`。

原因：这是特定终端工具行为，不是 NeoForge 物理红线。专用 Read 工具、PowerShell 7 和其他平台不一定存在此问题。

### 6.3 精简 SKILL.md 对 AGENTS.md 的重复

保留 `.agents/AGENTS.md` 作为唯一 P0 真源。

`SKILL.md` 仅保留 NeoForge 技能特有内容：

- reference 阅读额度；
- MCP-first 操作方法；
- StreamCodec 字段数和缓冲区补充；
- 导航索引；
- 写码后门禁入口。

NBT、Codec、客户端隔离、Payload 线程、静态 `.get()` 和 EventBus 分界无需在两处完整复述。

原因：这些规则目前在 AGENTS.md 与 SKILL.md 重复。精简收益不大，但属于安全、明确的固定上下文去重。

### 6.4 集中示例包名和 Mod ID 占位警告

在 `SKILL.md` 保留一次全局规则：

> references、examples 和 playbooks 中出现的示例包名、主类名和 Mod ID 均为占位符。

各 reference 不再重复相同的 4 至 6 行警告。

原因：一次任务通常只读一至两篇，单次收益有限，但集中规则可减少长期维护漂移。

### 6.5 清理无法验收的宣传式措辞

逐步替换：

```text
100% 毫无卡顿
完美杜绝
彻底解决
绝对安全
确保 100% 正确
```

改为可验证描述：

```text
避免每 tick 重建区块渲染
由客户端烟测验证纹理加载
降低该类存档错误风险
以当前依赖源码和门禁输出为准
```

原因：宣传式绝对表述既占篇幅，也容易把示例实现包装成唯一正确方案。工具包历史上已经发生过规则绝对化导致错误的事故。

### 6.6 控制事故登记表增长

建议：

- `anti_patterns.md` 只保留已提炼的稳定规则；
- 完整事故历史迁移至单独的 `incident_history.md`；
- 主文档只保留最近若干条和历史链接。

原因：事故历史有治理价值，但不需要进入每一次反模式专题读取的上下文。

## 7. 不建议实施的改动

以下改动缺乏真实收益，或会降低工具包质量：

1. 不压缩 `major-feature-v2.schema.json`。Schema 是后台校验资产，不是日常固定上下文，压缩会削弱合同精度。
2. 不拆分完整的 Menu、Screen、BE 集成教程链路。只需继续保持内容归位和主题内聚。
3. 不在 SKILL.md 导航表写易漂移的精确行号范围。
4. 不新增 `.encoding` 标识文件，AI 客户端不会可靠读取该文件决定编码。
5. 不把 Token 成本或配额管理写进工具包规则。
6. 不把客户端特定的多 Agent 指令写成 NeoForge 通用规则。
7. 不把 javac 汇总 deprecation Note 当作精确数量。

## 8. 推荐实施顺序

1. 为 `asset_gate.py` 增加旧式复数纹理路径检查和测试。
2. 修正元数据真源路径描述。
3. 在移植 SOP 与资源专题中补充旧路径迁移规则。
4. 在质量线中增加客户端烟测，后续实现 `--with-client`。
5. 删除 SOP 中默认 Git Commit 指令。
6. 明确迭代门禁与阶段收口门禁。
7. 将移植脚手架设计为审计文档，继续复用 Major 合同。
8. 实现精确 EventBus 版本检查。
9. 完善 deprecation 诊断。
10. 最后进行 SKILL 去重、占位警告集中、宣传措辞清理和事故历史归档。

## 9. 验证建议

文档修改后执行：

```powershell
python .agents/run.py .agents/gates/check_doc_index.py
python .agents/run.py .agents/gates/check_doc_meta.py
```

门禁修改后执行：

```powershell
python .agents/run.py -m unittest discover -s .agents/gates -p "test_*.py"
python .agents/run.py .agents/gates/pipeline.py --profile fast
```

资源门禁至少增加以下回归夹具：

1. 旧式 `textures/blocks/` 目录；
2. 旧式 `textures/items/` 目录；
3. 模型引用 `<modid>:blocks/example`；
4. 模型引用 `<modid>:items/example`；
5. 正确的 `textures/block/` 和 `textures/item/` 不误报；
6. NeoForge 21.1.180 的 `Bus.MOD` 不误报；
7. NeoForge 21.1.181+ 的冗余 `Bus.MOD` 正确提示。

## 10. 最终判断

这次真实移植没有证明工具包需要大规模裁剪文档。它证明的是：

- 资源静态门禁与真实客户端加载之间存在盲区；
- 元数据真源规则需要更精确；
- 移植需要轻量语义审计模板，但不需要第二套合同系统；
- 部分 Git、编码和多 Agent 工作流内容位于错误的规则层级；
- 文档应减少绝对化措辞，并继续依赖源码和门禁给出完成证据。

因此，最佳改进路径不是“先缩短文档”，而是“先让门禁拦住真实错误，再清理错误层级和低价值重复”。
