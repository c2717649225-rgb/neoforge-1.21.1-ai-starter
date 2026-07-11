# NeoForge 1.21.1 自定义粒子 (Particles) 系统指南

在魔法、动作或科技设备中，炫酷的魔法微粒、火焰喷射、电火花等视觉特效是提升模组高级感的必备机制。

在 1.21.1 中，粒子系统分为：**公共端注册（注册粒子类型）**、**物理客户端渲染（粒子实体类与渲染提供器）** 和 **JSON 材质映射文件**。

---

## 1. 注册粒子类型 (ParticleType)

粒子类型需要在公共总线进行声明注册，两端都会加载：

```java
package com.tutorial.tutorialmod.particle;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.particles.ParticleType;
import net.minecraft.core.particles.SimpleParticleType;
import net.minecraft.core.registries.Registries;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModParticles {
    public static final DeferredRegister<ParticleType<?>> PARTICLE_TYPES =
            DeferredRegister.create(Registries.PARTICLE_TYPE, TutorialMod.MODID);

    // 注册一个不需要附加额外数据的简单粒子 (SimpleParticleType)
    // 第一个参数为 false 代表此粒子不需要网络同步优化限制，可以本地高频泛用
    public static final DeferredHolder<ParticleType<?>, SimpleParticleType> RUBY_SPARKLE =
            PARTICLE_TYPES.register("ruby_sparkle", () -> new SimpleParticleType(false));
}
```

---

## 2. 编写粒子类与渲染提供器 (Client Only)

粒子实体类定义了粒子的重力、运动轨迹、衰减速度以及材质拉伸。

```java
package com.tutorial.tutorialmod.client.particle;

import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.particle.*;
import net.minecraft.core.particles.SimpleParticleType;

public class RubySparkleParticle extends TextureSheetParticle {

    private final SpriteSet sprites;

    protected RubySparkleParticle(ClientLevel level, double x, double y, double z, 
                                  double xSpeed, double ySpeed, double zSpeed, SpriteSet sprites) {
        super(level, x, y, z, xSpeed, ySpeed, zSpeed);
        this.sprites = sprites;

        this.lifetime = 20 + this.random.nextInt(10); // 存活时间 20 ~ 30 tick (1.5秒)
        this.gravity = 0.05F; // 粒子会受到微弱的重力缓缓下落 (负数则会上升)
        
        // 粒子的初始物理漂移速度
        this.xd = xSpeed * 0.1D;
        this.yd = ySpeed * 0.1D;
        this.zd = zSpeed * 0.1D;

        this.quadSize *= 0.8F; // 基础缩放系数 (0.8 倍大小)

        // 默认上色 (红色 ARGB)
        this.rCol = 1.0F;
        this.gCol = 0.2F;
        this.bCol = 0.2F;

        // 设置动画帧材质 (从 SpriteSet 中挑取第一帧初始化)
        this.setSpriteFromAge(sprites);
    }

    // 重写渲染模式类型，对于材质图集粒子，固定返回 PARTICLE_SHEET_OPAQUE 或 PARTICLE_SHEET_TRANSLUCENT
    @Override
    public ParticleRenderType getRenderType() {
        return ParticleRenderType.PARTICLE_SHEET_TRANSLUCENT; // 允许半透明叠加渲染
    }

    @Override
    public void tick() {
        super.tick(); // 执行重力位移和生命消亡
        // 每一 tick 自动根据粒子的寿命百分比自动渲染对应帧的贴图，形成流畅的连环动画
        this.setSpriteFromAge(this.sprites);
    }

    // 核心工厂提供器：接收 SpriteSet 并构建粒子实例
    public static class Provider implements ParticleProvider<SimpleParticleType> {
        private final SpriteSet sprites;

        public Provider(SpriteSet sprites) {
            this.sprites = sprites;
        }

        @Override
        public Particle createParticle(SimpleParticleType type, ClientLevel level, 
                                       double x, double y, double z, 
                                       double xSpeed, double ySpeed, double zSpeed) {
            return new RubySparkleParticle(level, x, y, z, xSpeed, ySpeed, zSpeed, this.sprites);
        }
    }
}
```

---

## 3. 注册粒子提供器 (RegisterParticleProvidersEvent)

我们需要在客户端 Mod 事件总线上订阅 `RegisterParticleProvidersEvent`，完成粒子类型与渲染提供器的绑定：

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.client.particle.RubySparkleParticle;
import com.tutorial.tutorialmod.particle.ModParticles;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterParticleProvidersEvent;

@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT)
public class ClientParticleRegistrar {

    @SubscribeEvent
    public static void registerParticleProviders(RegisterParticleProvidersEvent event) {
        // 注册工厂绑定
        event.registerSpriteSet(
                ModParticles.RUBY_SPARKLE.get(),
                RubySparkleParticle.Provider::new // 传入构造函数引用
        );
    }
}
```

---

## 4. 编写粒子纹理声明 JSON (Particle Texture)

粒子在客户端加载时，必须通过 JSON 声明其引用的具体 `.png` 材质文件：

*   **文件路径**：`src/main/resources/assets/tutorialmod/particles/ruby_sparkle.json`

```json
{
  "textures": [
    "tutorialmod:ruby_sparkle_0",
    "tutorialmod:ruby_sparkle_1",
    "tutorialmod:ruby_sparkle_2"
  ]
}
```

### 文件映射位置
上面的配置代表在客户端，该粒子会依次加载如下三个 PNG 图片作为它的动画帧材质：
1.  `assets/tutorialmod/textures/particle/ruby_sparkle_0.png`
2.  `assets/tutorialmod/textures/particle/ruby_sparkle_1.png`
3.  `assets/tutorialmod/textures/particle/ruby_sparkle_2.png`

---

## 5. 触发粒子生成方式 (Deal Spawning)

在 Java 代码中，你可以在服务端或物理客户端生成粒子：

### 5.1 服务端（向周围所有玩家广播同步粒子，最常用）
```java
// ServerLevel 层面广播
serverLevel.sendParticles(
        ModParticles.RUBY_SPARKLE.get(),
        x, y, z, 
        15, // 粒子生成数量
        0.2D, 0.2D, 0.2D, // 生成坐标的随机偏移偏差 (DX, DY, DZ)
        0.05D // 粒子的基础散射速度
);
```

### 5.2 客户端（仅本地生成，适合机器 animateTick 与本地方块效果）
```java
// Client Level 层面本地生成，不耗费任何服务器网络包流量
level.addParticle(
        ModParticles.RUBY_SPARKLE.get(),
        x, y, z,
        xSpeed, ySpeed, zSpeed
);
```
