# Minecraft 1.21.1 世界全局数据存储 (SavedData) 参考指南

在 Minecraft NeoForge 模组开发中，如果需要存储跨维度、全局性、服务器级别的持久化数据（如全局经济系统、任务系统、队伍管理），不适合附加到单个实体或区块上，应当使用 **`SavedData`** 存储机制。

---

## 1. 定义 SavedData 存储类

`SavedData` 只能在**服务端**使用，其底层是通过读写 NBT（`CompoundTag`）实现持久化的。每次修改数据后都必须标记为脏以保存：

```java
package com.tutorial.tutorialmod.data;

import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraft.world.level.storage.DimensionDataStorage;

public class GlobalQuestData extends SavedData {

    private int completedQuestsCount = 0;

    // 私有构造函数，只允许通过工厂加载或实例化
    private GlobalQuestData() {}

    // 1. 创建新数据的工厂方法
    public static GlobalQuestData create() {
        return new GlobalQuestData();
    }

    // 2. 从 NBT 恢复数据的工厂方法
    public static GlobalQuestData load(CompoundTag tag, HolderLookup.Provider lookupProvider) {
        GlobalQuestData data = new GlobalQuestData();
        data.completedQuestsCount = tag.getInt("CompletedQuestsCount");
        return data;
    }

    // 3. 写入数据到 NBT 存档中 (必须传入 Provider 作为第二个参数)
    @Override
    public CompoundTag save(CompoundTag tag, HolderLookup.Provider registries) {
        tag.putInt("CompletedQuestsCount", this.completedQuestsCount);
        return tag;
    }

    // 4. 定义 SavedData 工厂类 (Factory) 供 DimensionDataStorage 调度
    private static final Factory<GlobalQuestData> FACTORY = new Factory<>(
            GlobalQuestData::create,
            GlobalQuestData::load
    );

    // 5. 跨维度共享：静态获取方法，一般建议存储在主世界 (Overworld)
    public static GlobalQuestData get(MinecraftServer server) {
        DimensionDataStorage storage = server.overworld().getDataStorage();
        // 如果数据已存在则读取，如果不存在则自动使用 FACTORY 的 create() 创建
        GlobalQuestData data = storage.computeIfAbsent(FACTORY, "tutorialmod_quest_data");
        return data;
    }

    // === 业务逻辑方法 ===
    
    public int getCompletedQuestsCount() {
        return this.completedQuestsCount;
    }

    public void incrementQuests() {
        this.completedQuestsCount++;
        // 关键：修改数据后必须标记为脏，否则游戏存盘时不会写回磁盘文件
        this.setDirty();
    }
}
```

---

## 2. 在业务代码中使用 SavedData

```java
// 在服务端逻辑（如玩家完成任务的事件监听中）
MinecraftServer server = level.getServer();
if (server != null) {
    GlobalQuestData questData = GlobalQuestData.get(server);
    questData.incrementQuests();
    
    player.sendSystemMessage(Component.literal("全服已累计完成任务数: " + questData.getCompletedQuestsCount()));
}
```

---

## ⚠️ 1.21.1 SavedData 常见编译错误防御与自愈

*   **编译报错**：`QuestData is not abstract and does not override abstract method save(CompoundTag,Provider) in SavedData`
    *   ❌ 错误：在重写 `save` 时未引入 `HolderLookup.Provider`，仍然使用旧版本 1.20 的 `public CompoundTag save(CompoundTag tag)` 单参数签名。
    *   ✅ 修正：在 1.21.1 中，`save` 方法必须是双参签名：
        ```java
        @Override
        public CompoundTag save(CompoundTag tag, net.minecraft.core.HolderLookup.Provider registries) { ... }
        ```
        且必须保证类头部正确导入了 `net.minecraft.core.HolderLookup` 依赖。
*   **编译报错**：`method writeBlockPos in class NbtUtils cannot be applied to given types; required: BlockPos found: BlockPos,CompoundTag,String`
    *   ❌ 错误：在序列化 BlockPos 时，使用旧版 `NbtUtils.writeBlockPos(pos, tag, key)`。
    *   ✅ 修正：在 1.21.1 中，`NbtUtils.writeBlockPos(BlockPos)` 只接收一个参数并直接返回代表位置的 Tag 实例。我们需要将其手动 `put` 写入 `CompoundTag`：
        ```java
        tag.put("pos", NbtUtils.writeBlockPos(pos));
        ```
*   **编译报错**：`storageSource has protected access in MinecraftServer`
    *   ❌ 错误：试图通过 `server.storageSource.getLevelId()` 来为 SavedData 创建与世界存档名字相关的动态键名。
    *   ✅ 修正：`storageSource` 是受保护的，外部无法访问。要获取当前存档世界的名称，必须使用 `server.getWorldData().getLevelName()`。
