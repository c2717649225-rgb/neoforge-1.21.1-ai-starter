# NeoForge 1.21.1 Registration & Data Component Example

This file serves as a reference for standard registration patterns and using the new Data Component system in Minecraft 1.21.1.

## 1. Basic Registry Setup

Use `DeferredRegister` for blocks, items, components, and other registry types. Register the registers to the mod event bus in the mod constructor.

```java
public class MyMod {
    public static final String MODID = "mymod";
    
    // Create registers
    public static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks(MODID);
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems(MODID);
    
    public MyMod(IEventBus modEventBus, ModContainer modContainer) {
        // Register to event bus
        BLOCKS.register(modEventBus);
        ITEMS.register(modEventBus);
    }
}
```

## 2. Registering Blocks & Items

```java
// Registering a simple block
public static final DeferredBlock<Block> RUBY_BLOCK = BLOCKS.registerSimpleBlock(
    "ruby_block", 
    BlockBehaviour.Properties.of()
        .mapColor(MapColor.COLOR_RED)
        .strength(5.0F, 6.0F)
        .requiresCorrectToolForDrops()
);

// Registering a block item for the block
public static final DeferredItem<BlockItem> RUBY_BLOCK_ITEM = ITEMS.registerSimpleBlockItem(
    "ruby_block", 
    RUBY_BLOCK
);

// Registering a simple item
public static final DeferredItem<Item> RUBY = ITEMS.registerSimpleItem(
    "ruby", 
    new Item.Properties()
);
```

## 3. Registering & Using Custom Data Components (Replacing NBT)

In 1.21.1, items store custom data via **Data Components** instead of NBT. You must register custom components and read/write them using the component API.

### Step A: Register the Data Component Type

Create a `DeferredRegister` for components:

```java
import net.minecraft.core.component.DataComponentType;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.codec.ByteBufCodecs;
import com.mojang.serialization.Codec;

public class MyComponents {
    public static final DeferredRegister<DataComponentType<?>> DATA_COMPONENT_TYPES = 
        DeferredRegister.create(Registries.DATA_COMPONENT_TYPE, MyMod.MODID);
        
    // Define a simple integer component (e.g. magic energy charge)
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> ENERGY = 
        DATA_COMPONENT_TYPES.register("energy", () -> DataComponentType.<Integer>builder()
            .persistent(Codec.INT) // Allows the component to be saved to disk and synced
            .networkSynchronized(ByteBufCodecs.VAR_INT) // For networking sync
            .build()
        );
}
```

Make sure to register `MyComponents.DATA_COMPONENT_TYPES.register(modEventBus)` in your main mod constructor!

### Step B: Reading and Writing Components on an ItemStack

```java
ItemStack stack = new ItemStack(MyItems.RUBY.get());

// 1. Writing / setting component value
stack.set(MyComponents.ENERGY.get(), 100);

// 2. Reading component value (returns null if not present)
Integer energy = stack.get(MyComponents.ENERGY.get());
if (energy != null) {
    // Component is present
    System.out.println("Energy is: " + energy);
}

// 3. Getting with a fallback default value
int currentEnergy = stack.getOrDefault(MyComponents.ENERGY.get(), 0);

// 4. Modifying existing value
stack.update(MyComponents.ENERGY.get(), 0, currentEnergy -> currentEnergy + 10);
```

---

## 4. 自定义物品类与新版悬浮提示 (Tooltip)

在 1.21.1 中，重写物品的悬浮提示方法 `appendHoverText` 参数签名已发生改变：**`Level` 参数被替换为了 `Item.TooltipContext`**。

以下是实现“按住 Shift 键显示详细说明”的自定义物品类范例：

```java
package com.tutorial.tutorialmod.item;

import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ChatFormatting;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import java.util.List;

public class RubyWandItem extends Item {

    public RubyWandItem(Properties properties) {
        super(properties);
    }

    // 1.21.1 新版重写方法签名 (注意：Level 被移入到了 TooltipContext 中)
    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {
        // 默认显示的基础文字
        tooltipComponents.add(Component.translatable("tooltip.tutorialmod.ruby_wand.desc")
                .withStyle(ChatFormatting.GRAY));

        // 【严重警告】绝对不要直接在这里写 Screen.hasShiftDown()，这会导致 Dedicated Server (专用服务端) 在类加载验证时抛出 NoClassDefFoundError 崩溃！
        // 错误言论修正：“JVM 延迟加载”并不可靠，类验证器随时可能触发类解析。
        // 正确做法：必须使用 FMLEnvironment.dist == Dist.CLIENT 守卫，并调用客户端专门的辅助类（例如 ClientTooltipUtil）。
        
        if (net.neoforged.fml.loading.FMLEnvironment.dist == net.neoforged.api.distmarker.Dist.CLIENT) {
            if (com.tutorial.tutorialmod.client.ClientTooltipUtil.isShiftDown()) {
                // 显示详细的高阶属性说明
                tooltipComponents.add(Component.literal(" ")
                        .withStyle(ChatFormatting.DARK_PURPLE));
                tooltipComponents.add(Component.translatable("tooltip.tutorialmod.ruby_wand.shift_info_1")
                        .withStyle(ChatFormatting.AQUA));
                tooltipComponents.add(Component.translatable("tooltip.tutorialmod.ruby_wand.shift_info_2")
                        .withStyle(ChatFormatting.GOLD));
            } else {
                // 提示玩家按住 Shift
                tooltipComponents.add(Component.translatable("tooltip.tutorialmod.press_shift")
                        .withStyle(ChatFormatting.YELLOW, ChatFormatting.ITALIC));
            }
        }

        super.appendHoverText(stack, context, tooltipComponents, tooltipFlag);
    }
}
```
通过使用客户端守护与 `ClientTooltipUtil.isShiftDown()` 判定，可实现安全、防崩溃且符合原版视觉感受的物品信息悬浮反馈。
