# Minecraft 1.21.1 数据驱动附魔 (Custom Enchantments DataGen) 参考指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


在 Minecraft 1.21 及更高版本中，附魔系统经历了颠覆性的重构：
- **彻底废除硬编码类**：`Enchantment` 被改为 Java `record`（隐式为 final），不可再被继承。
- **完全由数据包 (Data Pack) 驱动**：附魔的定义不再通过传统的 `DeferredRegister` 在运行时注册，而是必须在 DataGen 阶段使用 `RegistrySetBuilder` 生成 JSON 文件并打包进游戏数据中。
- **使用组件定义行为**：附魔的具体效果（如增加伤害、护甲减免、攻击后触发效果等）全部由 `DataComponentMap` 定义。

---

## 1. 定义附魔 ResourceKey

附魔的唯一标识符使用 `ResourceKey<Enchantment>` 表示：

```java
package com.tutorial.tutorialmod.init;

import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.enchantment.Enchantment;

public class ModEnchantments {
    public static final String MOD_ID = "tutorialmod";

    // 自定义附魔 Key
    public static final ResourceKey<Enchantment> THUNDER_STRIKE = key("thunder_strike");

    private static ResourceKey<Enchantment> key(String name) {
        return ResourceKey.create(Registries.ENCHANTMENT,
                ResourceLocation.fromNamespaceAndPath(MOD_ID, name));
    }
}
```

---

## 2. 编写附魔 DataGen 引导类 (`DatapackBuiltinEntriesProvider`)

因为附魔是动态注册表（Registry-bound）的成员，必须使用 `DatapackBuiltinEntriesProvider` 并在其 `RegistrySetBuilder` 中引导：

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.init.ModEnchantments;
import net.minecraft.core.HolderGetter;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.HolderSet;
import net.minecraft.core.RegistrySetBuilder;
import net.minecraft.core.component.DataComponentMap;
import net.minecraft.core.registries.Registries;
import net.minecraft.data.DataGenerator;
import net.minecraft.data.PackOutput;
import net.minecraft.data.worldgen.BootstrapContext;
import net.minecraft.network.chat.Component;
import net.minecraft.tags.EnchantmentTags;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.enchantment.Enchantment;
import net.neoforged.neoforge.common.data.DatapackBuiltinEntriesProvider;
import net.neoforged.neoforge.common.data.ExistingFileHelper;
import net.neoforged.neoforge.data.event.GatherDataEvent;

import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CompletableFuture;

public class ModDataGen {

    public static void gatherData(GatherDataEvent event) {
        DataGenerator gen = event.getGenerator();
        PackOutput output = gen.getPackOutput();
        CompletableFuture<HolderLookup.Provider> lookupProvider = event.getLookupProvider();

        // 绑定附魔注册表到 RegistrySetBuilder
        RegistrySetBuilder builder = new RegistrySetBuilder()
                .add(Registries.ENCHANTMENT, ModDataGen::bootstrapEnchantments);

        // 使用 DatapackBuiltinEntriesProvider
        DatapackBuiltinEntriesProvider datapackProvider = new DatapackBuiltinEntriesProvider(
                output, lookupProvider, builder, Set.of(ModEnchantments.MOD_ID));
        gen.addProvider(event.includeServer(), datapackProvider);
    }

    private static void bootstrapEnchantments(BootstrapContext<Enchantment> bootstrap) {
        HolderGetter<Item> items = bootstrap.lookup(Registries.ITEM);

        // 注册闪电附魔 (Thunder Strike)
        bootstrap.register(
            ModEnchantments.THUNDER_STRIKE,
            new Enchantment(
                // 1. 本地化描述名称
                Component.translatable("enchantment.tutorialmod.thunder_strike"),
                // 2. 附魔基本定义属性
                new Enchantment.EnchantmentDefinition(
                    items.getOrThrow(ItemTags.SWORD_ENCHANTABLE), // 适用的物品类型 (TagKey)
                    Optional.empty(),                              // 附魔台主要物品 (Optional<HolderSet<Item>>)
                    5,                                             // 稀有度权重 (1-1024，越大越常见)
                    3,                                             // 最大等级 (1-255)
                    new Enchantment.Cost(10, 10),                  // 最小经验花费
                    new Enchantment.Cost(25, 10),                  // 最大经验花费
                    4,                                             // 铁砧合并花费
                    List.of(EquipmentSlotGroup.MAINHAND)           // 生效装备槽 (MAINHAND)
                ),
                // 3. 互斥附魔集 (使用 HolderSet<Enchantment>，可用 direct() 或通过 lookup 注入)
                HolderSet.empty(),
                // 4. 内置效果组件 Map (使用组件定义行为，如伤害加成、特效等)
                DataComponentMap.EMPTY
            )
        );
    }
}
```

---

## 3. 使用内置效果组件 (EnchantmentEffectComponents)

无需额外写事件监听器，1.21.1 提供了极其强大的内置组件，可直接绑定在附魔上：

```java
import net.minecraft.world.item.enchantment.ConditionalEffect;
import net.minecraft.world.item.enchantment.EnchantmentEffectComponents;
import net.minecraft.world.item.enchantment.LevelBasedValue;
import net.minecraft.world.item.enchantment.effects.AddValue;

// 在 Enchantment 构造函数的第四个参数注入效果 Map：
DataComponentMap.builder()
    // 增加伤害效果 (类似锋利)
    .set(
        EnchantmentEffectComponents.DAMAGE,
        List.of(new ConditionalEffect<>(
            new AddValue(LevelBasedValue.perLevel(2.0F, 1.0F)), // 每一级增加 2.0 + (level-1)*1.0 的伤害
            Optional.empty()                                    // 无额外环境判断条件 (Optional.empty())
        ))
    )
    .build();
```

---

## 4. 获取与读取附魔等级 (Gameplay API)

在 1.21.1 中，附魔也是 Holder 对象。通过 `EnchantmentHelper` 读取等级时：

```java
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.enchantment.EnchantmentHelper;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.core.registries.Registries;

public class EnchantmentHelperExample {

    public static int getThunderStrikeLevel(ItemStack stack, ServerLevel level) {
        return level.registryAccess()
                .registryOrThrow(Registries.ENCHANTMENT)
                .getHolder(ModEnchantments.THUNDER_STRIKE)
                .map(holder -> EnchantmentHelper.getItemEnchantmentLevel(holder, stack))
                .orElse(0);
    }
}
```

---

## ⚠️ 1.21.1 附魔 DataGen 常见编译错误防御与自愈

*   **编译报错**：`constructor EnchantmentDefinition cannot be applied to given types; required: HolderSet<Item>,Optional<HolderSet<Item>>,int,int,Cost,Cost,int,List<EquipmentSlotGroup>`
    *   ❌ 错误：在 `new Enchantment.EnchantmentDefinition(...)` 中漏传参数，或者把最后一个参数写成单个 `EquipmentSlotGroup.MAINHAND`。
    *   ✅ 修正：该构造器必须包含全部 **8 个**参数。第 2 个参数必须是 `Optional` 容器，最后一个必须是 `List` 容器。若要传递单个槽位，必须使用 `List.of(EquipmentSlotGroup.MAINHAND)`。
*   **运行时崩溃**：`UnsupportedOperationException: Tag ... can't be dereferenced during construction`
    *   ❌ 错误：在 `RegistrySetBuilder` 引导期，试图从 tag 里解析具体包含的所有物品列表并塞进 `HolderSet.direct(...)` 中。
    *   ✅ 修正：在此阶段标签还没有绑定到注册表。**绝对不能**对 `items.getOrThrow(ItemTags.SWORD_ENCHANTABLE)` 返回的 Named 标签持有器去调用 `forEach` / `contents` 解引用，必须将其直接作为 `HolderSet<Item>` 泛型传入附魔定义。
*   **编译报错**：`cannot find symbol: class EnchantmentCategory`
    *   ❌ 错误：`import net.minecraft.world.item.enchantment.EnchantmentCategory;`。
    *   ✅ 修正：1.21.1 已彻底移除附魔类别枚举。附魔支持哪些物品完全通过第一个参数的 `HolderSet<Item>` 来限定（如使用 `ItemTags.SWORD_ENCHANTABLE` 替代）。