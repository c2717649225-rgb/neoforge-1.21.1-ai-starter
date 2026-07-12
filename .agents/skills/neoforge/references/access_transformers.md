# NeoForge 1.21.1 访问转换器 (Access Transformers) 指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


在 Minecraft 模组开发中，如果需要访问、调用或重写原版类（Vanilla Classes）中的 `private` 或 `protected` 字段与方法，最底层、最直接且最高效的方式是使用**访问转换器 (Access Transformers, 简称 AT)**。

访问转换器在游戏启动阶段通过字节码转换，直接将目标字段/方法/类改为 `public` 或移除非 final（`non-final`）限制，从而避免使用开销巨大的 Java 反射。

---

## 1. 配置文件路径与生命周期

在 NeoForge 1.21.1 中，访问转换器配置文件的命名和位置有着严格的要求，放置错误会导致构建或运行游戏时完全失效：

*   **物理路径**：`src/main/resources/META-INF/neoforge.accesstransformer.cfg`
*   **启用配置**：NeoForge 1.21.1 默认会自动检索并解析 `META-INF/neoforge.accesstransformer.cfg`。如果使用的是标准 MDK，无需在 `build.gradle` 中做额外配置。若未生效，可检查 `build.gradle` 中是否有类似以下配置：
    ```groovy
    subprojects {
        // 确保 accessTransformer 被作为资源文件引用
    }
    ```

---

## 2. 语法规则与指令定义

AT 配置文件使用以空格分隔的纯文本格式，支持四种基本指令。

### 2.1 规则格式

| 目标类型 | 访问修饰符修改 | 移除非 final 限制 (变为可修改) |
| :--- | :--- | :--- |
| **类 (Class)** | `public <ClassName>` | `public-f <ClassName>` |
| **字段 (Field)** | `public <ClassName> <fieldName>` | `public-f <ClassName> <fieldName>` |
| **方法 (Method)** | `public <ClassName> <methodName>(<Params>)<Return>` | `public-f <ClassName> <methodName>(<Params>)<Return>` |

*注：若仅需保留原有 protected 权限但去除 final 限制，可使用 `protected-f`。*

### 2.2 语法详解与通配规则

*   **类名**：必须使用**带包名的全限定名**（如 `net.minecraft.world.entity.LivingEntity`），内嵌类（Inner Class）使用 `$` 符号连接（如 `net.minecraft.world.entity.ai.goal.AvoidEntityGoal$AvoidMercenary`）。
*   **字段名**：使用 Mojang 官方映射对应的真实名字。
*   **方法描述符**：方法必须写明完整的 JVM 签名（包括参数列表和返回值类型），不可包含多余的空格。
*   **注释**：使用 `#` 标识单行注释。

---

## 3. 经典开发场景示例 (Typical Use Cases)

以下是开发中经常需要通过 AT 暴露的原版底层接口：

```properties
# -------------------------------------------------------------
# 1. 暴露原版类（使其可以被直接继承或实例化）
# -------------------------------------------------------------
# 将原版躲避实体 AI 目标中的非公有内部类暴露给外包继承
public net.minecraft.world.entity.ai.goal.AvoidEntityGoal$AvoidMercenary

# -------------------------------------------------------------
# 2. 暴露原版类字段（直接读写，避免每 tick 调用的反射开销）
# -------------------------------------------------------------
# 暴露 LivingEntity 中的“最近受击来源实体”字段 (revengeEntity)
public net.minecraft.world.entity.LivingEntity revengeEntity

# 暴露 LivingEntity 中的“最近伤害来源时间”字段 (lastHurtByPlayerTime)
public net.minecraft.world.entity.LivingEntity lastHurtByPlayerTime

# 暴露 FoodData 玩家饥饿度管理类中的“当前饥饿值”字段 (foodLevel)
public-f net.minecraft.world.food.FoodData foodLevel

# -------------------------------------------------------------
# 3. 暴露原版类方法（直接调用或覆写）
# -------------------------------------------------------------
# 暴露 LivingEntity 中的“计算坠落伤害”方法
public net.minecraft.world.entity.LivingEntity calculateFallDamage(FZ)I

# 暴露 Mob 中的“根据装备插槽获取物品”的底层修改方法
public net.minecraft.world.entity.Mob setItemSlotAndDropWhenDisabled(Lnet/minecraft/world/entity/EquipmentSlot;Lnet/minecraft/world/item/ItemStack;)Lnet/minecraft/world/item/ItemStack;
```

### 💡 避坑指南：如何获取正确的方法 JVM 签名？
在 IDE 中（如 IntelliJ IDEA），您可以右键原版方法的声明，选择 **"Copy" -> "Copy Reference"** 或者使用字节码查看器直接获取其 descriptor 签名。
常见的类型映射关系对照：
*   `I` ➔ `int`
*   `Z` ➔ `boolean`
*   `F` ➔ `float`
*   `D` ➔ `double`
*   `V` ➔ `void`
*   `Lnet/minecraft/world/item/ItemStack;` ➔ `ItemStack` 对象类型（注意以 `L` 开头，以分号 `;` 结尾）

---

## 4. 冲突解决：AT 与 Mixin 的合理选型

许多初学者混淆了 Access Transformers 和 Mixin 的应用场景，导致项目架构臃肿：

*   **什么时候用 AT**：
    *   只需要将某个 `private` 方法公开以供自己的类直接调用。
    *   需要直接修改某个 vanilla 变量的值。
    *   **原则**：只改访问控制权限，不改动原有逻辑。
*   **什么时候用 Mixin**：
    *   需要在原版方法的开头、中间或返回处**插入自己的逻辑（如条件拦截、注入事件）**。
    *   需要拦截并替换（Redirect）原版方法内部调用的其他方法。
    *   **原则**：需要改变游戏原有运行逻辑时使用。