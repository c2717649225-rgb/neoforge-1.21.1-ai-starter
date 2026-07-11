# NeoForge 1.21.1 JEI (Just Enough Items) 联动开发指南

当中大型模组（尤其是包含自定义机器与配方的科技/魔法模组）发布时，对接 JEI 几乎是硬性标准。这能让玩家通过按 R 键直接查询机器配方。

在 1.21.1 中，JEI API 全面适配了 **`GuiGraphics` 绘制流** 和 **`IFocusGroup` 焦点筛选**。以下是编写 JEI 兼容插件的完整标准范例。

---

## 1. 创建 JEI 插件主类 (Entry Point)

JEI 会自动扫描带有 `@JeiPlugin` 注解的类。请确保该类不在物理客户端专属目录，因为它需要能够安全地在双端（主要是客户端加载时）被 JEI 检索加载：

```java
package com.tutorial.tutorialmod.compat.jei;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.recipe.CrushingRecipe;
import com.tutorial.tutorialmod.recipe.ModRecipes;
import mezz.jei.api.IModPlugin;
import mezz.jei.api.JeiPlugin;
import mezz.jei.api.registration.IRecipeCatalystRegistration;
import mezz.jei.api.registration.IRecipeCategoryRegistration;
import mezz.jei.api.registration.IRecipeRegistration;
import net.minecraft.client.Minecraft;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeManager;

import java.util.List;

@JeiPlugin
public class TutorialModJeiPlugin implements IModPlugin {
    
    public static final ResourceLocation PLUGIN_ID = 
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "jei_plugin");

    @Override
    public ResourceLocation getPluginUid() {
        return PLUGIN_ID;
    }

    // 1. 注册自定义配方页面分类 (Category)
    @Override
    public void registerCategories(IRecipeCategoryRegistration registration) {
        registration.addRecipeCategories(new CrushingRecipeCategory(
                registration.getJeiHelpers().getGuiHelper()
        ));
    }

    // 2. 将游戏内的配方数据全量注入到 JEI 容器中展示
    @Override
    public void registerRecipes(IRecipeRegistration registration) {
        RecipeManager recipeManager = Minecraft.getInstance().level.getRecipeManager();
        
        // 从原版配方管理器中拉取我们注册的粉碎机（Crushing）配方列表
        List<CrushingRecipe> recipes = recipeManager.getAllRecipesFor(ModRecipes.CRUSHING_TYPE.get())
                .stream()
                .map(RecipeHolder::value) // 1.21 中获取真实 Recipe 实例
                .toList();

        // 注入到我们定义的分类下
        registration.addRecipes(CrushingRecipeCategory.TYPE, recipes);
    }

    // 3. 注册催化剂（即把我们的机器方块绑定为配方入口，玩家在 JEI 点击该方块可以直接跳转查阅其所有配方）
    @Override
    public void registerRecipeCatalysts(IRecipeCatalystRegistration registration) {
        registration.addRecipeCatalyst(
                new ItemStack(ModBlocks.CRUSHER.get()), 
                CrushingRecipeCategory.TYPE
        );
    }
}
```

---

## 2. 编写自定义配方显示页面 (`IRecipeCategory`)

`IRecipeCategory` 负责定义配方在 JEI 面板中的排版、背景绘制、插槽对齐以及动态箭头动画：

```java
package com.tutorial.tutorialmod.compat.jei;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.recipe.CrushingRecipe;
import mezz.jei.api.constants.VanillaTypes;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.gui.drawable.IDrawableAnimated;
import mezz.jei.api.gui.ingredient.IRecipeSlotsView;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeIngredientRole;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;

public class CrushingRecipeCategory implements IRecipeCategory<CrushingRecipe> {
    
    // 定义该分类所处理的唯一配方类型绑定
    public static final RecipeType<CrushingRecipe> TYPE = 
            new RecipeType<>(
                    ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "crushing"), 
                    CrushingRecipe.class
            );

    private final IDrawable background;
    private final IDrawable icon;
    private final IDrawableAnimated arrow; // 动态进度箭头

    public CrushingRecipeCategory(IGuiHelper helper) {
        // 1. 使用 JEI 提供的材质定位，截取我们的机器 GUI 贴图的一部分作为 JEI 的背景面板 (这里宽 120, 高 50)
        ResourceLocation guiTexture = ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "textures/gui/crusher.png");
        this.background = helper.createDrawable(guiTexture, 30, 20, 120, 50);

        // 2. 设置该分类在 JEI 顶部的展示图标（使用我们的机器方块作为图标）
        this.icon = helper.createDrawableIngredient(VanillaTypes.ITEM_STACK, new ItemStack(ModBlocks.CRUSHER.get()));

        // 3. 截取并创建动态进度箭头 (由 x=176, y=14 截取 24x17 的剪刀/箭头材质，动画时长 200 ticks 即 10秒)
        this.arrow = helper.drawableBuilder(guiTexture, 176, 14, 24, 17)
                .buildAnimated(200, IDrawableAnimated.StartDirection.LEFT, false);
    }

    @Override
    public RecipeType<CrushingRecipe> getRecipeType() {
        return TYPE;
    }

    @Override
    public Component getTitle() {
        return Component.translatable("container.tutorialmod.crusher");
    }

    @Override
    public IDrawable getBackground() {
        return this.background;
    }

    @Override
    public IDrawable getIcon() {
        return this.icon;
    }

    // 4. 将配方的 Ingredient 和结果映射绑定到面板上
    // 注意：1.21.1 签名第三个参数为 IFocusGroup
    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, CrushingRecipe recipe, IFocusGroup focuses) {
        // 将输入 Ingredient 绑定在左侧坐标 (10, 15)
        builder.addSlot(RecipeIngredientRole.INPUT, 10, 15)
                .addIngredients(recipe.ingredient());

        // 将输出结果 ItemStack 绑定在右侧坐标 (80, 15)
        builder.addSlot(RecipeIngredientRole.OUTPUT, 80, 15)
                .addItemStack(recipe.result());
    }

    // 5. 绘制额外的 UI 特效（如进度条动画、火焰燃烧等）
    // 注意：1.21.1 签名使用 GuiGraphics 进行渲染
    @Override
    public void draw(CrushingRecipe recipe, IRecipeSlotsView recipeSlotsView, GuiGraphics guiGraphics, double mouseX, double mouseY) {
        // 在相对于背景面板 (45, 15) 的位置渲染进度箭头
        this.arrow.draw(guiGraphics, 45, 15);
    }
}
```

---

## 3. build.gradle 配置说明

在开发环境中，若需要引入并测试 JEI 联动，必须在 `build.gradle` 中追加对应的依赖。通常采用条件加载（`compileOnly`）或本地运行时加载（`runtimeOnly`）：

```groovy
dependencies {
    // 引入 JEI API（用于编写插件代码编译）
    compileOnly "mezz.jei:jei-1.21.1-neoforge-api:${jei_version}"
    
    // 在本地测试启动游戏时（gradlew runClient），自动在本地加载 JEI 便于调试
    runtimeOnly "mezz.jei:jei-1.21.1-neoforge:${jei_version}"
}
```

> [!TIP]
> **安全防护（无崩溃设计）**：
> JEI 的 `@JeiPlugin` 被注解标记后，其全部类只有在**客户端检测到有 JEI 模组存在时**才会被 JVM 检索载入。若玩家没有安装 JEI 直接运行模组，这段插件代码将静默被 JVM 忽略，**完全不会因为类加载缺失导致游戏在原版环境下崩溃**，具备极其出色的安全防护能力。
