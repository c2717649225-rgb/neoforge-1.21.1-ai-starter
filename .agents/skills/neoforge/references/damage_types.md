# NeoForge 1.21.1 自定义伤害类型 (Damage Types) 指南

在 Minecraft 1.20+ 和 1.21.1 中，伤害类型系统被彻底重构为**数据驱动（Data-driven）**的架构。原有的 `new DamageSource("bleeding")` 构造方法已被**完全移除**。

现在，所有的伤害类型必须通过 **JSON 配置文件**定义，在 Java 代码中声明 `ResourceKey` 进行引用，并利用动态注册表（RegistryAccess）构造伤害源。以下是实现自定义伤害类型（如无视护甲的“流血/真实伤害”）的完整指南。

---

## 1. 在 Java 中定义 ResourceKey

首先，在代码中声明对自定义伤害类型 JSON 文件的 ResourceKey 引用。该 Key 本身无需进行任何 Java 事件注册：

```java
package com.tutorial.tutorialmod.damage;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageType;

public class ModDamageTypes {
    // 声明指向 "tutorialmod:bleeding" 伤害类型的键值引用
    public static final ResourceKey<DamageType> BLEEDING = ResourceKey.create(
            Registries.DAMAGE_TYPE,
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "bleeding")
    );
}
```

---

## 2. 编写数据驱动 JSON 配置文件

您必须在模组资源目录下创建对应的 JSON 文件，以便游戏底层的注册表系统能够正确解析该伤害类型：

*   **文件路径**：`src/main/resources/data/tutorialmod/damage_type/bleeding.json`

```json
{
  "exhaustion": 0.1,
  "message_id": "bleeding",
  "scaling": "never"
}
```

### 属性详解
*   `message_id`：伤害的翻译标识符，用于在语言文件中配置死亡信息（例如 `death.attack.bleeding`）。
*   `exhaustion`：玩家受到此伤害时增加的饥饿度消耗值量（1.0F 相当于原版饥饿效果，0.1F 为微量）。
*   `scaling`：伤害如何随游戏难度（简单/普通/困难）进行缩放。可选值包括：
    *   `never`：伤害数值固定，不受难度影响（适合真实伤害/持续掉血）。
    *   `always`：伤害随难度比例缩放。
    *   `when_caused_by_living_non_player`：如果是怪物/非玩家生物造成的伤害，则随难度缩放。

---

## 3. 构造并触发伤害 (Deal Damage API)

由于伤害类型存储在动态注册表中，要对实体造成该伤害，必须通过当前世界（Level）的 `registryAccess()` 动态提取并构造伤害源实例：

```java
package com.tutorial.tutorialmod.util;

import com.tutorial.tutorialmod.damage.ModDamageTypes;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;

public class DamageUtil {

    // 对目标实体造成自定义流血伤害 (不包含攻击来源的纯环境伤害)
    public static void dealBleedingDamage(LivingEntity target, float amount) {
        // 1. 获取 Level 的动态伤害类型注册表
        Holder<DamageType> damageTypeHolder = target.level().registryAccess()
                .registryOrThrow(Registries.DAMAGE_TYPE)
                .getHolderOrThrow(ModDamageTypes.BLEEDING);

        // 2. 传入 Holder 构造 DamageSource
        DamageSource source = new DamageSource(damageTypeHolder);

        // 3. 对实体实施伤害
        target.hurt(source, amount);
    }

    // 对目标实体造成由攻击者触发的流血伤害 (包含攻击者源头，便于计算仇恨与击杀统计)
    public static void dealBleedingDamageFromAttacker(LivingEntity target, Entity attacker, float amount) {
        Holder<DamageType> damageTypeHolder = target.level().registryAccess()
                .registryOrThrow(Registries.DAMAGE_TYPE)
                .getHolderOrThrow(ModDamageTypes.BLEEDING);

        // 传入两个参数：伤害类型持有者，以及直接攻击源实体 (Direct Entity)
        DamageSource source = new DamageSource(damageTypeHolder, attacker);

        target.hurt(source, amount);
    }
}
```

---

## 4. 伤害标签与“真实伤害（无视护甲）”的实现

如果您希望让自定义伤害具备特殊的穿透判定（例如：**流血必须无视护甲、无视盾牌阻挡、或绕过抗性提升药水**），在 1.21.1 中**绝对禁止**在 Java 代码中强行写 `if` 判断计算，而必须使用原版的**伤害类型标签 (Damage Type Tags)**：

在您的资源文件夹下，为原版 **`minecraft`** 命名空间下的 Tag 追加您的自定义伤害 ID：

*   **实现无视护甲（真实伤害）**：
    *   **文件路径**：`src/main/resources/data/minecraft/tags/damage_type/bypasses_armor.json` (注意：命名空间必须是 **`minecraft`**，不能是 `tutorialmod`！)
    ```json
    {
      "replace": false,
      "values": [
        "tutorialmod:bleeding"
      ]
    }
    ```

*   **实现无视盾牌阻挡**：
    *   **文件路径**：`src/main/resources/data/minecraft/tags/damage_type/bypasses_shield.json`
    ```json
    {
      "replace": false,
      "values": [
        "tutorialmod:bleeding"
      ]
    }
    ```

*   **实现无视抗性提升药水Buff (如虚空伤害/饥饿伤害)**：
    *   **文件路径**：`src/main/resources/data/minecraft/tags/damage_type/bypasses_effects.json`
    ```json
    {
      "replace": false,
      "values": [
        "tutorialmod:bleeding"
      ]
    }
    ```

---

## 5. 配置死亡信息本地化

在语言文件中为您的 `message_id` 添加翻译文本，以支持完美的死亡屏幕信息展示：

*   **英文文件 (en_us.json)**：
    ```json
    {
      "death.attack.bleeding": "%1$s bled to death",
      "death.attack.bleeding.player": "%1$s bled to death whilst fighting %2$s"
    }
    ```
    * `%1$s` 代表受害者，`%2$s` 代表击杀该玩家的攻击源实体。
*   **中文文件 (zh_cn.json)**：
    ```json
    {
      "death.attack.bleeding": "%1$s 因失血过多而死",
      "death.attack.bleeding.player": "%1$s 在与 %2$s 战斗时因失血过多而死"
    }
    ```
