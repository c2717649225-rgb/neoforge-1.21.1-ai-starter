# Minecraft 1.21.1 进度系统与数据生成 (Advancements DataGen) 参考指南

在 Minecraft 1.21.1 中，进度（Advancement）的底层数据完全走向了数据驱动，并使用全新的 `AdvancementHolder` 代替了旧版的纯 Advancement 容器。
所有的进度数据必须通过 `AdvancementProvider` 配合 `AdvancementSubProvider` 自动生成为 JSON。

---

## 1. 编写进度生成器类 (ModAdvancementGenerator)

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.advancements.*;
import net.minecraft.advancements.critereon.InventoryChangeTrigger;
import net.minecraft.core.HolderLookup;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.common.data.AdvancementSubProvider;
import net.neoforged.neoforge.common.data.ExistingFileHelper;

import java.util.function.Consumer;

public class ModAdvancementGenerator implements AdvancementSubProvider {

    @Override
    public void generate(HolderLookup.Provider registries, Consumer<AdvancementHolder> saver, ExistingFileHelper existingFileHelper) {
        // 1. 创建根进度 (Root Advancement)
        AdvancementHolder rootAdvancement = Advancement.Builder.advancement()
                // 进度显示设置：图标、标题、描述、背景贴图、进度类型、是否在聊天栏播报、是否隐藏等
                .display(
                        new ItemStack(ModItems.RUBY.get()), // 图标 (必须是 ItemLike 或者是 ItemStack)
                        Component.translatable("advancements.tutorialmod.root.title"), // 标题
                        Component.translatable("advancements.tutorialmod.root.description"), // 描述
                        ResourceLocation.withDefaultNamespace("textures/block/stone.png"), // 背景图 (仅根进度需要)
                        AdvancementType.TASK, // 类型 (TASK, CHALLENGE, GOAL)
                        true,  // showToast (弹窗)
                        true,  // announceToChat (聊天栏通知)
                        false  // hidden (是否隐藏)
                )
                // 触发条件：这里使用立即触发 (进入游戏立刻解锁)
                .addCriterion("immediate", TriggerInstance.EMPTY)
                .save(saver, ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "root"));

        // 2. 创建子进度 (Child Advancement)
        AdvancementHolder rubyPickaxeAdvancement = Advancement.Builder.advancement()
                // 设置父节点，完成继承
                .parent(rootAdvancement)
                .display(
                        new ItemStack(ModItems.RUBY_PICKAXE.get()),
                        Component.translatable("advancements.tutorialmod.ruby_pickaxe.title"),
                        Component.translatable("advancements.tutorialmod.ruby_pickaxe.description"),
                        null,
                        AdvancementType.TASK,
                        true,
                        true,
                        false
                )
                // 触发条件：当玩家背包中拥有红宝石稿时解锁
                .addCriterion("has_ruby_pickaxe", InventoryChangeTrigger.TriggerInstance.hasItems(ModItems.RUBY_PICKAXE.get()))
                .save(saver, ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_pickaxe"));
    }
}
```

---

## 2. 在 DataGenerators 中注册 AdvancementProvider

在 `DataGenerators.gatherData` 中完成绑定：

```java
    // 在 gatherData 方法中：
    generator.addProvider(event.includeServer(), new AdvancementProvider(
            packOutput, 
            lookupProvider, 
            existingFileHelper, 
            List.of(new ModAdvancementGenerator()) // 传入进度子提供者实例
    ));
```

---

## ⚠️ 1.21.1 进度 DataGen 常见编译错误与自愈

*   **编译报错**：`method generate(HolderLookup.Provider,Consumer,ExistingFileHelper) is protected in ...`
    *   ❌ 错误：在实现 `AdvancementSubProvider` 时，重写 `generate` 方法的访问修饰符标记为 `protected` 或省略（即 package-private）。
    *   ✅ 修正：在 1.21.1 中，接口 `AdvancementSubProvider` 声明的 `generate` 方法必须是 **`public`** 访问权限。在子类覆写时**必须显式添加 `public` 关键字**，否则会报访问修饰符降级编译错误。
*   **编译报错**：`cannot find symbol: method display(EntityType,Component,...)`
    *   ❌ 错误：在 `.display(...)` 中使用 `EntityType` 或 `Block` 裸对象作为第一个图标参数。
    *   ✅ 修正：`Advancement.Builder.display` 接口在 1.21.1 中，第一参数图标对象**绝对不支持 `EntityType` 等非物品类型**。必须包装为 `ItemLike`（如 `Items.DIAMOND`、`Blocks.DIRT`）或者是 `ItemStack` 实例传入。
*   **运行时崩溃**：`IllegalArgumentException (Parent advancement ... is not registered)`
    *   ❌ 错误：子进度的 `.parent(...)` 中传入了未经保存或尚未初始化的其他进度 Holder 引用。
    *   ✅ 修正：父进度必须在子进度保存前，已经被调用 `.save(saver, ...)` 注册。且调用 `parent` 时必须传入已保存后返回的 `AdvancementHolder` 实例。
