# 模组通用架构设计蓝图 (Architecture & Design Blueprint)

> 本文档用于定义项目的高维架构和代码设计原则。当需要进行模块重构、代理设计或结构性调整时，开发人员或 AI 应当主动读取本文档。

---

## 📐 1. 核心设计原则 (Minecraft SOLID Guidelines)

1. **单一职责原则 (SRP)**：
   * `Block` 类仅负责方块物理定义，复杂状态与 Tick 逻辑必须交由 `BlockEntity` 处理。
   * 模型的注册与渲染逻辑必须与方块类完全剥离，交由 `BlockStateProvider` 与 `BlockEntityRenderer` 处理。
2. **开闭原则 (OCP)**：
   * 注册配方、世界生成、注册项扩展，必须监听平台提供的特定事件（如监听 `CreativeModeTabEvent`）或使用数据包（Biome Modifier），严禁直接使用 Mixin 强行修改底层核心类。
3. **接口隔离原则 (ISP)**：
   * 机器实体不得直接实现物品栏或流体处理接口。必须内部持有 `ItemStackHandler` / `FluidTank` 等封装实例，并在注册能力（Capabilities）时，按需向特定的面（Direction）暴露。
4. **迪米特法则 (LoD)**：
   * 方块实体需要与邻近方块交互时（如从旁边箱子抽取物品），必须通过 `level.getCapability(...)` 查询能力接口，严禁直接强转邻近方块实体类型并调用其私有方法。

---

## 🌐 2. 跨平台移植与解耦架构 (Portability & Decoupling)

为了确保核心业务逻辑能无缝移植到 Fabric，项目建议采用**平台代理包装层（Platform Delegation Layer）**架构：

1. **业务逻辑与平台接口分离**：
   * 将核心逻辑（如物品交互、状态计算、实体 AI 属性决策）剥离至纯 Java 逻辑层。
   * 平台独有逻辑（如 NeoForge 的事件注册、能力系统、特有网络发包）完全封装在平台独立的适配层。
2. **使用 IPlatformHelper 模式**：
   * 建立通用的业务依赖接口（例如 `IPlatformHelper`），定义注册、发包、能力查询等方法。
   * 在运行时，通过服务加载器（ServiceLoader）或依赖注入动态注入当前平台的具体实现。

---

## ⚡ 3. 性能、异常与线程安全准则

1. **高频 Tick 严禁高开销操作**：
   * 所有的 `tick()` 方法中，绝对禁止进行任何 I/O 读写、高开销容器遍历（如每次 tick 遍历世界实体）以及高频垃圾对象分配。
   * 对于大型遍历或寻路，必须引入时间步长（Tick Cooldown）进行节流（Throttling）。
2. **并发线程安全**：
   * 多线程或异步场景下，优先使用 `ConcurrentHashMap`、`AtomicInteger`、`CopyOnWriteArrayList`。
3. **崩溃防御**：
   * 所有内部异常必须被捕获并优雅降级（如打印日志、安全移除实体），绝对禁止导致整个游戏物理客户端或服务端发生崩溃。
