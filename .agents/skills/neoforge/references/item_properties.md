# NeoForge 1.21.1 物品动态渲染属性 (ItemProperties) 指南

在 Minecraft 中，有些 2D 物品需要根据自身的属性状态动态替换贴图纹理。最经典的例子是：**弓在拉弦时，随着拉力进度（pulling / pull）改变拉开程度贴图；盾牌在格挡（blocking）时展示格挡姿态贴图**。

这需要我们使用客户端的 **`ItemProperties`** 注册浮点数属性属性（Predicates），并在物品模型 JSON 中声明 `overrides` 覆写。

---

## 1. 注册客户端物品渲染属性 (ItemProperties)

此项注册必须在**物理客户端**进行，我们订阅客户端生命周期事件 `FMLClientSetupEvent`，并且为了线程安全，必须使用 **`event.enqueueWork(...)`**：

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.client.renderer.item.ItemProperties;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;

@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT)
public class ClientItemPropertiesRegistrar {

    @SubscribeEvent
    public static void onClientSetup(FMLClientSetupEvent event) {
        // 使用 enqueueWork 确保所有的属性注册都排程在客户端主线程安全执行
        event.enqueueWork(() -> {
            
            // 1. 注册自定义物品 (例如自定义的长弓: RUBY_BOW) 的 "pull" 进度属性 (0.0F ~ 1.0F)
            ItemProperties.register(
                    ModItems.RUBY_BOW.get(),
                    ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "pull"),
                    // Lambda 接收：ItemStack，当前Level，持有实体的LivingEntity，以及随机数种子
                    (stack, level, entity, seed) -> {
                        if (entity == null) {
                            return 0.0F;
                        }
                        // 如果玩家没有正在使用此长弓，拉力进度为 0
                        if (entity.getUseItem() != stack) {
                            return 0.0F;
                        }
                        // 计算拉弦已经持续的 tick 数
                        int useTicks = stack.getUseDuration(entity) - entity.getUseItemRemainingTicks();
                        return (float) useTicks / 20.0F; // 假设 20 tick (1秒) 拉满
                    }
            );

            // 2. 注册 "pulling" 状态属性 (0.0F 或 1.0F，代表是否处于拉弦状态)
            ItemProperties.register(
                    ModItems.RUBY_BOW.get(),
                    ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "pulling"),
                    (stack, level, entity, seed) -> {
                        return entity != null && entity.isUsingItem() && entity.getUseItem() == stack ? 1.0F : 0.0F;
                    }
            );
        });
    }
}
```

---

## 2. 在物品模型 JSON 中声明覆写 (overrides)

注册完 Java 属性后，我们必须在物品模型 JSON 中配置根据条件覆写贴图：

*   **文件路径**：`src/main/resources/assets/tutorialmod/models/item/ruby_bow.json`

```json
{
  "parent": "minecraft:item/generated",
  "textures": {
    "layer0": "tutorialmod:item/ruby_bow_standby"
  },
  "display": {},
  "overrides": [
    {
      "predicate": {
        "tutorialmod:pulling": 1.0
      },
      "model": "tutorialmod:item/ruby_bow_pulling_0"
    },
    {
      "predicate": {
        "tutorialmod:pulling": 1.0,
        "tutorialmod:pull": 0.65
      },
      "model": "tutorialmod:item/ruby_bow_pulling_1"
    },
    {
      "predicate": {
        "tutorialmod:pulling": 1.0,
        "tutorialmod:pull": 0.9
      },
      "model": "tutorialmod:item/ruby_bow_pulling_2"
    }
  ]
}
```

### 属性详解
*   `predicate`：判定匹配条件。例如当 `"tutorialmod:pulling"` 属性值为 `1.0` 且拉力值 `"tutorialmod:pull"` 达到 `0.9` 以上时，将自动切换为加载渲染 `tutorialmod:item/ruby_bow_pulling_2.json` 模型的材质贴图。
*   你需要额外为覆写分支分别创建对应的 `ruby_bow_pulling_0.json` 等常规层贴图映射文件。

---

## 3. 物理防崩溃红线

*   **隔离 `ItemProperties` 导入**：`ItemProperties`（`net.minecraft.client.renderer.item.ItemProperties`）类在物理服务端 Jar 包中**根本不存在**。必须将其完全限制在被 `@EventBusSubscriber(value = Dist.CLIENT)` 标记的客户端注册类中。绝对禁止在 Item 子类的 Java 构造函数、或者公共总线里直接调用此方法，否则会导致联机开服瞬间闪退。
*   **线程安全注册**：任何客户端静态渲染属性属性必须在 `event.enqueueWork(...)` 里面进行排程，严禁在其外部直接裸写，否则在联机状态下由于多线程并行冲突，有概率导致游戏启动时偶发性死锁或抛出并发注册冲突警告。

---

## 4. 1.21.1 自定义食物属性与物品使用红线

在 1.21.1 中，食物属性（`FoodProperties`）也是作为数据组件绑定的。通过 `Item.Properties().food(...)` 进行注册。

### ⚠️ 1.21.1 物品与食物使用高频编译错误防御与自愈

*   **编译报错**：`cannot find symbol: method isEdible() location: class Item / class ItemStack`
    *   ❌ 错误：使用 `stack.getItem().isEdible()` 或 `stack.isEdible()` 判断物品是否是食物。
    *   ✅ 修正：1.21.1 已经**彻底删除了该方法**。判断物品是否是食物，必须改为检测其食物组件属性：
        ```java
        stack.getFoodProperties(null) != null
        ```
*   **编译报错**：`method getUseDuration in class ItemStack cannot be applied to given types; required: LivingEntity, found: no arguments`
    *   ❌ 错误：在逻辑中无参调用 `stack.getUseDuration()`。
    *   ✅ 修正：在 1.21.1 中，`getUseDuration` 方法已变更为**必须传入一个 `LivingEntity` 实参**。即：
        ```java
        stack.getUseDuration(entity)
        ```
*   **编译报错**：`cannot find symbol: method alwaysEat() location: class Builder`
    *   ❌ 错误：配置食物属性时写 `.alwaysEat()`。
    *   ✅ 修正：1.21.1 的 `FoodProperties.Builder` 已经将该方法重命名为 `.alwaysEdible()`。
*   **编译报错**：`incompatible types: MobEffect cannot be converted to Holder<MobEffect>`
    *   ❌ 错误：`new MobEffectInstance(MobEffects.REGENERATION, 200)`（其中传入了裸 `MobEffect` 实例）。
    *   ✅ 修正：在 1.21.1 中，`MobEffects` 下所有的常量均为 `Holder<MobEffect>`，且 `MobEffectInstance` 构造器也要求接收 `Holder` 对象。直接透传常量即可。
