# NeoForge & Fabric 跨平台接口解耦 (ServiceLoader) 范例

如果您规划让模组项目在未来能够以最低的代码修改代价移植至 **Fabric** 平台，必须在通用业务逻辑中**严禁直接调用加载器独有的 API**（例如：在核心逻辑中直接调用 `Level.getCapability()` 获取能量，或者直接触发 NeoForge 的 `PacketDistributor` 发送网络包）。

推荐采用原版和大型模组通用的 **Java 服务加载器 (ServiceLoader) 模式**，将平台相关的独有操作抽象隔离。

---

## 1. 架构示意图 (Architecture)

```
                     ┌────────────────────────┐
                     │     Common (通用层)     │
                     │  - IPlatformHelper     │ <── 核心逻辑在此调用接口
                     │  - Services (加载类)    │
                     └────────────────────────┘
                                 ▲
          ┌──────────────────────┴──────────────────────┐
          │                                             │
┌───────────────────┐                         ┌───────────────────┐
│  NeoForge (实现层) │                         │   Fabric (实现层)  │
│  - NeoForgeHelper │                         │  - FabricHelper   │
└───────────────────┘                         └───────────────────┘
```

---

## 2. 编写通用接口与静态入口 (Common Layer)

在通用代码包（Common）中定义平台相关行为的底层契约接口，并创建一个统一获取服务的静态引导类：

### 2.1 定义平台服务契约接口 (`IPlatformHelper`)
*   **代码位置**：`com/tutorial/tutorialmod/platform/services/IPlatformHelper.java`

```java
package com.tutorial.tutorialmod.platform.services;

public interface IPlatformHelper {
    
    // 1. 获取当前是否运行在客户端
    boolean isClient();

    // 2. 检查某个模组 ID 是否已经加载 (NeoForge 与 Fabric 获取模组列表的 API 截然不同)
    boolean isModLoaded(String modId);
    
    // 3. 通用能量/附件获取桥接方法 (解耦 getCapability() / BlockApiLookup())
    // 平台实现类会去读取各自的 Capability 或者是 ApiLookup
    int getEnergyValue(net.minecraft.world.level.block.entity.BlockEntity blockEntity);
}
```

### 2.2 编写全局加载类 (`Services`)
*   **代码位置**：`com/tutorial/tutorialmod/platform/Services.java`

```java
package com.tutorial.tutorialmod.platform;

import com.tutorial.tutorialmod.platform.services.IPlatformHelper;
import java.util.ServiceLoader;

public class Services {
    
    // 静态常量，游戏加载时自动解析并注入对应平台实现的实现类
    public static final IPlatformHelper PLATFORM = load(IPlatformHelper.class);

    public static <T> T load(Class<T> serviceClass) {
        return ServiceLoader.load(serviceClass)
                .findFirst()
                .orElseThrow(() -> new NullPointerException("Failed to load service implementation for: " + serviceClass.getName()));
    }
}
```

---

## 3. 在 NeoForge 平台层中实现接口 (NeoForge Layer)

在 NeoForge 项目专属的子模块/代码包中，编写对该接口的具体实现，读取 NeoForge 的专属 API：

### 3.1 编写适配实现类 (`NeoForgePlatformHelper`)
*   **代码位置**：`com/tutorial/tutorialmod/platform/NeoForgePlatformHelper.java`

```java
package com.tutorial.tutorialmod.platform;

import com.tutorial.tutorialmod.platform.services.IPlatformHelper;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLEnvironment;

public class NeoForgePlatformHelper implements IPlatformHelper {

    @Override
    public boolean isClient() {
        return FMLEnvironment.dist.isClient();
    }

    @Override
    public boolean isModLoaded(String modId) {
        return ModList.get().isLoaded(modId);
    }

    @Override
    public int getEnergyValue(BlockEntity blockEntity) {
        // 在 NeoForge 中，调用其独有的 Capability 机制
        // 假设之前注册了能量 Capability：net.neoforged.neoforge.capabilities.Capabilities
        // return blockEntity.getLevel().getCapability(Capabilities.EnergyStorage.BLOCK, blockEntity.getBlockPos(), null).getEnergyStored();
        return 0; 
    }
}
```

### 3.2 注册 Java SPI 配置文件

为了让 Java 的 `ServiceLoader` 能在游戏加载时顺利加载到该实现类，必须在 resources 资源路径下声明服务实现类映射：

*   **文件路径**：`src/main/resources/META-INF/services/com.tutorial.tutorialmod.platform.services.IPlatformHelper`
*   **文件内容**（填入 NeoForge 实现类的全类名，只有一行，无空格，无分号）：
    ```
    com.tutorial.tutorialmod.platform.NeoForgePlatformHelper
    ```

---

## 4. 业务逻辑层的优雅调用 (Gameplay Invocation)

在通用代码包的业务逻辑类中，**严禁直接导入 neoforge 相关的包**，一律通过 `Services.PLATFORM` 接口进行访问：

```java
package com.tutorial.tutorialmod.item;

import com.tutorial.tutorialmod.platform.Services;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.level.block.entity.BlockEntity;

public class RubyWandItem extends Item {
    public RubyWandItem(Properties properties) {
        super(properties);
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        BlockEntity targetBE = context.getLevel().getBlockEntity(context.getClickedPos());
        
        if (targetBE != null) {
            // 通过接口动态获取能量值，成功将 "Level.getCapability" 解耦出了核心业务类
            int energy = Services.PLATFORM.getEnergyValue(targetBE);
            System.out.println("Block Entity Energy (Decoupled): " + energy);
        }
        
        // 检查模组兼容性，无需直接引入 ModList
        if (Services.PLATFORM.isModLoaded("jei")) {
            // 处理与 jei 的联动业务...
        }

        return InteractionResult.SUCCESS;
    }
}
```
通过这套 **Interface -> ServiceLoader -> Expect/Actual Pattern**，您可以强力保护核心逻辑不被特定的加载器“深度绑架”，在移植 Fabric 时仅需在 Fabric 端重写 `IPlatformHelper` 即可，实现真正的高质量软件架构开发。
