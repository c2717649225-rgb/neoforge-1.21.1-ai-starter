# NeoForge 1.21.1 自定义流体 (Custom Fluids) 注册与渲染指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


自定义流体是 Minecraft 模组中技术细节最多、环环相扣的系统。注册一个流体，必须打通 **FluidType (流体类型)**、**Source/Flowing Fluids (双端流体实例)**、**LiquidBlock (流体方块)** 和 **BucketItem (桶物品)** 之间的属性关联。

此外，在 1.21.1 中，流体的材质渲染必须使用 NeoForge 的 **`IClientFluidTypeExtensions`** 扩展，直接在流体类型中静态绑定。

---

## 1. 定义与注册 FluidType (流体类型)

`FluidType` 决定了流体的物理属性（如温度、粘度、光照强度）以及其客户端渲染材质（静止与流动贴图）：

```java
package com.tutorial.tutorialmod.fluid;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.client.extensions.common.IClientFluidTypeExtensions;
import net.neoforged.neoforge.fluids.FluidType;
import java.util.function.Consumer;

public class MyCustomFluidType extends FluidType {

    public MyCustomFluidType(Properties properties) {
        super(properties);
    }

    // 1.21.1 核心：重写此方法以绑定客户端流体渲染材质 (Still & Flowing)
    @Override
    public void initializeClient(Consumer<IClientFluidTypeExtensions> consumer) {
        consumer.accept(new IClientFluidTypeExtensions() {
            // 静止材质贴图 (指向 assets/tutorialmod/textures/block/liquid_ruby_still.png)
            private static final ResourceLocation STILL_TEXTURE =
                    ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "block/liquid_ruby_still");
            
            // 流动材质贴图 (指向 assets/tutorialmod/textures/block/liquid_ruby_flow.png)
            private static final ResourceLocation FLOWING_TEXTURE =
                    ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "block/liquid_ruby_flow");

            @Override
            public ResourceLocation getStillTexture() {
                return STILL_TEXTURE;
            }

            @Override
            public ResourceLocation getFlowingTexture() {
                return FLOWING_TEXTURE;
            }
        });
    }
}
```

---

## 2. 完整的流体与相关物品注册链

流体的注册需要五端绑定。以下是标准的注册类设计：

```java
package com.tutorial.tutorialmod.fluid;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.BucketItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LiquidBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.material.Fluid;
import net.neoforged.neoforge.fluids.BaseFlowingFluid;
import net.neoforged.neoforge.fluids.FluidType;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.NeoForgeRegistries;

public class ModFluids {
    // 1. 注册总线定义
    public static final DeferredRegister<FluidType> FLUID_TYPES =
            DeferredRegister.create(NeoForgeRegistries.Keys.FLUID_TYPES, TutorialMod.MODID);
            
    public static final DeferredRegister<Fluid> FLUIDS =
            DeferredRegister.create(Registries.FLUID, TutorialMod.MODID);

    // 2. 注册 FluidType（配置温度为 1000 开尔文，粘度/浓度为 1500）
    public static final DeferredHolder<FluidType, FluidType> RUBY_FLUID_TYPE =
            FLUID_TYPES.register("ruby_fluid", () -> new MyCustomFluidType(
                    FluidType.Properties.create()
                            .temperature(1000)
                            .viscosity(1500)
                            .density(1500)
            ));

    // 3. 注册源流体 (Source Fluid) 
    public static final DeferredHolder<Fluid, BaseFlowingFluid.Source> RUBY_FLUID_SOURCE =
            FLUIDS.register("ruby_fluid", () -> new BaseFlowingFluid.Source(ModFluids.RUBY_FLUID_PROPERTIES));

    // 4. 注册流动流体 (Flowing Fluid)
    public static final DeferredHolder<Fluid, BaseFlowingFluid.Flowing> RUBY_FLUID_FLOWING =
            FLUIDS.register("ruby_fluid_flowing", () -> new BaseFlowingFluid.Flowing(ModFluids.RUBY_FLUID_PROPERTIES));

    // 5. 声明属性包（关联流体类型、源流体、流动流体，并延时指定对应的方块和桶）
    public static final BaseFlowingFluid.Properties RUBY_FLUID_PROPERTIES =
            new BaseFlowingFluid.Properties(RUBY_FLUID_TYPE, RUBY_FLUID_SOURCE, RUBY_FLUID_FLOWING)
                    .slopeFindDistance(4) // 蔓延斜度查找距离 (水为4，岩浆为主世界2/下界4)
                    .levelDecreasePerBlock(1) // 每格流速衰减值 (水为1，岩浆为2)
                    .block(() -> ModFluids.RUBY_FLUID_BLOCK.get()) // 绑定的流体方块
                    .bucket(() -> ModFluids.RUBY_FLUID_BUCKET.get()); // 绑定的桶物品

    // 6. 注册在世界中呈现的物理流体方块 (LiquidBlock)
    public static final DeferredHolder<Block, LiquidBlock> RUBY_FLUID_BLOCK =
            ModBlocks.BLOCKS.register("ruby_fluid_block", () ->
                    new LiquidBlock(RUBY_FLUID_SOURCE.get(), BlockBehaviour.Properties.ofFullCopy(Blocks.LAVA))
            );

    // 7. 注册桶装流体物品 (BucketItem)
    public static final DeferredHolder<Item, BucketItem> RUBY_FLUID_BUCKET =
            ModItems.ITEMS.register("ruby_fluid_bucket", () ->
                    new BucketItem(RUBY_FLUID_SOURCE.get(), new Item.Properties()
                            .craftRemainder(Items.BUCKET) // 倒出液体后在合成栏/容器中留下空桶
                            .stacksTo(1) // 堆叠上限为 1
                    )
            );
}
```

*主类构造器中必须注册对应总线：*
`ModFluids.FLUID_TYPES.register(modEventBus);`
`ModFluids.FLUIDS.register(modEventBus);`

---

## 3. 在磁盘中添加材质与本地化说明

### 3.1 贴图文件放入目录
由于我们在 `MyCustomFluidType` 中指定的贴图前缀为 `block/liquid_ruby_still` 和 `block/liquid_ruby_flow`，您需要将以下两个 `.png` 文件和同名的 `.mcmeta` 动画配置文件（如果需要流动动画）放入对应的资源目录下：
*   **静止材质**：`src/main/resources/assets/tutorialmod/textures/block/liquid_ruby_still.png`
*   **流动材质**：`src/main/resources/assets/tutorialmod/textures/block/liquid_ruby_flow.png`

### 3.2 翻译 Key 配置
*   **中文文件 (zh_cn.json)**：
    ```json
    {
      "fluid_type.tutorialmod.ruby_fluid": "液态红宝石",
      "block.tutorialmod.ruby_fluid_block": "液态红宝石方块",
      "item.tutorialmod.ruby_fluid_bucket": "液态红宝石桶"
    }
    ```
    *注：流体类型的翻译 Key 固定前缀为 `fluid_type.<modid>.<fluid_type_name>`。*