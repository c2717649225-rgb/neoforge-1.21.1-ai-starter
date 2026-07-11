# NeoForge 1.21.1 Recipes & Tags Data Generation Example

This file provides code examples for automatically generating recipe and tag JSON files using NeoForge 1.21.1 data generation.

---

## 1. Recipes Generation (`RecipeProvider`)

Extend `RecipeProvider` and implement the `buildRecipes` method.

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.PackOutput;
import net.minecraft.data.recipes.*;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.Ingredient;

import java.util.List;
import java.util.concurrent.CompletableFuture;

public class ModRecipeProvider extends RecipeProvider {

    public ModRecipeProvider(PackOutput output, CompletableFuture<HolderLookup.Provider> lookupProvider) {
        super(output, lookupProvider);
    }

    @Override
    protected void buildRecipes(RecipeOutput output) {
        // 1. Shaped Recipe: 9 Raw Rubies -> 1 Ruby Block
        ShapedRecipeBuilder.shaped(RecipeCategory.BUILDING_BLOCKS, ModBlocks.RUBY_BLOCK.get())
                .pattern("###")
                .pattern("###")
                .pattern("###")
                .define('#', ModItems.RAW_RUBY.get())
                .unlockedBy("has_raw_ruby", has(ModItems.RAW_RUBY.get()))
                .save(output);

        // 2. Shapeless Recipe: 1 Ruby Block -> 9 Rubies
        ShapelessRecipeBuilder.shapeless(RecipeCategory.MISC, ModItems.RUBY.get(), 9)
                .requires(ModBlocks.RUBY_BLOCK.get())
                .unlockedBy("has_ruby_block", has(ModBlocks.RUBY_BLOCK.get()))
                .save(output);

        // 3. Smelting Recipe: Raw Ruby -> Ruby
        SimpleCookingRecipeBuilder.smelting(
                Ingredient.of(ModItems.RAW_RUBY.get()),
                RecipeCategory.MISC,
                ModItems.RUBY.get(),
                0.7F, // 经验值
                200   // 烧炼时间 (tick)
        )
        .unlockedBy("has_raw_ruby", has(ModItems.RAW_RUBY.get()))
        .save(output, ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_from_smelting"));
    }
}
```

---

## 2. Block Tags Generation (`BlockTagsProvider`)

Extend NeoForge's custom `BlockTagsProvider` to register block tags (e.g. mineable tools, ore tags).

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.PackOutput;
import net.minecraft.tags.BlockTags;
import net.neoforged.neoforge.common.Tags;
import net.neoforged.neoforge.common.data.BlockTagsProvider;
import net.neoforged.neoforge.common.data.ExistingFileHelper;
import org.jetbrains.annotations.Nullable;

import java.util.concurrent.CompletableFuture;

public class ModBlockTagProvider extends BlockTagsProvider {

    public ModBlockTagProvider(PackOutput output, CompletableFuture<HolderLookup.Provider> lookupProvider, @Nullable ExistingFileHelper existingFileHelper) {
        super(output, lookupProvider, TutorialMod.MODID, existingFileHelper);
    }

    @Override
    protected void addTags(HolderLookup.Provider provider) {
        // 1. Add blocks to vanilla tags (e.g., mineable with pickaxe, requires iron tool)
        this.tag(BlockTags.MINEABLE_WITH_PICKAXE)
                .add(ModBlocks.RUBY_BLOCK.get())
                .add(ModBlocks.RUBY_ORE.get());

        this.tag(BlockTags.NEEDS_IRON_TOOL)
                .add(ModBlocks.RUBY_BLOCK.get())
                .add(ModBlocks.RUBY_ORE.get());

        // 2. Add blocks to common tag (NeoForge uses 'c' namespace)
        this.tag(Tags.Blocks.ORES)
                .add(ModBlocks.RUBY_ORE.get());
    }
}
```

---

## 3. Item Tags Generation (`ItemTagsProvider`)

Extend the vanilla `ItemTagsProvider` to register item tags and copy existing block tags.

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.PackOutput;
import net.minecraft.data.tags.ItemTagsProvider;
import net.minecraft.world.level.block.Block;
import net.neoforged.neoforge.common.Tags;
import net.neoforged.neoforge.common.data.ExistingFileHelper;
import org.jetbrains.annotations.Nullable;

import java.util.concurrent.CompletableFuture;

public class ModItemTagProvider extends ItemTagsProvider {

    public ModItemTagProvider(PackOutput output, CompletableFuture<HolderLookup.Provider> lookupProvider,
                              CompletableFuture<TagLookup<Block>> blockTags, @Nullable ExistingFileHelper existingFileHelper) {
        super(output, lookupProvider, blockTags, TutorialMod.MODID, existingFileHelper);
    }

    @Override
    protected void addTags(HolderLookup.Provider provider) {
        // 1. Copy block tags directly to item tags (BlockItem -> Item tag mapping)
        // This is crucial for blocks in tags to match as items in tags.
        // E.g., copying your block ore tag to item ore tag
        // this.copy(Tags.Blocks.ORES, Tags.Items.ORES);

        // 2. Add simple items to tags
        this.tag(Tags.Items.GEMS)
                .add(ModItems.RUBY.get());

        this.tag(Tags.Items.RAW_MATERIALS)
                .add(ModItems.RAW_RUBY.get());
    }
}
```

---

## 4. Integration in `DataGenerators`

Update the `DataGenerators.gatherData` class to register these providers. Note that `ModItemTagProvider` depends on `ModBlockTagProvider`.

```java
@SubscribeEvent
public static void gatherData(GatherDataEvent event) {
    DataGenerator generator = event.getGenerator();
    PackOutput packOutput = generator.getPackOutput();
    ExistingFileHelper existingFileHelper = event.getExistingFileHelper();
    CompletableFuture<HolderLookup.Provider> lookupProvider = event.getLookupProvider();

    // 1. Register Recipe Provider
    generator.addProvider(event.includeServer(), new ModRecipeProvider(packOutput, lookupProvider));

    // 2. Register Tag Providers (BlockTagProvider must be declared first to pass its contents to ItemTagProvider)
    ModBlockTagProvider blockTags = new ModBlockTagProvider(packOutput, lookupProvider, existingFileHelper);
    generator.addProvider(event.includeServer(), blockTags);
    
    generator.addProvider(event.includeServer(), new ModItemTagProvider(
            packOutput,
            lookupProvider,
            blockTags.contentsGetter(), // Required lookup parameter
            existingFileHelper
    ));
}
```
