# Minecraft 1.21.1 药水效果、注册与酿造 (Potions & Brewing Recipes) 参考指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


在 Minecraft 1.21.1 中，药水注册以及酿造配方系统全面接入了现代的数据组件化，并废除了以前的大量硬编码工具类：
- **废除 PotionUtils**：所有的药水信息提取不再通过 `PotionUtils`，改由 `DataComponents.POTION_CONTENTS` 配合数据组件 `PotionContents` 存取。
- **酿造配方事件总线现代化**：酿造配方的添加改在 `RegisterBrewingRecipesEvent` 事件中，通过其提供的 `PotionBrewing.Builder` 完成。

---

## 1. 注册自定义 MobEffect (药水效果) 与 Potion (药水)

```java
package com.tutorial.tutorialmod.potion;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectCategory;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.item.alchemy.Potion;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModPotions {
    public static final DeferredRegister<MobEffect> MOB_EFFECTS = DeferredRegister.create(Registries.MOB_EFFECT, TutorialMod.MODID);
    public static final DeferredRegister<Potion> POTIONS = DeferredRegister.create(Registries.POTION, TutorialMod.MODID);

    // 1. 注册状态效果（MobEffect，1.21 前称为 Potion）
    public static final DeferredHolder<MobEffect, MobEffect> FLIGHT_EFFECT = MOB_EFFECTS.register("flight",
            () -> new MobEffect(MobEffectCategory.BENEFICIAL, 0x7CAFC6) // 增益效果，颜色值
    );

    // 2. 注册对应的药水类型 (Potion)，封装一个或多个 MobEffectInstance 效果实例
    public static final DeferredHolder<Potion, Potion> FLIGHT_POTION = POTIONS.register("flight",
            () -> new Potion(new MobEffectInstance(FLIGHT_EFFECT, 3600, 0))) // 3600 tick = 3 分钟，I 级
    );

    public static void register(IEventBus modBus) {
        MOB_EFFECTS.register(modBus);
        POTIONS.register(modBus);
    }
}
```

---

## 2. 注册酿造配方 (RegisterBrewingRecipesEvent)

配方注册必须在 **GAME 总线**（对应 Forge 游戏事件总线）的 `RegisterBrewingRecipesEvent` 中使用：

```java
package com.tutorial.tutorialmod.event;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.potion.ModPotions;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.alchemy.PotionBrewing;
import net.minecraft.world.item.alchemy.Potions;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.brewing.RegisterBrewingRecipesEvent;

@EventBusSubscriber(modid = TutorialMod.MODID) // 默认挂在 NeoForge 游戏总线上
public class BrewingRecipeHandler {

    @SubscribeEvent
    public static void registerBrewing(RegisterBrewingRecipesEvent event) {
        PotionBrewing.Builder builder = event.getBuilder();

        // 粗制的药水 + 羽毛 = 飞行药水
        builder.addMix(
                Potions.AWKWARD,           // 基础药水 (Holder<Potion>)
                Items.FEATHER,             // 酿造材料 (Item)
                ModPotions.FLIGHT_POTION   // 结果药水 (Holder<Potion>)
        );
    }
}
```

---

## 3. 读取和修改物品的药水信息 (PotionContents Component)

1.21.1 彻底抛弃了 `PotionUtils.getPotion(stack)` 这种 NBT 裸解析，完全使用类型安全的数据组件组件机制：

```java
import net.minecraft.core.component.DataComponents;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.alchemy.PotionContents;
import net.minecraft.world.effect.MobEffectInstance;

public class PotionContentsExample {

    public static void handlePotionStack(ItemStack stack) {
        // 1. 读取药水内容组件 (可能返回 null)
        PotionContents contents = stack.get(DataComponents.POTION_CONTENTS);
        if (contents != null) {
            // 遍历药水包含的所有状态效果实例
            for (MobEffectInstance effect : contents.getAllEffects()) {
                MobEffect category = effect.getEffect().value();
                int duration = effect.getDuration();
                int amplifier = effect.getAmplifier();
            }
        }

        // 2. 修改/写入药水数据
        stack.set(DataComponents.POTION_CONTENTS, new PotionContents(ModPotions.FLIGHT_POTION));
    }
}
```

---

## ⚠️ 1.21.1 药水与特定工具高频编译错误防御与自愈

*   **编译报错**：`cannot find symbol: class PotionUtils location: package net.minecraft.world.item.alchemy`
    *   ❌ 错误：试图通过 `PotionUtils.getPotion(stack)` 或 `PotionUtils.getMobEffects(stack)` 解析数据。
    *   ✅ 修正：1.21.1 中 `PotionUtils` 已经被删除。药水读写一律通过 `stack.get(DataComponents.POTION_CONTENTS)` 并调用返回对象 `PotionContents` 的方法。
*   **编译报错**：`cannot find symbol: class PotionItem location: package net.minecraft.world.item.alchemy`
    *   ❌ 错误：`import net.minecraft.world.item.alchemy.PotionItem;`。
    *   ✅ 修正：`PotionItem` 处于 `net.minecraft.world.item.PotionItem`，不在 alchemy 子包下。
*   **编译报错**：`method does not override or implement a method from a supertype` (在覆写 `getUseDuration` 时)
    *   ❌ 错误：使用旧版本单参覆写 `public int getUseDuration(ItemStack stack) { ... }`。
    *   ✅ 修正：在 1.21.1 中，食物、药水及一切可使用物品的 `getUseDuration` 方法均已变更为双参数签名：
        ```java
        @Override
        public int getUseDuration(ItemStack stack, net.minecraft.world.entity.LivingEntity entity) {
            return 32;
        }
        ```
*   **编译报错**：`constructor DiggerItem cannot be applied to given types; required: Tier,TagKey<Block>,Properties; found: Tier,TagKey<Block>,float,float,Properties`
    *   ❌ 错误：编写工具类（如 `PickaxeItem` 或自定义 Digger 子类）时，在 `super(...)` 构造器中传入攻击力基准和攻击速度参数。
    *   ✅ 修正：1.21.1 的工具构造器不再接收伤害和速度数值参数。工具的伤害属性必须通过 attributes 属性构建，使用 `properties.attributes(DiggerItem.createAttributes(tier, attackDamage, attackSpeed))` 传入。