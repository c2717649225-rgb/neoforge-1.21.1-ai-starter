# NeoForge 1.21.1 模组配置系统 (Mod Configuration) 开发指南

NeoForge 整合并扩展了原生的 **FML 模组配置系统**，允许我们通过编写 `ModConfigSpec` 构建类型安全、可自动生成、自动校验，并完美支持热重载（Hot-Reloading）的 `.toml` 配置文件。

---

## 1. 声明与构建配置规约 (`ModConfigSpec`)

为了让配置定义清晰、易维护，建议建立独立的 `Config` 类，使用 `ModConfigSpec.Builder` 进行链式声明。

通常，配置文件分为三种类型：
*   **COMMON**: 客户端和服务端共用（如方块属性、特定计算数值）。存储于 `config/<modid>-common.toml`。
*   **CLIENT**: 仅物理客户端生效（如 HUD 渲染偏好、声音大小、界面开关）。存储于 `config/<modid>-client.toml`。
*   **SERVER**: 存储于世界存档内（如特定世界规则、生成限制），会随联机同步至客户端。存储于 `saves/<world>/serverconfig/<modid>-server.toml`。

### 示例：创建 COMMON 配置类

```java
package com.tutorial.tutorialmod.config;

import net.neoforged.common.ModConfigSpec;
import java.util.List;

public class ModCommonConfig {
    // 1. 定义配置规约实例 (Spec)
    public static final ModConfigSpec SPEC;
    
    // 2. 声明具体的配置值持有容器 (使用 ModConfigSpec.ConfigValue 或特定子类型如 BooleanValue, DoubleValue 等)
    // 推荐在外部通过 Supplier 转换读取以确保热重载安全性
    public static final ModConfigSpec.BooleanValue LOG_DIRT_BLOCK;
    public static final ModConfigSpec.IntValue MAGIC_NUMBER;
    public static final ModConfigSpec.ConfigValue<String> MAGIC_NUMBER_INTRODUCTION;
    public static final ModConfigSpec.ConfigValue<List<? extends String>> BLACKLISTED_ITEMS;

    static {
        ModConfigSpec.Builder builder = new ModConfigSpec.Builder();

        // 3. 构建配置组 (可选，用于在 TOML 中进行分区注释与嵌套结构)
        builder.comment("Common settings for Tutorial Mod").push("common_settings");

        LOG_DIRT_BLOCK = builder
                .comment("Whether to log when a dirt block is checked in common setup")
                .define("logDirtBlock", true);

        MAGIC_NUMBER = builder
                .comment("A magic number used in tutorial logic")
                .comment("Min: 0, Max: 1000")
                .defineInRange("magicNumber", 42, 0, 1000);

        MAGIC_NUMBER_INTRODUCTION = builder
                .comment("The prefix text printed before the magic number")
                .define("magicNumberIntroduction", "The magic number is: ");
                
        BLACKLISTED_ITEMS = builder
                .comment("A list of registry names of items that are blacklisted")
                .defineListAllowEmpty("blacklistedItems", List.of("minecraft:bedrock"), o -> o instanceof String);

        builder.pop(); // 弹出当前组

        SPEC = builder.build(); // 构建生成最终 Spec
    }
}
```

---

## 2. 注册配置文件

在主模组类（如 `TutorialMod.java`）的构造函数中，将构建好的 Spec 注册给 `ModContainer`：

```java
package com.tutorial.tutorialmod;

import com.tutorial.tutorialmod.config.ModCommonConfig;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.fml.ModContainer;

@Mod(TutorialMod.MODID)
public class TutorialMod {
    public static final String MODID = "tutorialmod";

    public TutorialMod(IEventBus modEventBus, ModContainer modContainer) {
        // 注册通用配置 (COMMON)，系统会自动生成并读取 config/tutorialmod-common.toml
        modContainer.registerConfig(ModConfig.Type.COMMON, ModCommonConfig.SPEC);
        
        // 也可以用相同方式注册客户端/服务端配置
        // modContainer.registerConfig(ModConfig.Type.CLIENT, ModClientConfig.SPEC);
    }
}
```

---

## 3. 动态配置重载事件监听 (Config Events)

为了在游戏运行期间，玩家修改 `.toml` 文件保存后，模组能够**立即响应新配置**（例如重新刷新实体属性、重置内部变量缓存），我们需要在 **MOD 事件总线** 上订阅 `ModConfigEvent` 事件：

```java
package com.tutorial.tutorialmod.config;

import com.tutorial.tutorialmod.TutorialMod;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.fml.event.config.ModConfigEvent;

@EventBusSubscriber(modid = TutorialMod.MODID)
public class ConfigEventHandler {

    // 监听配置加载与重载事件 (ModConfigEvent.Loading 和 ModConfigEvent.Reloading)
    @SubscribeEvent
    public static void onConfigEvent(final ModConfigEvent event) {
        // 确认是本模组的配置文件被刷新了
        if (event.getConfig().getModId().equals(TutorialMod.MODID)) {
            TutorialMod.LOGGER.info("Configuration for Tutorial Mod has been loaded or reloaded!");
            
            // 示例：在配置变化时执行动态逻辑
            if (event instanceof ModConfigEvent.Reloading) {
                // 执行如重置缓存、更新客户端本地渲染映射等操作
                syncRuntimeValues();
            }
        }
    }
    
    private static void syncRuntimeValues() {
        // 读取新的值并应用到运行时系统
        int magicNumber = ModCommonConfig.MAGIC_NUMBER.get();
        // TutorialMod.LOGGER.info("Applied new magic number: {}", magicNumber);
    }
}
```
*注：`ModConfigEvent` 会在游戏启动加载（`Loading`）以及运行时文件保存（`Reloading`）时触发。*

---

## 4. ⚠️ 线程安全与 Supplier 封装规范

### 4.1 为什么要使用 Supplier
因为配置文件加载滞后于类的静态变量构造，且可以在游戏运行中被随时热重载。为了防止 AI 或开发者将配置项的值缓存为不可变的静态变量（这会导致配置修改后游戏内无法刷新数值），**必须在实际调用逻辑中使用 `configValue.get()` 读取，或者用 `Supplier` 封装**：

```java
// ❌ 错误示范：将配置读取死死锁在类的静态区
public static final int CACHED_NUMBER = ModCommonConfig.MAGIC_NUMBER.get(); // 游戏内修改 TOML 时此变量不会刷新！

//  正确示范：使用包装的 Supplier 动态读取
public static final java.util.function.Supplier<Integer> MAGIC_NUMBER_SUPPLIER = ModCommonConfig.MAGIC_NUMBER::get;
```

### 4.2 线程安全注意事项
*   `ModConfigSpec.ConfigValue` 的底层读写由 TOML 解析层处理，其 `get()` 方法本身在内存级别是线程安全的。
*   如果将配置值频繁应用于高频 Tick（如每 tick 判断是否扣除玩家能量），为了避免在主线程中由于大量调用解包而引起微小性能波动，您可以在 `ConfigEventHandler` 监听配置重载事件，将读取到的值存入类成员变量（如 `private static int activeMagicNumber`），在高频 tick 中读取此缓存变量，但在 `ModConfigEvent.Reloading` 触发时必须立刻同步更新它。
