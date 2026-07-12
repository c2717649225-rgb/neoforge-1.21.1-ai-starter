# NeoForge 1.21.1 自定义世界生成 (Worldgen) 矿石生成指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


在 Minecraft 1.20+ 和 1.21.1 中，所有的世界生成（包括矿石、植被、结构）均由**数据驱动（Data-driven）**控制。Java 代码中直接操作生成逻辑的方法已被**彻底废除**。

若要让模组注册的自定义矿石在主世界或下界自然生成，必须配置一套完整的数据 JSON 链条：**Configured Feature (配置特征) -> Placed Feature (放置特征) -> Biome Modifier (群系修改器)**。

---

## 1. 第一步：定义配置特征 (Configured Feature)

配置特征用于定义**“生成什么物品”**。例如矿脉的方块类型、矿脉大小、以及它们可以替换原版的哪些方块（如石头或深板岩）：

*   **文件路径**：`src/main/resources/data/tutorialmod/worldgen/configured_feature/ruby_ore.json`

```json
{
  "type": "minecraft:ore",
  "config": {
    "discard_chance_on_air_exposure": 0.0,
    "size": 9,
    "targets": [
      {
        "state": {
          "Name": "tutorialmod:ruby_ore"
        },
        "target": {
          "predicate_type": "minecraft:tag_match",
          "tag": "minecraft:stone_ore_replaceables"
        }
      },
      {
        "state": {
          "Name": "tutorialmod:deepslate_ruby_ore"
        },
        "target": {
          "predicate_type": "minecraft:tag_match",
          "tag": "minecraft:deepslate_ore_replaceables"
        }
      }
    ]
  }
}
```

### 属性详解
*   `size`：矿脉的大小（最大包含的方块数量，这里设为 9）。
*   `discard_chance_on_air_exposure`：当矿石暴露在空气中时被舍弃不生成的概率（0.0 代表完全不舍弃，适合普通矿石；若设为 0.5，则有一半暴露在洞穴空气中的矿石会变成石头，适合煤矿等）。
*   `targets`：目标替换规则列表。
    *   `state`：生成的模组矿石方块。
    *   `target`：检测被替换的原版方块标签。`stone_ore_replaceables`（石头、安山岩、闪长岩等）和 `deepslate_ore_replaceables`（深板岩、凝灰岩）。

---

## 2. 第二步：定义放置特征 (Placed Feature)

放置特征用于定义**“如何分布、层高范围”**。例如每区块生成多少次、层高范围以及生成高度的拉伸模式：

*   **文件路径**：`src/main/resources/data/tutorialmod/worldgen/placed_feature/ruby_ore_placed.json`

```json
{
  "feature": "tutorialmod:ruby_ore",
  "placement": [
    {
      "type": "minecraft:count",
      "count": 8
    },
    {
      "type": "minecraft:in_square"
    },
    {
      "type": "minecraft:height_range",
      "height": {
        "type": "minecraft:trapezoid",
        "max_inclusive": {
          "absolute": 80
        },
        "min_inclusive": {
          "absolute": -64
        }
      }
    },
    {
      "type": "minecraft:biome"
    }
  ]
}
```

### 属性详解
*   `feature`：指向我们第一步定义的 Configured Feature（`tutorialmod:ruby_ore`）。
*   `placement`：放置规则过滤器列表。
    *   `minecraft:count`：每区块（16x16）尝试生成该矿脉的次数（这里为 8 次）。
    *   `minecraft:in_square`：在区块的水平 X 和 Z 轴上进行随机散布。
    *   `minecraft:height_range`：生成的高度（Y 轴）区间。
        *   `minecraft:trapezoid`：**梯形/三角拉伸分布**（最常用）。Y 轴高度在 `min_inclusive`（-64层）和 `max_inclusive`（80层）之间，其中**正中间层数（Y = 8）生成概率最高**，越靠近边界概率越低。
        *   若需要均匀分布（如铁矿），将 type 改为 `minecraft:uniform`。
    *   `minecraft:biome`：群系过滤器，确保矿石只在当前群系允许的规则下生成（非空区块除外）。

---

## 3. 第三步：定义群系修改器 (Biome Modifier)

在 NeoForge 中，要将我们的 Placed Feature 正式放入世界生成管线中，必须定义一个 Biome Modifier。

> [!WARNING]
> **新版命名空间与类型红线**：
> 在 1.21.1 NeoForge 中，文件夹路径必须存放在 **`neoforge/biome_modifier/`** 命名空间下。修改器的 type 类型也已正式由 Forge 版的 `forge:add_features` 升级为了 **`neoforge:add_features`**。如果放错位置或写错类型，游戏将直接无视此生成规则。

*   **文件路径**：`src/main/resources/data/tutorialmod/neoforge/biome_modifier/add_ruby_ore.json`

```json
{
  "type": "neoforge:add_features",
  "biomes": "#minecraft:is_overworld",
  "features": "tutorialmod:ruby_ore_placed",
  "step": "underground_ores"
}
```

### 属性详解
*   `type`：必须是 **`neoforge:add_features`**。
*   `biomes`：指定在哪些群系生成。可以使用群系标签，例如 `#minecraft:is_overworld` 代表所有主世界群系，或者 `#minecraft:is_nether`（下界）、`#minecraft:is_end`（末地）。也可以传入包含多个群系 ID 的列表。
*   `features`：指向我们第二步定义的 Placed Feature（`tutorialmod:ruby_ore_placed`）。
*   `step`：定义在世界的哪一个阶段生成。矿石固定为 **`underground_ores`**（地下矿石阶段）。（如果是自定义花草树木，则为 `vegetal_decoration`）。