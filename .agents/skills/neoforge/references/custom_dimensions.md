# NeoForge 1.21.1 自定义维度 (Dimensions) 指南

在 Minecraft 中，添加类似“下界”、“末地”或全新的冒险维度（如暮色森林），其物理环境和规则的注册已完全由**数据驱动（Data-driven）**的 JSON 接管。

Java 代码现在只负责**注册对应的 ResourceKey（资源键）**，以及执行玩家传送等业务逻辑。

---

## 1. 声明维度 ResourceKey (Java)

首先，在 Java 代码中注册指向自定义维度的 ResourceKey。维度由 `Dimension` 本身与 `DimensionType`（维度类型，即维度的规则配置）组成：

```java
package com.tutorial.tutorialmod.worldgen.dimension;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.dimension.DimensionType;

public class ModDimensions {
    // 1. 声明世界级别键（Level Key，类似于 Level.OVERWORLD）
    public static final ResourceKey<Level> RUBY_DIM_KEY = ResourceKey.create(
            Registries.DIMENSION,
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_dimension")
    );

    // 2. 声明维度类型定义键 (Dimension Type Key)
    public static final ResourceKey<DimensionType> RUBY_DIM_TYPE = ResourceKey.create(
            Registries.DIMENSION_TYPE,
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_dim_type")
    );
}
```

---

## 2. 编写维度类型 JSON (Dimension Type)

维度类型文件定义了该维度的物理环境属性（如是否有昼夜交替、是否有床爆炸、重力如何、天空亮度如何）：

*   **文件路径**：`src/main/resources/data/tutorialmod/dimension_type/ruby_dim_type.json`

```json
{
  "ultrawarm": false,
  "natural": true,
  "coordinate_scale": 1.0,
  "has_skylight": true,
  "has_ceiling": false,
  "ambient_light": 0.0,
  "fixed_time": 6000,
  "monster_spawn_light_level": 0,
  "monster_spawn_block_light_limit": 0,
  "piglin_safe": false,
  "bed_works": true,
  "respawn_anchor_works": false,
  "has_raids": true,
  "logical_height": 384,
  "height": 384,
  "min_y": -64,
  "infiniburn": "#minecraft:infiniburn_overworld",
  "effects": "minecraft:overworld"
}
```

### 属性详解
*   `natural`：是否是自然维度。如果是，则指南针能正常指向南方，床可以正常睡觉不会爆炸。
*   `fixed_time`：若填入具体数值（如 `6000`），则该维度的时间会永远锁定在中午，不会有昼夜交替。不填则有昼夜循环。
*   `ambient_light`：环境光照亮度。`0.0` 是主世界模式（无光处漆黑），`1.0` 是下界/末地模式（没有光源也能看清周围）。
*   `effects`：天空背景和雾效渲染渲染方案。常用有 `minecraft:overworld`（主世界天空和天气）、`minecraft:the_nether`（下界红色雾气）、`minecraft:the_end`（末地紫色天空）。

---

## 3. 编写维度实例 JSON (Dimension)

维度实例文件定义了该维度使用的是什么维度类型、使用的是什么世界生成器（Chunk Generator）、以及有哪些生物群系（Biomes）：

*   **文件路径**：`src/main/resources/data/tutorialmod/dimension/ruby_dimension.json`

```json
{
  "type": "tutorialmod:ruby_dim_type",
  "generator": {
    "type": "minecraft:noise",
    "settings": "minecraft:overworld",
    "biome_source": {
      "type": "minecraft:multi_noise",
      "biomes": [
        {
          "biome": "minecraft:plains",
          "parameters": {
            "temperature": 0.0,
            "humidity": 0.0,
            "continentalness": 0.0,
            "erosion": 0.0,
            "depth": 0.0,
            "weirdness": 0.0,
            "offset": 0.0
          }
        }
      ]
    }
  }
}
```

### 属性详解
*   `type`：指向我们在第二步声明的维度类型（`tutorialmod:ruby_dim_type`）。
*   `generator`：地图生成器。通常使用 `minecraft:noise`（原版噪声发生器，用于生成类似主世界的地形）。
*   `settings`：生成设置。如使用 `minecraft:overworld` 生成常规地表，使用 `minecraft:nether` 生成洞穴地狱，使用 `minecraft:caves` 生成纯地下洞穴世界。
*   `biome_source`：生物群系来源。这里使用了最基础的 `multi_noise`，并将整个维度全部填充满 `minecraft:plains`（平原群系）以作为最简结构。

---

## 4. 传送玩家至自定义维度 (Java Teleportation API)

在 Java 中，如果需要通过传送门或右键道具让玩家在不同维度穿梭，必须利用服务端的 `changeDimension` 方法进行维度调度：

```java
package com.tutorial.tutorialmod.worldgen.dimension;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;

public class TeleportUtil {

    public static void teleportToRubyDimension(ServerPlayer player) {
        // 1. 获取当前玩家所处服务器实例
        net.minecraft.server.MinecraftServer server = player.getServer();
        if (server == null) {
            return;
        }

        // 2. 根据我们定义的 ResourceKey 获取服务端的维度世界对象 (ServerLevel)
        ServerLevel destination = server.getLevel(ModDimensions.RUBY_DIM_KEY);

        if (destination != null) {
            // 3. 1.21.1 核心：构建维度切换过渡参数 (DimensionTransition)
            // 传入目标世界、目标位置 (Vec3)、移动向量 (Vec3)、偏航角 (float)、俯仰角 (float)、是否作为乘客 (boolean)、以及传送后回调动作
            net.minecraft.world.level.portal.DimensionTransition transition = new net.minecraft.world.level.portal.DimensionTransition(
                    destination,
                    player.position(),
                    player.getDeltaMovement(),
                    player.getYRot(),
                    player.getXRot(),
                    false,
                    net.minecraft.world.level.portal.DimensionTransition.DO_NOTHING
            );

            // 4. 执行传送
            player.changeDimension(transition);
        }
    }
}
```
通过这种**JSON定义物理规则 -> Java调用Teleport接口**的开发方式，你可以极其轻松地将玩家传送到任何自定义的冒险维度中。
