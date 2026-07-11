# NeoForge 1.21.1 自定义生物群系 (Biomes) 指南

在 Minecraft 1.20+ 和 1.21.1 中，**自定义生物群系 (Biomes)** 同样完全通过数据包下的 **JSON 配置文件**进行定义。

Java 代码只负责在需要引用该群系时定义其 `ResourceKey<Biome>`。

---

## 1. 在 Java 中声明群系 ResourceKey

```java
package com.tutorial.tutorialmod.worldgen.biome;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.biome.Biome;

public class ModBiomes {
    // 声明指向 "tutorialmod:ruby_forest" 生物群系的注册键
    public static final ResourceKey<Biome> RUBY_FOREST = ResourceKey.create(
            Registries.BIOME,
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_forest")
    );
}
```

---

## 2. 编写生物群系 JSON 配置文件

生物群系文件控制了该群系的环境色调（雾色、草色、水色、天空色）、气候条件（温度、降雨）、生成的结构和植物特征、以及自然繁衍的生物。

*   **文件路径**：`src/main/resources/data/tutorialmod/worldgen/biome/ruby_forest.json`

```json
{
  "has_precipitation": true,
  "temperature": 0.7,
  "downfall": 0.8,
  "temperature_modifier": "none",
  "effects": {
    "fog_color": 16738431,
    "water_color": 4159204,
    "water_fog_color": 329011,
    "sky_color": 8103167,
    "foliage_color": 16711808,
    "grass_color": 16724838,
    "mood_sound": {
      "sound": "minecraft:ambient.cave",
      "tick_delay": 6000,
      "block_search_extent": 8,
      "offset": 2.0
    }
  },
  "spawners": {
    "monster": [
      {
        "type": "minecraft:zombie",
        "weight": 100,
        "minCount": 1,
        "maxCount": 4
      }
    ],
    "creature": [
      {
        "type": "minecraft:wolf",
        "weight": 8,
        "minCount": 2,
        "maxCount": 4
      }
    ],
    "ambient": [],
    "underground_water_creature": [],
    "water_creature": [],
    "water_ambient": [],
    "axolotls": []
  },
  "spawn_costs": {},
  "carvers": {
    "air": [
      "minecraft:cave",
      "minecraft:canyon"
    ]
  },
  "features": [
    [],
    [
      "minecraft:lake_lava_underground",
      "minecraft:lake_lava_surface"
    ],
    [],
    [],
    [],
    [],
    [
      "minecraft:ore_dirt",
      "minecraft:ore_gravel",
      "minecraft:ore_coal_upper",
      "minecraft:ore_iron_middle"
    ],
    [],
    [],
    [],
    []
  ]
}
```

---

## 3. 核心属性详解与配色进制转换

*   **降雨与气候**：
    *   `has_precipitation`：是否会下雨/下雪。
    *   `temperature`：温度。如果低于 `0.15` 会下雪且水会结冰；如果温度为 `0.7` 则会降下正常的雨水。
*   **配色配置（十进制颜色编码）**：
    *   在 JSON 中，所有的颜色属性（`fog_color` 雾色、`water_color` 水色、`sky_color` 天空色、`foliage_color` 树叶色、`grass_color` 草色）**必须使用 24位 RGB 颜色的十进制数值**表示。
    *   *计算方法*：将十六进制的 RGB 颜色转换为十进制。例如：
        *   红色 `#FF0000` -> 十进制值为 `16711680`。
        *   绿色 `#00FF00` -> 十进制值为 `65280`。
        *   红宝石叶片偏粉色 `#FFA0FF` -> 十进制值为 `16752895`。
*   **生物衍生 (`spawners`)**：
    *   将该群系专属的生态系统分类声明（`monster` 敌对、`creature` 动物、`ambient` 蝙蝠等环境生物）配置在此处，游戏将自动进行常规刷怪循环。
*   **世界生成特征映射 (`features`)**：
    *   列表按从 0 到 10 的阶段排列，控制矿石生成、树木生成、遗迹生成。例如在阶段 6 (`underground_ores`) 追加我们配置的 Placed Feature 矿石，或者在阶段 9 (`vegetal_decoration`) 放入自定义的树木以进行地形美化。
