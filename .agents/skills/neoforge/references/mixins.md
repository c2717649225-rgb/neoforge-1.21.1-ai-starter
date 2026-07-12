# Minecraft 1.21.1 Mixin 字节码注入系统参考指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


**Mixin** 是一种在运行时动态修改 Minecraft 原版（或其它依赖模组）已编译类字节码的机制。它是修改游戏原版行为、注入自定义逻辑的必由之路。

在 1.21.1 中，项目采用 **Mojang 官方映射 (Mojang Mappings)**，混淆名与方法名均使用 Mojang 官方命名。

---

## 1. 基础配置与挂载

### 1.1 在 `neoforge.mods.toml` 模板中激活 Mixin 配置
由于 NeoForge 1.21.1 采用模板热重载生成元数据，您**绝对不能直接修改 `src/main/resources/META-INF/neoforge.mods.toml`**。
必须修改位于模组模板目录下的 `src/main/templates/META-INF/neoforge.mods.toml`（或 MDK 指定的模板路径），在文件尾部将 Mixin 模板的注释符号（`#`）去掉，并**必须保留 `${mod_id}` 变量占位符**：

```toml
[[mixins]]
config = "${mod_id}.mixins.json"
```
*注：Gradle 的 `generateModMetadata` 任务会在编译时自动将 `${mod_id}` 替换为真实的 ModID（如 `tutorialmod.mixins.json`），强行写死会导致多项目编译时元数据脱节。*

### 1.2 新建 Mixin 配置文件 (`tutorialmod.mixins.json`)
在 `src/main/resources/` 目录下新建 `tutorialmod.mixins.json`。必须在文件中声明 `refmap` 属性，以便在编译打包时自动生成混淆映射：
```json
{
  "required": true,
  "minVersion": "0.8",
  "package": "com.tutorial.tutorialmod.mixin",
  "compatibilityLevel": "JAVA_21",
  "refmap": "tutorialmod.refmap.json",
  "mixins": [
    "CreeperMixin",
    "ItemMixin"
  ],
  "client": [],
  "injectors": {
    "defaultRequire": 1
  }
}
```

### 1.3 `build.gradle` 配置说明 (ModDevGradle 2.0)
在 NeoForge 1.21.1 采用的 **ModDevGradle 2.0** 构建体系下，你**完全不需要**在 `build.gradle` 中声明 `mixin {}` 闭包或引入外部 MixinGradle 插件。ModDevGradle 会自动处理 Mixins 和 Refmap 的生成。

> [!WARNING]
> **绝对禁止手动声明 Mixin 注解处理器**：
> 在 `build.gradle` 的 `dependencies` 中，**绝对不能**手动添加 `annotationProcessor 'org.spongepowered:mixin:...'` 或者是 `net.fabricmc:sponge-mixin` 的 AP。MDG 2.x 已经内置了 Mixin 编译器插件，并自动配置了 Mojang 映射。如果手动添加，旧的 AP 会顶替内置 AP 导致所有的 `@Inject`、`@Shadow` 找不到 Mojang 映射，编译时疯狂报 `Unable to locate obfuscation mapping`。


---

## 2. 常用 Mixin 注解与编程规范

所有的 Mixin 类都必须放在上面配置文件中指定的 `package` 包下（即 `com.tutorial.tutorialmod.mixin`）。

### 2.1 `@Inject` 基础拦截 (拦截 Void 方法并注入逻辑)
用于在方法开头 (`HEAD`)、结尾 (`TAIL`) 或特定调用处注入逻辑。

**示例**：拦截苦力怕的 `tick()` 方法，使其在特定条件下立刻爆炸。
```java
package com.tutorial.tutorialmod.mixin;

import net.minecraft.world.entity.monster.Creeper;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(Creeper.class)
public abstract class CreeperMixin {

    // 1. 使用 @Shadow 引用目标类中的私有字段或方法
    @Shadow private int swell;
    @Shadow private int maxSwell;
    @Shadow public abstract void ignite();

    // 2. 拦截 Creeper 的 tick()V 方法
    // target 为混淆的方法名，1.21.1 采用 Mojang 官方命名，方法参数为 void 时可缩写为 "tick"
    @Inject(method = "tick", at = @At("HEAD"))
    private void onTick(CallbackInfo ci) {
        Creeper creeper = (Creeper) (Object) this; // 获取当前 Creeper 实例
        
        // 逻辑：如果苦力怕处于水里，让它立刻引燃
        if (creeper.isInWater()) {
            this.ignite();
            // 如果要彻底拦截并中断原方法的后续执行（仅限 cancellable = true 的注入）：
            // ci.cancel();
        }
    }
}
```

### 2.2 `@Inject` 拦截带返回值的方法并修改返回值 (`CallbackInfoReturnable`)
常用于修改原版物品属性、玩家抗性等。

**示例**：让所有铁制工具/防具在渲染时带上附魔的“闪烁光泽 (Glint)”。
```java
package com.tutorial.tutorialmod.mixin;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Item.class)
public class ItemMixin {

    // 拦截 isFoil(Lnet/minecraft/world/item/ItemStack;)Z 方法（即物品是否闪烁）
    // target 签名必须写全。cancellable = true 允许我们返回自定义结果
    @Inject(method = "isFoil", at = @At("HEAD"), cancellable = true)
    private void onIsFoil(ItemStack stack, CallbackInfoReturnable<Boolean> cir) {
        Item item = (Item) (Object) this;
        
        // 逻辑：如果是铁剑或铁甲，直接强制返回 true，使其有附魔闪光效果
        if (stack.is(Items.IRON_SWORD) || stack.is(Items.IRON_CHESTPLATE)) {
            cir.setReturnValue(true); // 拦截并返回 true
        }
    }
}
```

### 2.3 `@Redirect` 重定向方法调用 (危险操作，慎用)
用于将原版代码中的某一个方法调用重定向为您自定义的方法。因为如果有多个模组对同一个地方进行 `@Redirect`，会导致**严重的模组冲突**。

优先推荐使用 `@Inject` 或 `@ModifyVariable`，只有在必须彻底接管原版某个方法内部的子方法调用时才使用 `@Redirect`。

---

## 3. 避坑指南与最佳实践

1. **混淆签名定位**：
   * 1.21.1 采用官方混淆，方法名与参数签名必须使用 Mojang 官方命名。
   * 可以查阅反编译代码或利用本地 MCP 工具 `search_class` 与 `read_class` 来精确获取方法签名（例如：`hurt(Lnet/minecraft/world/damagesource/DamageSource;F)Z`）。
2. **`CallbackInfo` 引入错误**：
   * 方法返回值是 `void` 的，必须使用 `CallbackInfo`；
   * 方法有具体返回值的，必须使用 `CallbackInfoReturnable<T>`（T 为包装类，如 `Boolean`、`Integer`）。如果写错，游戏启动时会直接崩溃报 `Invalid Injector`。
3. **保持 Mixin 最小改动**：
   * 尽量只在 Mixin 中插入事件派发（如 `NeoForge.EVENT_BUS.post(event)`)，然后通过正常的事件监听器去处理具体业务逻辑。这样做冲突概率最小，代码最易维护。

---

## 4. 高级 Mixin 应用：@Accessor（访问器）与 @Invoker（调用器）

在模组开发中，很多时候你需要从外部强行获取原版类中的某一个私有字段（`@Accessor`）或者强行调用其内部的一个私有方法（`@Invoker`）。

### 4.1 接口混合模式（标准解耦实践）

**硬性红线**：绝对不能直接把 `@Accessor`/`@Invoker` 写在 Mixin 类内部然后试图在普通业务类中去 `import` 它。因为 Mixin 类属于运行时动态编织，编译期无法直接被常规 Java 类引入，否则会导致 `ClassNotFound` 或编译未定义的报错。

**正确范式**：
1. **新建普通 Java 接口**：声明用于暴露的 getter/setter 或调用方法。
2. **使 Mixin 类实现该接口**：在 Mixin 类的 `@Accessor` 或 `@Invoker` 方法上覆写该接口方法。
3. **业务层强转使用**。

#### 步骤一：创建普通的业务接口
```java
package com.tutorial.tutorialmod.mixin.accessor;

public interface MobEntityAccessorInterface {
    // 暴露 Mob 类中私有字段 doingEntityTick
    boolean getDoingEntityTick();
}
```

#### 步骤二：编写 Mixin 类实现该接口并绑定访问器
```java
package com.tutorial.tutorialmod.mixin;

import com.tutorial.tutorialmod.mixin.accessor.MobEntityAccessorInterface;
import net.minecraft.world.entity.Mob;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(Mob.class)
public abstract class MobMixin implements MobEntityAccessorInterface {

    // 绑定 Mob 中的私有变量 "doingEntityTick"
    @Accessor("doingEntityTick")
    @Override
    public abstract boolean getDoingEntityTick();
}
```

#### 步骤三：在业务逻辑中强转对象并调用
```java
Mob mob = ...;
// 直接将目标类强转为我们定义的接口类型，即可安全、无反射开销地读取私有字段！
boolean isTicking = ((MobEntityAccessorInterface) mob).getDoingEntityTick();
```

---

## ⚠️ 1.21.1 Mixin 常见编译错误与自愈

*   **编译报错**：`Unable to locate obfuscation mapping for @Inject / @Shadow target ...`
    *   ❌ 错误 1：在 `build.gradle` 中声明了手动的注解处理器 AP（见 1.3 节），这会导致 Mojang 映射查找失效。
    *   ❌ 错误 2：`@Mixin` 或者是 `@Inject` 定位的方法不处于该类的**实际声明类**中。例如：试图对 `LivingEntity` 进行 `@Mixin`，并在其中 `@Inject` 方法 `heal(F)V`。因为 `heal` 实际定义在父类 `Entity` 里，`LivingEntity` 本身并没有覆盖此方法。
    *   ✅ 修正：删除 `build.gradle` 手动 AP 引用；且 `@Mixin` 的目标类必须是该方法的实际声明类。如果要在子类截获，应该 Mixin 它的声明父类并用 `instanceof` 判断。
*   **编译报错**：`InvalidMixinException: Added field ... must be private`
    *   ❌ 错误：在 Mixin 类中编写了没有被 `@Shadow` 标记的 `public` 或 `protected` 静态/非静态新字段或辅助方法。
    *   ✅ 修正：在 Mixin 中声明的任何全新字段和辅助方法，**必须**使用 `private` 修饰符（防止多模组字节码合并时名字冲突）。
*   **编译报错**：`cannot find symbol: method priority() location: @Inject`
    *   ❌ 错误：在 `@Inject` 注解中添加了 `priority = 1000`。
    *   ✅ 修正：`@Inject` 注解没有 priority 属性！优先级属性只属于类注解 `@Mixin`，或者是 `@Inject` 内部的 `order` 属性。
*   **编译报错**：`remap = true target not found` (在重写非原版/扩展接口方法时)
    *   ❌ 错误：对 Forge/NeoForge 扩展的自定义非混淆方法（或者是三方 API）使用默认的 `@Inject`。
    *   ✅ 修正：默认情况下 `@Inject` 的 `remap` 属性为 `true`（要求 AP 去 Mojang 映射表查找其混淆前身）。对于本来就没有混淆的 NeoForge 特有方法，必须显式声明 `@Inject(..., remap = false)`。
