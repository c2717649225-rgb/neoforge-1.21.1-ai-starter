# NeoForge 1.21.1 物品与方块动态着色 (Color Handlers) 指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


在 Minecraft 开发中，如果需要实现“根据方块所处生物群系动态改变方块颜色（如树叶、草方块）”，或者“根据 ItemStack 中的动态变量（如电能百分比、魔法属性）渲染不同的武器贴图颜色”，最优雅的方式是使用**颜色处理器 (Color Handlers)**。

这避免了为同一种贴图重复绘制几十种颜色的低效手段。

---

## 1. 材质 JSON 中的 `tintindex` 设定

颜色处理器根据模型 JSON 中的 **`tintindex`（染色索引）** 来精准识别应该对贴图的哪一部分进行上色。

在您的 `models/item/` 或 `models/block/` 的 JSON 文件中，如果希望某一层贴图被代码动态着色，必须显式指明其 `tintindex`（例如 `0` 表示第一染色层，不写则不进行染色）：

```json
{
  "parent": "minecraft:item/generated",
  "textures": {
    "layer0": "tutorialmod:item/magic_wand_base",   // 基础材质（不染色）
    "layer1": "tutorialmod:item/magic_wand_crystal" // 水晶材质（这一层将被我们用代码动态上色）
  },
  "elements": [],
  "overrides": [],
  "gui_light": "front"
}
```
*注：在上面的 JSON 中，`layer1` 会被默认识别为 `tintIndex == 1`（按声明顺序或配置）。*

---

## 2. 注册物品着色器 (RegisterColorHandlersEvent.Item)

物品的染色必须在客户端 Mod 事件总线上监听 `RegisterColorHandlersEvent.Item` 进行注册，并且使用 `@EventBusSubscriber` 的物理客户端安全隔离防闪退：

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.item.ModItems;
import com.tutorial.tutorialmod.recipe.MyComponents; // 假设我们之前注册的组件
import net.minecraft.client.color.item.ItemColor;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterColorHandlersEvent;

@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT)
public class ClientColorRegistrar {

    @SubscribeEvent
    public static void registerItemColors(RegisterColorHandlersEvent.Item event) {
        // 注册物品着色器。Lambda 表达式接收：ItemStack 和当前正在被渲染的材质层的 tintIndex
        event.register(
                new ItemColor() {
                    @Override
                    public int getColor(net.minecraft.world.item.ItemStack stack, int tintIndex) {
                        // 1. 过滤染色索引：只对 tintindex 为 1 的水晶层（layer1）进行上色
                        if (tintIndex == 1) {
                            
                            // 2. 从物品数据组件（Data Components）中读取魔力量
                            int magicEnergy = stack.getOrDefault(MyComponents.ENERGY.get(), 0);
                            
                            // 3. 根据魔力比例，动态返回一个包含 Alpha 通道的 32位 ARGB 十六进制整型颜色
                            if (magicEnergy >= 80) {
                                return 0xFFFF00FF; // 满魔力：亮粉色 (Alpha: FF, R: FF, G: 00, B: FF)
                            } else if (magicEnergy >= 40) {
                                return 0xFF00FFFF; // 中等魔力：天蓝色
                            } else {
                                return 0xFFFF0000; // 低魔力：红色
                            }
                        }
                        
                        // 4. 返回 0xFFFFFFFF 代表“不染色（保留原 PNG 贴图的像素色）”
                        return 0xFFFFFFFF;
                    }
                },
                ModItems.RUBY_WAND.get() // 绑定到具体的物品
        );
    }
}
```

---

## 3. 注册方块着色器 (RegisterColorHandlersEvent.Block)

如果是方块需要动态染色（如不同群系颜色不同的草地方块，或者根据能量状态变色的电缆），需要使用 `RegisterColorHandlersEvent.Block` 事件：

```java
    @SubscribeEvent
    public static void registerBlockColors(RegisterColorHandlersEvent.Block event) {
        event.register(
                (state, level, pos, tintIndex) -> {
                    // level 和 pos 可能为空（例如在物品栏、或者 JEI 里面展示该方块的虚拟投影时）
                    if (level != null && pos != null) {
                        if (tintIndex == 0) {
                            // 读取当前方块所处坐标的群系草地颜色
                            return net.minecraft.client.renderer.BiomeColors.getAverageGrassColor(level, pos);
                        }
                    }
                    // 默认草地绿颜色 (0x79C05A)
                    return 0xFF79C05A;
                },
                ModBlocks.RUBY_BLOCK.get() // 绑定方块
        );
    }
```

---

## 4. 关键避坑与注意事项

*   **物理双端安全隔离**：无论是 `ItemColor` 还是 `BlockColor`，由于它们使用了客户端渲染的 `ItemColors` 和 `BiomeColors` 类，**必须严格放在 `Dist.CLIENT` 标记的事件订阅器类里**。严禁直接在主类或通用包中注册，否则联机开服直接发生 `NoClassDefFoundError` 奔溃。
*   **1.21.1 性能红线**：颜色处理器在客户端渲染的每帧都会为每个渲染插槽（Slot）高频调用。**绝对禁止**在 `getColor` 方法中读取磁盘、进行大循环、或者频繁调用 `new` 关键字生成临时垃圾对象，否则会因为引起频繁的 GC（垃圾回收器）动作而导致玩家游戏画面剧烈卡顿（掉帧）。