# NeoForge 1.21.1 全局掉落修改器 (Global Loot Modifiers) 开发指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


当您需要向原版地牢宝箱添加战利品，或者让原版怪物/方块掉落模组自定义物品时，直接覆写原版掉落表 JSON 会与其它模组发生毁灭性的覆盖冲突。

NeoForge 提供了非侵入式的**全局掉落修改器（Global Loot Modifiers，简称 GLM）**机制。它允许我们在不破坏原版文件的提前下，在游戏运行时动态把物品塞入任何掉落表中，实现完美的多模组兼容。

---

## 1. 创建自定义 LootModifier 类

自定义掉落修改器需要继承 `LootModifier`，并通过 `RecordCodecBuilder` 配合 `LootModifier.codecStart` 定义 MapCodec 序列化逻辑，这能让您在数据 JSON 中动态配置掉落物和几率：

```java
package com.tutorial.tutorialmod.loot;

import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.neoforged.neoforge.common.loot.IGlobalLootModifier;
import net.neoforged.neoforge.common.loot.LootModifier;

public class AddItemLootModifier extends LootModifier {
    
    // 1. 使用 RecordCodecBuilder 定义 MapCodec
    // 使用 codecStart(inst) 会自动序列化和处理 JSON 中的 "conditions" (触发条件数组)
    public static final MapCodec<AddItemLootModifier> CODEC = RecordCodecBuilder.mapCodec(inst ->
            codecStart(inst).and(
                    BuiltInRegistries.ITEM.byNameCodec().fieldOf("item").forGetter(m -> m.item),
                    com.mojang.serialization.Codec.FLOAT.fieldOf("chance").forGetter(m -> m.chance) // 假设可配置掉落几率
            ).apply(inst, AddItemLootModifier::new)
    );

    private final Item item;
    private final float chance;

    public AddItemLootModifier(LootItemCondition[] conditions, Item item, float chance) {
        super(conditions);
        this.item = item;
        this.chance = chance;
    }

    // 2. 编写修改掉落物的核心逻辑
    @Override
    protected ObjectArrayList<ItemStack> doApply(ObjectArrayList<ItemStack> generatedLoot, LootParams context) {
        // 条件判断已在底层自动处理，此处只需编写概率并追加物品
        if (context.getRandom().nextFloat() <= this.chance) {
            generatedLoot.add(new ItemStack(this.item));
        }
        return generatedLoot;
    }

    @Override
    public MapCodec<? extends IGlobalLootModifier> codec() {
        return CODEC;
    }
}
```

---

## 2. 注册 LootModifier 序列化器

必须将该序列化器注册到 `NeoForgeRegistries.Keys.GLOBAL_LOOT_MODIFIER_SERIALIZERS` 中：

```java
package com.tutorial.tutorialmod.loot;

import com.mojang.serialization.MapCodec;
import com.tutorial.tutorialmod.TutorialMod;
import net.neoforged.neoforge.common.loot.IGlobalLootModifier;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

public class ModLootModifiers {
    public static final DeferredRegister<MapCodec<? extends IGlobalLootModifier>> LOOT_MODIFIERS =
            DeferredRegister.create(NeoForgeRegistries.Keys.GLOBAL_LOOT_MODIFIER_SERIALIZERS, TutorialMod.MODID);

    // 注册我们编写的 AddItemLootModifier
    public static final DeferredHolder<MapCodec<? extends IGlobalLootModifier>, MapCodec<AddItemLootModifier>> ADD_ITEM =
            LOOT_MODIFIERS.register("add_item", () -> AddItemLootModifier.CODEC);
}
```
*切记在主类构造器中调用注册总线：*
`ModLootModifiers.LOOT_MODIFIERS.register(modEventBus);`

---

## 3. 在磁盘中配置数据 JSON

注册完毕后，需要在数据包中通过两个 JSON 文件来激活和配置修改器：

### 3.1 激活入口主配置 (`global_loot_modifiers.json`)
此文件用来宣告有哪些全局修改器在当前存档中生效（NeoForge 会自动扫描并合并所有模组的该配置文件）：
*   **文件路径**：`src/main/resources/data/neoforge/loot_modifiers/global_loot_modifiers.json` (注意：命名空间必须是 **`neoforge`**，不能是 `tutorialmod`！)

```json
{
  "replace": false,
  "entries": [
    "tutorialmod:add_wand_to_dungeon"
  ]
}
```

### 3.2 编写修改器参数与触发条件
在这里配置我们的修改器行为（指定具体要添加什么物品，以及在什么条件下才触发）：
*   **文件路径**：`src/main/resources/data/tutorialmod/loot_modifiers/add_wand_to_dungeon.json`

```json
{
  "type": "tutorialmod:add_item",
  "conditions": [
    {
      "condition": "minecraft:loot_table_id",
      "loot_table": "minecraft:chests/simple_dungeon"
    }
  ],
  "item": "tutorialmod:ruby_wand",
  "chance": 0.35
}
```

### 💡 常见触发条件模板
*   **仅在破坏特定方块时追加掉落**（例如破坏原版铁矿石有概率掉落模组物品）：
    ```json
    {
      "condition": "minecraft:block_state_property",
      "block": "minecraft:iron_ore"
    }
    ```
*   **仅在击杀特定实体时追加掉落**（例如击杀僵尸有概率掉落）：
    ```json
    {
      "condition": "minecraft:entity_properties",
      "entity": "this",
      "predicate": {
        "type": "minecraft:zombie"
      }
    }
    ```
通过全局掉落修改器，我们的模组可以以最温和、安全的方式全面融入 Minecraft 的生态体系中，彻底规避了卡开服和掉落失效的售后兼容问题。