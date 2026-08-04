---
status: verified
pin_minecraft: 1.21.1
pin_neo: 21.1.x
last_verified: 2026-08-02
---
# NeoForge 1.21.1 客户端数据同步与渲染避坑指南 (Client Data Sync & Rendering)

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。

---

## 1. BlockEntity 数据同步：`sendBlockUpdated` 逻辑与阻断坑

### 现象与原理
在 1.21.1 中，当方块实体（BlockEntity）的内部数据变化（如能量变化、槽位变更、工作状态变化）需要同步给客户端时，调用 `level.sendBlockUpdated(pos, oldState, newState, flags)` 是常规手段。
**关键陷阱**：如果旧的 `oldState` 与新的 `newState` 属于同一个 `BlockState`（即方块属性如 `FACING`、`LIT` 没有改变），原版 `Level.sendBlockUpdated` 会内部判断状态未变而**自动阻断** `ClientboundBlockEntityDataPacket` 的组装与发送！

### 正确写法
- **方案 A（广播原生更新包）**：通过 `ServerLevel` 直接给维度内的追踪玩家广播网络包。
  ```java
  public void syncToClient(ServerLevel level) {
      this.setChanged();
      ClientboundBlockEntityDataPacket packet = ClientboundBlockEntityDataPacket.create(this);
      level.getServer().getPlayerList().broadcastAll(packet, level.dimension());
  }
  ```
- **方案 B（使用自定义 Payload 网络包）**：对于高频数据更新，推荐使用 `CustomPacketPayload` + `PacketDistributor` 发送。

### 错误反例
```java
// ❌ 错误：oldState 与 newState 完全相同时，原版 Level 会阻断 BE 数据包发送，客户端数据永远不会更新！
level.sendBlockUpdated(worldPosition, getBlockState(), getBlockState(), Block.UPDATE_ALL);
```

---

## 2. 客户端处理 BE 更新包：`loadAdditional` 必须成对读写

### 现象与原理
在 1.21.1 中，NeoForge 与原版重构了 `ClientboundBlockEntityDataPacket` 的反序列化流程：
客户端收到包后走 `loadWithComponents` ➔ 内部顺次调用 `loadAdditional(tag, registries)`。**旧版本中的 `handleUpdateTag` 已经不会再被默认同步逻辑自动调用**！

### 正确写法
`saveAdditional` 与 `loadAdditional` 必须成对读写所有需要客户端渲染与状态所需的 NBT/Data Component 字段：

```java
@Override
protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
    super.saveAdditional(tag, registries);
    tag.putInt("Energy", this.energyStorage.getEnergyStored());
    tag.putString("CustomName", this.customName);
}

@Override
protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
    super.loadAdditional(tag, registries);
    this.energyStorage.setEnergy(tag.getInt("Energy"));
    this.customName = tag.getString("CustomName");
}

@Override
public CompoundTag getUpdateTag(HolderLookup.Provider registries) {
    CompoundTag tag = new CompoundTag();
    saveAdditional(tag, registries);
    return tag;
}

@Override
public Packet<ClientGamePacketListener> getUpdatePacket() {
    return ClientboundBlockEntityDataPacket.create(this);
}
```

### 错误反例
```java
// ❌ 错误：在 handleUpdateTag 里写客户端读取逻辑。1.21.1 默认走 loadAdditional，导致客户端只跑 saveAdditional/loadAdditional，客户端读取为空！
@Override
public void handleUpdateTag(CompoundTag tag, HolderLookup.Provider registries) {
    // 在 1.21.1 中此方法默认不会被网络包解包自动调用！
    this.energyStorage.setEnergy(tag.getInt("Energy"));
}
```

---

## 3. `PacketDistributor` 与原版网络包分流

### 现象与原理
NeoForge 1.21.1 的 `PacketDistributor` 泛型强化为只接收 `CustomPacketPayload` 接口。**直接将原版 `Packet<?>`（如 `ClientboundBlockEntityDataPacket`）传入 `PacketDistributor` 会引发类型不匹配或编译报错**。

### 正确写法
- **原版 Packet<?>**：使用 `PlayerList` 或 `ServerPlayer.connection.send(...)`：
  ```java
  // 原版包发给全维度追踪玩家
  serverLevel.getServer().getPlayerList().broadcastAll(packet, serverLevel.dimension());
  ```
- **NeoForge CustomPacketPayload**：注册 Payload 后使用 `PacketDistributor`：
  ```java
  // 自定义 Payload
  PacketDistributor.sendToPlayersTrackingChunk(serverLevel, new ChunkPos(pos), myPayload);
  ```

---

## 4. `RenderType.LINES` 顶点格式与 Sodium / Iris 兼容性

### 现象与原理
原版/NeoForge 1.21.1 中 `RenderType.lines()` / `LINES` 的顶点格式为 `DefaultVertexFormat.POSITION_COLOR_NORMAL`。
如果使用 `VertexConsumer` 绘制线段（如视线、射线、方块边框）时漏掉了 `.setNormal(...)`，顶点构建器的内存 Buffer 步进会发生错位。在安装了 **Sodium / Iris** 等显卡优化模组的环境下，VBO 上传阶段会抛出 `BufferOverflowException` 或直接导致游戏崩溃。

### 正确写法
```java
VertexConsumer buffer = bufferSource.getBuffer(RenderType.lines());

// 必须严格按 POSITION -> COLOR -> NORMAL 顺序构建顶点
buffer.addVertex(poseStack.last().pose(), x1, y1, z1)
      .setColor(255, 0, 0, 255)
      .setNormal(poseStack.last(), nx, ny, nz); // ⚠️ 绝不能漏掉 setNormal！

buffer.addVertex(poseStack.last().pose(), x2, y2, z2)
      .setColor(255, 0, 0, 255)
      .setNormal(poseStack.last(), nx, ny, nz);
```

### 错误反例
```java
// ❌ 错误：缺 setNormal！在 Vanilla 下可能静默丢帧，在 Sodium/Iris 渲染优化下直接崩溃！
buffer.addVertex(poseStack.last().pose(), x1, y1, z1)
      .setColor(255, 0, 0, 255); // 缺 .setNormal()
```

---

## 5. `RenderLevelStageEvent` 中 `MultiBufferSource` 手动 `endBatch()`

### 现象与原理
在监听 `RenderLevelStageEvent` 进行世界空间自定义渲染（如激光、光束、粒子线段）时，通常从 `event.getLevelRenderer().renderBuffers().bufferSource()` 获取 `BufferSource`。
由于 `RenderLevelStageEvent` 在全局渲染流程中间触发，如果渲染完毕后未显式调用 `bufferSource.endBatch(renderType)`，顶点数据会留在内存 Buffer 中，被后续其他 RenderType 覆盖或混刷乱序。

### 正确写法
```java
@SubscribeEvent
public static void onRenderLevelStage(RenderLevelStageEvent event) {
    if (event.getStage() == RenderLevelStageEvent.Stage.AFTER_PARTICLES) {
        MultiBufferSource.BufferSource bufferSource = Minecraft.getInstance().renderBuffers().bufferSource();
        RenderType myRenderType = RenderType.lines();
        VertexConsumer buffer = bufferSource.getBuffer(myRenderType);

        // ... 绘制顶点 ...

        // ⚠️ 必须显式 endBatch，确保顶点在当前 Stage 立即提交 GPU 渲染
        bufferSource.endBatch(myRenderType);
    }
}
```

---

## 6. 服务端右键交互优先级与抢占

### 现象与原理
1.21.1 中玩家右键方块时的服务端方法调用顺序为：
1. `BlockBehaviour.useItemOn`（手上持有物品右键方块）
2. `BlockBehaviour.useWithoutItem`（空手或手上物品无法在方块上使用）
3. `Item.useOn`（物品自身的右键方块逻辑）

**关键行为**：如果方块的 `useItemOn` 返回了 `ItemInteractionResult.SUCCESS` 或 `CONSUME`，物品的 `Item.useOn` 逻辑将被彻底抢占拦截。若希望让物品优先处理（如特定工具、板手、能量测量仪），方块交互必须返回 `ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION`。

### 正确写法
```java
@Override
protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {
    if (stack.is(MyItems.SPECIAL_WRENCH.get())) {
        // 允许物品自身 useOn 优先处理
        return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }
    // 处理方块自己的物品右键逻辑
    return ItemInteractionResult.SUCCESS;
}
```
