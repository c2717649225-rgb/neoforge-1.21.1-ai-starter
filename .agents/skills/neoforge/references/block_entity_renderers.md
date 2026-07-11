# NeoForge 1.21.1 方块实体动态渲染 (BlockEntityRenderer) 指南

在 Minecraft 模组开发中，有很多静态 JSON 模型无法实现的动态视觉效果。例如：**祭坛（Pedestal）上方缓缓自转并上下浮动的道具、动态转动的齿轮、或者根据能量值伸缩的活塞**。

这些特效需要使用 **`BlockEntityRenderer` (简称 BER)** 在游戏运行中动态计算并绘制。

---

## 1. 编写方块实体渲染器类 (BlockEntityRenderer)

动态渲染器必须实现 `BlockEntityRenderer<T>` 接口。为了在世界中渲染物品，我们需要在构造器中获取原版的渲染上下文：

```java
package com.tutorial.tutorialmod.client.renderer;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.tutorial.tutorialmod.block.entity.MyPedestalBlockEntity;
import net.minecraft.client.Minecraft;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.blockentity.BlockEntityRenderer;
import net.minecraft.client.renderer.blockentity.BlockEntityRendererProvider;
import net.minecraft.client.renderer.entity.ItemRenderer;
import net.minecraft.world.item.ItemDisplayContext;
import net.minecraft.world.item.ItemStack;

public class PedestalBlockEntityRenderer implements BlockEntityRenderer<MyPedestalBlockEntity> {

    private final ItemRenderer itemRenderer;

    // 构造器：通过 Context 获取 Minecraft 原版的 ItemRenderer
    public PedestalBlockEntityRenderer(BlockEntityRendererProvider.Context context) {
        this.itemRenderer = context.getItemRenderer();
    }

    // 核心渲染方法：每帧都会被调用进行动态绘制
    @Override
    public void render(MyPedestalBlockEntity blockEntity, float partialTick, PoseStack poseStack, 
                       MultiBufferSource bufferSource, int packedLight, int packedOverlay) {
        
        // 1. 获取方块实体中存放的物品 (例如玩家放置在祭坛上的宝石)
        ItemStack itemStack = blockEntity.getDisplayedItem();
        
        if (itemStack.isEmpty()) {
            return; // 没有物品，不执行绘制
        }

        // 2. 隔离渲染矩阵 (防止我们的平移/旋转影响到世界上其他物体的渲染)
        poseStack.pushPose();

        // 3. 将渲染中心平移至方块的顶部中央 (方块尺寸为 1.0 x 1.0 x 1.0)
        // X轴偏移 0.5，Y轴偏移 1.2 (悬浮在方块上方)，Z轴偏移 0.5
        double time = blockEntity.getLevel().getGameTime() + partialTick;
        double bobbingOffset = Math.sin(time * 0.1D) * 0.08D; // 利用正弦函数计算上下浮动微调值
        
        poseStack.translate(0.5D, 1.1D + bobbingOffset, 0.5D);

        // 4. 缩放物品尺寸（原版物品渲染默认很大，缩小至 0.6 倍适合摆放）
        poseStack.scale(0.6F, 0.6F, 0.6F);

        // 5. 让物品自转：绕 Y 轴不断旋转
        float rotationAngle = (float) (time * 3.0D); // 旋转速度系数
        poseStack.mulPose(Axis.YP.rotationDegrees(rotationAngle));

        // 6. 调用原版 ItemRenderer 渲染该 ItemStack
        // 参数：物品，渲染上下文类型（GROUND表示掉落物扁平模式，FIXED为固定模式，GUI为界面模式），光照，叠加光，PoseStack，缓冲区，世界，随机数种子
        this.itemRenderer.renderStatic(
                itemStack,
                ItemDisplayContext.GROUND, // 使用地面掉落物渲染模式 (会有微弱的 3D 厚度)
                packedLight,               // 传入当前方块坐标处的光照亮度（包含日光和方块光源，保证暗处变暗，亮处变亮）
                packedOverlay,             // 叠加特效（如闪烁红光）
                poseStack,
                bufferSource,
                blockEntity.getLevel(),
                0
        );

        // 7. 释放渲染矩阵，恢复默认空间状态
        poseStack.popPose();
    }
}
```

---

## 2. 注册渲染器 (EntityRenderersEvent.RegisterRenderers)

BER 的注册必须在客户端 Mod 事件总线上监听 `EntityRenderersEvent.RegisterRenderers` 进行注册，并且使用 `@EventBusSubscriber` 配合 `Dist.CLIENT` 物理安全隔离：

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.client.renderer.PedestalBlockEntityRenderer;
import com.tutorial.tutorialmod.block.entity.MyBlockEntities; // 假设我们注册的方块实体类型
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;

@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT) // 1.21.1+ 已废弃 bus 参数，系统会自动通过 IModBusEvent 路由
public class ClientRendererRegistrar {

    @SubscribeEvent
    public static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
        // 将自定义的渲染器绑定到特定的 BlockEntityType 上
        event.registerBlockEntityRenderer(
                MyBlockEntities.PEDESTAL_BLOCK_ENTITY.get(), // 绑定的方块实体类型
                PedestalBlockEntityRenderer::new             // 构造器引用
        );
    }
}
```

---

## 3. 性能优化与安全红线

*   **数据防抖缓存**：`render` 方法在客户端每帧都会被高频调用（FPS 多少就执行多少次）。**严禁**在 `render()` 内调用任何会分配内存的对象，比如 `new ItemStack()`、大循环遍历、或者复杂的计算。所有的浮空展示物品和状态数据，都应当在方块实体的 Java 类中用私有字段缓存好，在此处直接 $O(1)$ 读取。
*   **物理端安全隔离**：`BlockEntityRenderer` 和 `PoseStack` 属于纯物理客户端的图形学 API。此类必须严格放置在仅客户端加载的代码中，绝对不能在通用方块实体类中直接实例化或引用该渲染器，否则联机开服（Dedicated Server）启动时会导致直接闪退。
*   **光照计算传递**：在渲染物品时，必须传递 `packedLight` 参数（而不是写死最大亮度），否则物品在漆黑的矿洞里依然会显示 100% 亮度的荧光，破坏真实光影效果。
