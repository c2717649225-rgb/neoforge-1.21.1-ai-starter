# NeoForge 1.21.1 创造模式物品栏与模组配置模板

本文件提供编写 Minecraft 1.21.1 NeoForge 模组时最常用的两个基础脚手架代码：**创造模式物品栏 (Creative Tabs)** 和 **模组配置文件系统 (Config System)**。

---

## 1. 创造模式物品栏 (Creative Tabs)

有两类方法将物品加入创造模式：**新建自定义物品栏**，或**将物品追加到原版的物品栏**（如“原料”、“武器”等）。

### 1.1 新建自定义创造模式物品栏 (`CreativeModeTab`)
使用 `DeferredRegister` 注册自定义物品栏，推荐将其指定图标并绑定展示项：

```java
package com.tutorial.tutorialmod.item;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModCreativeTabs {
    public static final DeferredRegister<CreativeModeTab> CREATIVE_MODE_TABS =
            DeferredRegister.create(Registries.CREATIVE_MODE_TAB, TutorialMod.MODID);

    public static final DeferredHolder<CreativeModeTab, CreativeModeTab> TUTORIAL_TAB = CREATIVE_MODE_TABS.register(
            "tutorial_tab",
            () -> CreativeModeTab.builder()
                    .title(Component.translatable("itemGroup.tutorial_tab")) // 语言键名
                    .icon(() -> new ItemStack(ModItems.RUBY.get()))         // 物品栏图标
                    .displayItems((parameters, output) -> {
                        // 在此添加该物品栏要展示的所有方块和物品
                        output.accept(ModItems.RUBY.get());
                        output.accept(ModItems.RAW_RUBY.get());
                        output.accept(ModBlocks.RUBY_BLOCK.get());
                        output.accept(ModBlocks.RUBY_ORE.get());
                    })
                    .build()
    );
}
```
*在主类构造器中必须调用 `ModCreativeTabs.CREATIVE_MODE_TABS.register(modEventBus)`*

### 1.2 追加物品到原版物品栏
如果您不想创建新物品栏，只想把自定义物品挂载到原版（如“原料”栏）：
```java
package com.tutorial.tutorialmod.event;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.world.item.CreativeModeTabs;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.BuildCreativeModeTabContentsEvent;

@EventBusSubscriber(modid = TutorialMod.MODID)
public class ModCreativeTabEvents {

    @SubscribeEvent
    public static void buildContents(BuildCreativeModeTabContentsEvent event) {
        // 判断当前构建的物品栏是否是原版的 "原料 (INGREDIENTS)" 栏
        if (event.getTabKey() == CreativeModeTabs.INGREDIENTS) {
            // 将我们的红宝石和粗红宝石追加到该物品栏中
            event.accept(ModItems.RUBY.get());
            event.accept(ModItems.RAW_RUBY.get());
        }
    }
}
```

---

## 2. 模组配置系统 (Config System)

NeoForge 提供了内置的配置系统，允许生成并在 `config/` 目录下读取 `.toml` 配置文件。

### 2.1 定义配置规范 (`ModConfigSpec`)
```java
package com.tutorial.tutorialmod.config;

import net.neoforged.neoforge.common.ModConfigSpec;

public class ModCommonConfigs {
    public static final ModConfigSpec.Builder BUILDER = new ModConfigSpec.Builder();
    public static final ModConfigSpec SPEC;

    // 定义配置项
    public static final ModConfigSpec.ConfigValue<Integer> MAX_ENERGY;
    public static final ModConfigSpec.ConfigValue<String> MACHINE_NAME;
    public static final ModConfigSpec.BooleanValue ALLOW_AUTO_CRAFT;

    static {
        BUILDER.push("General Settings");

        MAX_ENERGY = BUILDER.comment("机器的最大能量容量")
                .defineInRange("maxEnergy", 10000, 1000, 100000);

        MACHINE_NAME = BUILDER.comment("机器的默认名称显示")
                .define("machineName", "Ruby Machine");

        ALLOW_AUTO_CRAFT = BUILDER.comment("是否允许机器自动合成")
                .define("allowAutoCraft", true);

        BUILDER.pop();
        SPEC = BUILDER.build();
    }
}
```

### 2.2 在模组中注册和读取配置
在您主类的构造函数中进行绑定：
```java
package com.tutorial.tutorialmod;

import com.tutorial.tutorialmod.config.ModCommonConfigs;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;

@Mod(TutorialMod.MODID)
public class TutorialMod {
    public static final String MODID = "tutorialmod";

    public TutorialMod(IEventBus modEventBus, ModContainer modContainer) {
        // 注册 Common 类型的配置文件。这会在游戏启动时自动读取/生成 config/tutorialmod-common.toml
        modContainer.registerConfig(ModConfig.Type.COMMON, ModCommonConfigs.SPEC);
        
        // 其它注册逻辑...
    }
}
```

### 2.3 在代码中使用配置值
```java
// 使用 .get() 读取值
int maxCapacity = ModCommonConfigs.MAX_ENERGY.get();
if (ModCommonConfigs.ALLOW_AUTO_CRAFT.get()) {
    // 执行自动合成逻辑
}
```

---

### 2.4 性能与生命周期警告：COMMON 与 SERVER 配置的区别 (Lifecycle Warning)

> [!WARNING]
> 在 NeoForge 1.21.1 中，配置文件有严格的加载生命周期限制：
> 1. **`COMMON` 配置**：在游戏启动期加载。**可以**在 `CommonSetup` 或注册表初始化时安全读取。它保存在全局 `config/` 目录下，双端独立读取，不强制同步。
> 2. **`SERVER` 配置**：保存在存档的 `serverconfig/` 目录中，在联机时由服务端强制同步给客户端。**只有在世界/地图加载时才会读取**。
>
> **避坑红线**：严禁在 `FMLCommonSetupEvent`、物品/方块注册阶段或主类构造器中调用 `ModConfig.Type.SERVER` 的配置值，否则在游戏启动时会直接抛出 `NullPointerException` 并崩溃。服务器配置值只能在游戏运行期（例如：方块 Tick、玩家交互、事件触发）被动态调用。

