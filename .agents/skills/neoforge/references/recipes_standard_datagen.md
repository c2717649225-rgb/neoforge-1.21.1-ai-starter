# Minecraft 1.21.1 标准合成与烹饪配方数据生成 (Recipes DataGen) 参考指南

在 Minecraft 1.21.1 中，传统的 `FinishedRecipe` 类已被完全移除，数据生成一律使用 **`RecipeOutput`** 作为输出。
所有的配方生成器必须继承 `RecipeProvider` 并重写 `buildRecipes(RecipeOutput)`。

---

## 1. 编写配方提供者类 (ModRecipeProvider)

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.PackOutput;
import net.minecraft.data.recipes.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.level.ItemLike;
import net.neoforged.neoforge.common.conditions.IConditionBuilder;

import java.util.List;
import java.util.concurrent.CompletableFuture;

public class ModRecipeProvider extends RecipeProvider implements IConditionBuilder {

    public ModRecipeProvider(PackOutput output, CompletableFuture<HolderLookup.Provider> registries) {
        super(output, registries);
    }

    @Override
    protected void buildRecipes(RecipeOutput recipeOutput) {
        // 1. 有形合成配方 (Shaped)
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, ModBlocks.RUBY_BLOCK.get())
                .pattern("RRR")
                .pattern("RRR")
                .pattern("RRR")
                .define('R', ModItems.RUBY.get())
                .unlockedBy("has_ruby", has(ModItems.RUBY.get())) // 解锁条件
                .save(recipeOutput);

        // 2. 无形合成配方 (Shapeless)
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, ModItems.RUBY.get(), 9)
                .requires(ModBlocks.RUBY_BLOCK.get())
                .unlockedBy("has_ruby_block", has(ModBlocks.RUBY_BLOCK.get()))
                .save(recipeOutput);

        // 3. 矿石批量熔炼与高炉配方 (Cooking)
        // 批量将粗红宝石和深层红宝石矿石熔炼为红宝石
        List<ItemLike> rubySmeltables = List.of(ModItems.RAW_RUBY.get(), ModBlocks.RUBY_ORE.get());
        oreSmelting(recipeOutput, rubySmeltables, RecipeCategory.MISC, ModItems.RUBY.get(), 0.7F, 200, "ruby");
        oreBlasting(recipeOutput, rubySmeltables, RecipeCategory.MISC, ModItems.RUBY.get(), 0.7F, 100, "ruby");

        // 4. 切石机配方 (Stonecutting)
        SingleItemRecipeBuilder.stonecutting(
                Ingredient.of(ModBlocks.RUBY_BLOCK.get()),
                RecipeCategory.BUILDING_BLOCKS,
                ModBlocks.RUBY_SLAB.get(), // 假设有红宝石台阶
                2                            // 产出数量
        ).unlockedBy("has_ruby_block", has(ModBlocks.RUBY_BLOCK.get()))
         .save(recipeOutput, ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_slab_from_stonecutting"));

        // 5. 锻造台升级配方 (Smithing Transform)
        SmithingTransformRecipeBuilder.smithing(
                Ingredient.of(Items.NETHERITE_UPGRADE_SMITHING_TEMPLATE), // 升级模板
                Ingredient.of(ModItems.RUBY_SWORD.get()),                 // 基础武器 (红宝石剑)
                Ingredient.of(Items.NETHERITE_INGOT),                       // 升级材料 (下界合金锭)
                RecipeCategory.COMBAT,
                ModItems.NETHERITE_RUBY_SWORD.get()                         // 产出武器
        ).unlocks("has_netherite_ingot", has(Items.NETHERITE_INGOT))
         .save(recipeOutput, ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "netherite_ruby_sword_smithing"));
    }
}
```

---

## ⚠️ 1.21.1 配方 DataGen 常见编译错误与自愈

*   **编译报错**：`no suitable method found for requires(TagKey<Item>,int)`
    *   ❌ 错误：在无形配方中为标签直接指定数量参数，如：`.requires(ItemTags.WOOL, 6)`。
    *   ✅ 修正：`ShapelessRecipeBuilder.requires` **不支持 `TagKey` 带数量**。对于需要多个标签的情况，必须使用 `Ingredient` 包裹：
        ```java
        .requires(Ingredient.of(ItemTags.WOOL), 6)
        ```
*   **编译报错**：`cannot find symbol: class FinishedRecipe`
    *   ❌ 错误：`import net.minecraft.data.recipes.FinishedRecipe;` 或在 `buildRecipes` 签名中使用它。
    *   ✅ 修正：在 1.21.1 中 `FinishedRecipe` 类已被**完全移除**。数据生成器接收并导出全部使用 **`RecipeOutput`** 替代。
*   **运行时崩溃**：`IllegalStateException (Loot/Recipe Output Count exceeds Max Stack Size)`
    *   ❌ 错误：为不可堆叠物品（如剑、工具、盔甲，其 `maxStackSize = 1`）配置了大于 1 的配方输出数量。
    *   ✅ 修正：不可堆叠物品的输出参数必须为 1，或者缺省该参数（默认为 1），否则 `runData` 时数据校验层会直接崩溃中止。
*   **运行时崩溃**：`Duplicate recipe ...`
    *   ❌ 错误：对同一个输出物品在没有手动指定 `ResourceLocation` 的情况下调用了多次 `.save(recipeOutput)`。
    *   ✅ 修正：`save(recipeOutput)` 默认使用输出物品的注册名称作为配方 JSON 的文件名。如果同一物品有多个不同的配方（如熔炉和高炉），除了第一种之外，后续必须显式传入唯一的 `ResourceLocation`：
        ```java
        .save(recipeOutput, ResourceLocation.fromNamespaceAndPath(MODID, "ruby_from_blasting"))
        ```
