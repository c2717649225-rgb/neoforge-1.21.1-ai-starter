# NeoForge 1.21.1 自定义合成与配方序列化 (Custom Recipes) 指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


科技模组（如发电机、粉碎机）或魔法模组（如祭坛）通常都需要自定义合成配方类型。在 1.21.1 中，配方系统废弃了旧的方法，**全面采用 Codec（`MapCodec` 和 `StreamCodec`）进行序列化**，并且用泛型的 **`RecipeInput` 接口**取代了旧版的 `Container` 接口。

以下是实现高扩展性、高性能自定义配方的标准范例。

---

## 1. 定义数据输入接口 (`RecipeInput`)

首先，定义一个轻量级的配方输入容器（例如单输入槽机器，如粉碎机）：

```java
package com.tutorial.tutorialmod.recipe;

import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.wrapper.RecipeInput;

public record SingleItemRecipeInput(ItemStack input) implements RecipeInput {
    @Override
    public ItemStack getItem(int index) {
        if (index != 0) {
            throw new IllegalArgumentException("Index " + index + " is out of bounds for SingleItemRecipeInput");
        }
        return this.input;
    }

    @Override
    public int size() {
        return 1;
    }
}
```

---

## 2. 编写自定义配方类 (`Recipe`)

配方类需要包含：输入 Ingredient、输出 ItemStack、以及匹配匹配逻辑：

```java
package com.tutorial.tutorialmod.recipe;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.HolderLookup;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;

public record CrushingRecipe(Ingredient ingredient, ItemStack result) implements Recipe<SingleItemRecipeInput> {

    @Override
    public boolean matches(SingleItemRecipeInput input, Level level) {
        // 匹配逻辑：玩家放入的物品是否符合我们定义的 Ingredient
        return this.ingredient.test(input.input());
    }

    @Override
    public ItemStack assemble(SingleItemRecipeInput input, HolderLookup.Provider registries) {
        // 返回合成结果的拷贝，确保不会污染原始数据
        return this.result.copy();
    }

    @Override
    public boolean canCraftInDimensions(int width, int height) {
        // 是否可以在特定大小的合成网格中合成（非工作台合成直接返回 true）
        return true;
    }

    @Override
    public ItemStack getResultItem(HolderLookup.Provider registries) {
        // 返回默认输出，用于 JEI 等模组进行展示
        return this.result;
    }

    @Override
    public RecipeSerializer<?> getSerializer() {
        return ModRecipes.CRUSHING_SERIALIZER.get();
    }

    @Override
    public RecipeType<?> getType() {
        return ModRecipes.CRUSHING_TYPE.get();
    }
}
```

---

## 3. 编写配方序列化器 (`RecipeSerializer`)

这是 1.21.1 中最关键的部分。需要使用 `MapCodec` 读取数据包 JSON，使用 `StreamCodec` 同步网络流。

```java
package com.tutorial.tutorialmod.recipe;

import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeSerializer;

public class CrushingRecipeSerializer implements RecipeSerializer<CrushingRecipe> {
    
    // 1. 用于读取和写入数据包 JSON 文件的 MapCodec
    public static final MapCodec<CrushingRecipe> CODEC = RecordCodecBuilder.mapCodec(instance ->
            instance.group(
                    Ingredient.CODEC_NONEMPTY.fieldOf("ingredient").forGetter(CrushingRecipe::ingredient),
                    ItemStack.CODEC.fieldOf("result").forGetter(CrushingRecipe::result)
            ).apply(instance, CrushingRecipe::new)
    );

    // 2. 用于在联机时将服务端配方同步到客户端的 StreamCodec（使用 RegistryFriendlyByteBuf 确保物品注册表被正确反序列化）
    public static final StreamCodec<RegistryFriendlyByteBuf, CrushingRecipe> STREAM_CODEC = StreamCodec.composite(
            Ingredient.CONTENTS_STREAM_CODEC, CrushingRecipe::ingredient,
            ItemStack.STREAM_CODEC, CrushingRecipe::result,
            CrushingRecipe::new
    );

    @Override
    public MapCodec<CrushingRecipe> codec() {
        return CODEC;
    }

    @Override
    public StreamCodec<RegistryFriendlyByteBuf, CrushingRecipe> streamCodec() {
        return STREAM_CODEC;
    }
}
```

---

## 4. 注册配方类型与序列化器

```java
package com.tutorial.tutorialmod.recipe;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.crafting.RecipeSerializer;
import net.minecraft.world.item.crafting.RecipeType;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModRecipes {
    // 1. 注册配方序列化器
    public static final DeferredRegister<RecipeSerializer<?>> RECIPE_SERIALIZERS =
            DeferredRegister.create(Registries.RECIPE_SERIALIZER, TutorialMod.MODID);
            
    // 2. 注册配方类型（用于标识配方属于哪种机器）
    public static final DeferredRegister<RecipeType<?>> RECIPE_TYPES =
            DeferredRegister.create(Registries.RECIPE_TYPE, TutorialMod.MODID);

    public static final DeferredHolder<RecipeSerializer<?>, RecipeSerializer<CrushingRecipe>> CRUSHING_SERIALIZER =
            RECIPE_SERIALIZERS.register("crushing", CrushingRecipeSerializer::new);

    public static final DeferredHolder<RecipeType<?>, RecipeType<CrushingRecipe>> CRUSHING_TYPE =
            RECIPE_TYPES.register("crushing", () -> new RecipeType<>() {
                @Override
                public String toString() {
                    return "crushing";
                }
            });
}
```
*切记在主类构造器中调用注册总线：*
`ModRecipes.RECIPE_SERIALIZERS.register(modEventBus);`
`ModRecipes.RECIPE_TYPES.register(modEventBus);`

---

## 5. 性能优化：配方快速缓存查找 (Recipe Caching)

对于需要在 Tick 中不断检查配方的自定义机器方块实体（`BlockEntity`），**绝对禁止**每 tick 直接调用 `RecipeManager#getRecipeFor()`，那会导致严重的线性扫描卡顿。

应该实现基于输入 ItemStack 的快速缓存匹配（使用 `RecipeManager.createRecipeLookup` 或缓存上一次匹配成功的 `RecipeHolder`）：

```java
package com.tutorial.tutorialmod.block.entity;

import com.tutorial.tutorialmod.recipe.CrushingRecipe;
import com.tutorial.tutorialmod.recipe.ModRecipes;
import com.tutorial.tutorialmod.recipe.SingleItemRecipeInput;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.Optional;

public class CrusherBlockEntity extends BlockEntity {
    // 缓存上一次成功匹配的配方引用，避免每 tick 遍历查找
    private RecipeHolder<CrushingRecipe> cachedRecipe = null;
    private ItemStack lastCheckedInput = ItemStack.EMPTY;

    public CrusherBlockEntity(BlockPos pos, BlockState state) {
        super(ModBlockEntities.CRUSHER.get(), pos, state);
    }

    public void tickServer() {
        ItemStack currentInput = this.getItemHandler().getStackInSlot(0); // 假设输入槽在 0 索引
        
        if (currentInput.isEmpty()) {
            this.cachedRecipe = null;
            this.lastCheckedInput = ItemStack.EMPTY;
            return;
        }

        // 性能优化核心点：仅当输入槽物品种类或数量变化时，才去执行昂贵的 RecipeManager 搜索
        if (!ItemStack.isSameItemSameComponents(currentInput, this.lastCheckedInput)) {
            this.lastCheckedInput = currentInput.copy();
            
            // 构造轻量级输入容器进行匹配
            SingleItemRecipeInput input = new SingleItemRecipeInput(currentInput);
            RecipeManager recipeManager = this.level.getRecipeManager();
            
            // 查找配方并将结果放入缓存中
            Optional<RecipeHolder<CrushingRecipe>> recipeOpt = recipeManager.getRecipeFor(
                    ModRecipes.CRUSHING_TYPE.get(),
                    input,
                    this.level
            );
            
            this.cachedRecipe = recipeOpt.orElse(null);
        }

        // 如果缓存的配方存在，执行冶炼进度增加逻辑
        if (this.cachedRecipe != null) {
            // this.progress++;
            // if (this.progress >= this.maxProgress) { this.craft(this.cachedRecipe); }
        }
    }
}
```
通过这种**输入状态对比 + 配方引用的快速缓存设计**，能够完美解决中大型模组中多台机器同时运行时导致的服务器 TPS 卡顿问题。