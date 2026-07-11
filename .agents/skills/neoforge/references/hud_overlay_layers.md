# NeoForge 1.21.1 HUD 界面图层 (GUI Layers) 渲染指南

如果模组需要实时展示自定义能量条、宠物状态、虚空之盾或特殊动作条，则需要在屏幕上绘制自定义 HUD 覆盖图层。

在 1.21.1 中，NeoForge **彻底废除了旧版的 `IGuiOverlay` 机制，升级为了全新的 GUI Layers（界面图层）系统**。以下是编写物理安全、坐标自适应的 HUD 图层的开发范例。

---

## 1. 注册自定义 HUD 图层 (RegisterGuiLayersEvent)

自定义图层的注册必须在客户端 Mod 事件总线上监听 `RegisterGuiLayersEvent` 进行注册，并且使用 `@EventBusSubscriber` 配合 `Dist.CLIENT` 物理安全隔离：

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterGuiLayersEvent;
import net.neoforged.neoforge.client.gui.VanillaGuiLayers;

@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT) // 1.21.1+ 已废弃 bus 参数，系统会自动通过 IModBusEvent 路由
public class ClientHUDRegistrar {

    @SubscribeEvent
    public static void registerGuiLayers(RegisterGuiLayersEvent event) {
        // 使用 event.registerAbove 将我们的图层精确渲染在原版快捷栏 (HOTBAR) 之上
        event.registerAbove(
                VanillaGuiLayers.HOTBAR, // 锚定层 (也可以是 VanillaGuiLayers.EXPERIENCE_BAR 等)
                ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "wolf_status_hud"), // 图层唯一ID
                (guiGraphics, deltaTracker) -> {
                    // 调用我们具体的 HUD 渲染体
                    renderWolfStatusHUD(guiGraphics, deltaTracker.getGameTimeDeltaTicks());
                }
        );
    }

    private static void renderWolfStatusHUD(GuiGraphics guiGraphics, float partialTick) {
        // 渲染核心逻辑...
    }
}
```

---

## 2. 编写动态绘制逻辑 (Drawing & Layout)

在 HUD 渲染中，需要根据窗口分辨率动态计算渲染原点（例如正中心、偏右下方），并调用 `GuiGraphics` 的绘制 API：

```java
    private static final ResourceLocation HUD_TEXTURE = 
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "textures/gui/hud_elements.png");

    private static void renderWolfStatusHUD(GuiGraphics guiGraphics, float partialTick) {
        net.minecraft.client.Minecraft minecraft = net.minecraft.client.Minecraft.getInstance();
        
        // 1. 安全检查：如果玩家处于旁观者模式，或者打开了任何游戏菜单界面，则隐藏 HUD
        if (minecraft.player == null || minecraft.player.isSpectator() || minecraft.screen != null) {
            return;
        }

        // 2. 获取当前窗口的宽度与高度 (用于自适应排版)
        int width = minecraft.getWindow().getGuiScaledWidth();
        int height = minecraft.getWindow().getGuiScaledHeight();

        // 3. 计算坐标原点 (例如放在屏幕快捷栏右侧 50 格，贴着底部上方 40 格)
        int x = width / 2 + 95;
        int y = height - 40;

        // 4. 渲染文字 (参数：字体渲染器，文字 Component，坐标，颜色，是否带阴影)
        String levelText = "Active Companion Level: 30";
        guiGraphics.drawString(
                minecraft.font,
                levelText,
                x, y,
                0xFFFFAA00, // 亮橙色 (ARGB 格式)
                true        // 启用阴影
        );

        // 5. 渲染贴图元素 (如爱心、能量槽)
        // 参数：贴图路径，屏幕绘制X，屏幕绘制Y，材质UV_X，材质UV_Y，绘制宽度，绘制高度
        guiGraphics.blit(
                HUD_TEXTURE,
                x, y + 12,        // 绘制坐标
                0, 0,             // 贴图在素材文件中的左上角坐标 (UV)
                9, 9              // 渲染 9x9 的小爱心贴图
        );
        
        // 6. 绘制半透明几何图形 (常用于绘制背景条)
        // 参数：左X，上Y，右X，下Y，32位十六进制颜色（含透明度）
        guiGraphics.fill(
                x - 2, y - 2, 
                x + 120, y + 25, 
                0x77000000 // 半透明黑色背景 (0x77 透明度，0x000000 黑色)
        );
    }
```

---

## 3. 性能优化与安全红线

*   **仅在客户端运行**：HUD 绘制属于纯客户端的底层渲染流。绝对禁止在 HUD 渲染代码中直接修改服务端的数据（如调用 `player.heal()`），也不要直接读取不稳定的数据包，必须保证只从本地客户端实例（`Minecraft.getInstance()`）及其持有的本地实体/玩家中读取镜像数据。
*   **避免高开销操作**：`render` 方法在客户端每帧都会被调用（FPS 多少就调用多少次，通常每秒上百次）。**绝对禁止**在此方法中进行 `new ItemStack()`、大集合遍历、或者复杂的数学计算。所有数值应该提前在 `Clientbound` 同步包中处理并缓存好，渲染逻辑只负责 $O(1)$ 的读取与呈现。
*   **图层屏蔽**：如果想完全关掉某个原版的 GUI 层（例如当玩家骑马时屏蔽掉原版心形栏，或者开发自定义状态栏来替换原版饱食度栏），可以使用 `RegisterGuiLayersEvent` 提供的禁用功能。
