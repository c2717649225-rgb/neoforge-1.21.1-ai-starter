# NeoForge 1.21.1 数据映射 (Data Maps) 进阶开发指南

在 Minecraft 1.21 及以上版本中，NeoForge 引入了全新的**数据映射 (Data Maps)** 系统。它允许我们将自定义的数据对象，通过**数据包（JSON 资源）**的形式动态挂载到任何注册表项（如 `Item`、`Block`、`EntityType` 等）上。

这在很大程度上替代了传统“硬编码标签 (Tag)”或“自定义 JSON 文件加载”的方式，提供了一种支持热重载、高度兼容的多模组配置共享方案。

---

## 1. 声明数据映射的 Record 与 Codec (Java)

首先，编写您需要附带的数据结构（必须是 Java Record），并提供其序列化 Codec：

```java
package com.tutorial.tutorialmod.datamap;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;

// 示例：我们需要为物品绑定一个“红宝石价值”属性
public record RubyValue(int value) {
    public static final Codec<RubyValue> CODEC = RecordCodecBuilder.create(instance ->
            instance.group(
                    Codec.INT.fieldOf("value").forGetter(RubyValue::value)
            ).apply(instance, RubyValue::new)
    );
}
```

---

## 2. 声明并注册 DataMapType

数据映射需要在 **MOD 事件总线** 上订阅 `RegisterDataMapTypesEvent` 事件进行声明：

```java
package com.tutorial.tutorialmod.datamap;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.registries.datamaps.DataMapType;
import net.neoforged.neoforge.registries.datamaps.RegisterDataMapTypesEvent;

public class ModDataMaps {

    // 1. 创建 DataMapType 静态引用（指定关联注册表为 Registries.ITEM）
    public static final DataMapType<Item, RubyValue> RUBY_VALUES = DataMapType.builder(
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_values"),
            Registries.ITEM,
            RubyValue.CODEC
    ).build();

    // 2. 在 MOD 总线上订阅事件并执行注册
    @EventBusSubscriber(modid = TutorialMod.MODID)
    public static class Registrar {
        @SubscribeEvent
        public static void registerDataMaps(RegisterDataMapTypesEvent event) {
            event.register(RUBY_VALUES);
        }
    }
}
```

---

## 3. 在 Java 中查询挂载的值 (Query API)

一旦注册并提供了 JSON 映射，您可以在任意代码位置，通过 Registry Holder 安全地获取其绑定的静态值：

```java
package com.tutorial.tutorialmod.item;

import com.tutorial.tutorialmod.datamap.ModDataMaps;
import com.tutorial.tutorialmod.datamap.RubyValue;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.entity.player.Player;

public class RubyWandItem extends net.minecraft.world.item.Item {
    public RubyWandItem(Properties properties) {
        super(properties);
    }

    public void processItemValue(ItemStack stack, Player player) {
        // 1. 通过 item.builtInRegistryHolder() 获取物品的注册表 Holder
        // 2. 调用 .getData() 传入我们的 DataMapType 静态键值
        RubyValue data = stack.getItem().builtInRegistryHolder().getData(ModDataMaps.RUBY_VALUES);
        
        if (data != null) {
            int value = data.value();
            player.sendSystemMessage(net.minecraft.network.chat.Component.literal("Ruby value is: " + value));
        } else {
            // 代表该物品在数据包中没有任何 RubyValue 映射
        }
    }
}
```

---

## 4. 编写数据包映射 JSON 资源 (Datapack JSON)

数据映射采用纯数据驱动配置。您只需要在数据包的 `data_maps` 目录下，按照 `data_maps/<registry_path>/<map_name>.json` 的路径放置文件：

*   **物理路径**：`src/main/resources/data/tutorialmod/data_maps/item/ruby_values.json`
    *(注：因为关联的是 `Registries.ITEM`，所以中间目录是 `item`；如果是方块则是 `block`)*

```json
{
  "values": {
    "tutorialmod:ruby": {
      "value": 100
    },
    "minecraft:diamond": {
      "value": 80
    },
    "minecraft:coal": {
      "value": 5
    }
  }
}
```

### 💡 核心设计优势
1.  **无反射/快速检索**：数据映射会在游戏启动加载数据包时，由 NeoForge 批量解析并缓存至注册表对象内部，调用 `getData()` 为 `O(1)` 时间复杂度，完全没有性能损耗。
2.  **数据包重写与合并**：其他模组或服务器开发者可以通过自己的数据包，在 `data/othermod/data_maps/item/ruby_values.json` 中配置相同名字的文件，即可实现值的动态覆盖、添加或合并，完全解耦。


---

## 5. 使用数据生成器自动生成 Data Maps (DataGen)

除了手动编写 JSON 资源文件外，首选并推荐使用 NeoForge 的 **`DataMapProvider`** 通过数据生成器自动编译生成 JSON：

### 5.1 创建 DataMapProvider 类
```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.datamap.ModDataMaps;
import com.tutorial.tutorialmod.datamap.RubyValue;
import com.tutorial.tutorialmod.item.ModItems; // 示例自定义物品注册类
import net.minecraft.core.HolderLookup;
import net.minecraft.data.PackOutput;
import net.minecraft.world.item.Items;
import net.neoforged.neoforge.common.data.DataMapProvider;
import java.util.concurrent.CompletableFuture;

public class ModDataMapProvider extends DataMapProvider {

    public ModDataMapProvider(PackOutput packOutput, CompletableFuture<HolderLookup.Provider> lookupProvider) {
        super(packOutput, lookupProvider);
    }

    @Override
    protected void gather(HolderLookup.Provider provider) {
        // 使用 builder 链式注册各个物品的映射值
        this.builder(ModDataMaps.RUBY_VALUES)
                .add(ModItems.RUBY_ITEM.getId(), new RubyValue(100), false) // 第三个参数表示是否强制覆盖原有值 (replace)
                .add(Items.DIAMOND, new RubyValue(80), false)
                .add(Items.EMERALD, new RubyValue(120), false);
    }
}
```

### 5.2 在 GatherDataEvent 事件中注册 Provider
在您的 DataGen 订阅类中（或者主类的 Mod 总线监听器中）挂载它：

```java
@EventBusSubscriber(modid = TutorialMod.MODID)
public class DataGenerators {
    
    @SubscribeEvent
    public static void gatherData(GatherDataEvent event) {
        var generator = event.getGenerator();
        var packOutput = generator.getPackOutput();
        var lookupProvider = event.getLookupProvider();
        
        // 挂载 DataMapProvider
        generator.addProvider(
                event.includeServer(),
                new ModDataMapProvider(packOutput, lookupProvider)
        );
    }
}
```
通过 `gradlew runData` 命令即可一键自动输出至 `src/generated/resources/data/tutorialmod/data_maps/item/ruby_values.json` 物理文件，确保 100% 格式无误。
