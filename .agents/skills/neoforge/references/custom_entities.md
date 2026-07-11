# NeoForge 1.21.1 自定义生物实体与 AI 系统指南

在 Minecraft 中，开发自定义生物实体（Mobs）需要严密处理双端隔离。如果将客户端渲染相关的类（如 `Renderer`、`Model`）直接与服务端的属性或 AI 逻辑写在同一个普通类中，**在联机服务器（Dedicated Server）启动时会直接崩溃**。

本指南提供了最规范的实体注册、属性注入、客户端独立绑定以及高性能 AI 节流设计的标准实现。

---

## 1. 自定义实体注册与逻辑类

```java
package com.tutorial.tutorialmod.entity;

import com.tutorial.tutorialmod.entity.ai.WaterAvoidGoal;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.attributes.AttributeSupplier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.ai.goal.*;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;

public class RubyGhostEntity extends Monster {

    public RubyGhostEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
    }

    // 1. 声明实体的属性构造器（注意：这里仅定义，并不执行注册）
    public static AttributeSupplier.Builder createAttributes() {
        return Monster.createMonsterAttributes()
                .add(Attributes.MAX_HEALTH, 20.0D)       // 生命值 20
                .add(Attributes.MOVEMENT_SPEED, 0.25D)   // 移动速度
                .add(Attributes.ATTACK_DAMAGE, 4.0D)     // 攻击伤害
                .add(Attributes.FOLLOW_RANGE, 32.0D);    // 仇恨追踪范围
    }

    // 2. 编写实体的 AI 行为（Goals）
    @Override
    protected void registerGoals() {
        // 浮水行为 (高优先级 0)
        this.goalSelector.addGoal(0, new FloatGoal(this));
        
        // 性能优化：我们编写的自定义高性能避水/移动 AI 目标 (优先级 1)
        this.goalSelector.addGoal(1, new WaterAvoidGoal(this, 1.0D));

        // 追击玩家并近战攻击 (优先级 2)
        this.goalSelector.addGoal(2, new MeleeAttackGoal(this, 1.2D, false));

        // 随机看守与四周巡逻 (优先级 3)
        this.goalSelector.addGoal(3, new WaterAvoidingRandomStrollGoal(this, 1.0D));
        this.goalSelector.addGoal(4, new LookAtPlayerGoal(this, Player.class, 8.0F));
        this.goalSelector.addGoal(5, new RandomLookAroundGoal(this));

        // 仇恨目标：反击攻击它的生物
        this.targetSelector.addGoal(1, new HurtByTargetGoal(this));
        // 仇恨目标：主动寻找并攻击玩家
        this.targetSelector.addGoal(2, new NearestAttackableTargetGoal<>(this, Player.class, true));
    }
}
```

在注册类中添加实体类型定义：
```java
package com.tutorial.tutorialmod.entity;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.entity.MobCategory;
import net.minecraft.world.entity.EntityType;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModEntities {
    public static final DeferredRegister<EntityType<?>> ENTITY_TYPES =
            DeferredRegister.create(Registries.ENTITY_TYPE, TutorialMod.MODID);

    public static final DeferredHolder<EntityType<?>, EntityType<RubyGhostEntity>> RUBY_GHOST =
            ENTITY_TYPES.register("ruby_ghost", () ->
                    EntityType.Builder.of(RubyGhostEntity::new, MobCategory.MONSTER)
                            .sized(0.6F, 1.8F) // 碰撞箱大小 (宽, 高)
                            .build("ruby_ghost")
            );
}
```

---

## 2. 属性绑定事件 (必须监听在 Mod 总线)

在模组启动时，必须使用事件将属性注入到对应的 `EntityType` 中。该事件必须绑定在 **MOD 事件总线**，这是服务端正常加载实体的基础：

```java
package com.tutorial.tutorialmod.entity;

import com.tutorial.tutorialmod.TutorialMod;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.entity.EntityAttributeCreationEvent;

@EventBusSubscriber(modid = TutorialMod.MODID) // 1.21.1+ 已废弃 bus 参数，系统会自动通过 IModBusEvent 路由
public class EntityAttributeRegistrar {

    @SubscribeEvent
    public static void registerAttributes(EntityAttributeCreationEvent event) {
        // 将 RubyGhostEntity 的属性构建器绑定给其 EntityType
        event.put(ModEntities.RUBY_GHOST.get(), RubyGhostEntity.createAttributes().build());
    }
}
```

---

## 3. 客户端渲染物理分离注册 (Client Only)

所有与 `Model`（模型）、`Renderer`（渲染类）相关的类加载，必须**完全隔绝在物理客户端事件总线**中。

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.entity.ModEntities;
import net.minecraft.client.renderer.entity.GhastRenderer; // 假设使用原版的恶魂 (Ghast) 渲染器
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;

// 极其重要：value = Dist.CLIENT 限制此事件处理器只在物理客户端加载，防止服务端崩溃
@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT) // 1.21.1+ 已废弃 bus 参数，系统会自动通过 IModBusEvent 路由
public class ClientEntityRendererRegistrar {

    @SubscribeEvent
    public static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
        // 将实体和渲染器进行绑定
        event.registerEntityRenderer(ModEntities.RUBY_GHOST.get(), context -> new GhastRenderer(context));
    }
}
```

---

## 4. 性能优化：自定义 AI Goal 的频次限制 (Tick Throttling)

自定义 AI 如果在 `tick()` 中频繁调用复杂的寻路和周围实体扫描，会让服务器负载指数级上升。优秀的设计应当实现**时间步长检测 (Tick Cooldown)**：

```java
package com.tutorial.tutorialmod.entity.ai;

import net.minecraft.world.entity.PathfinderMob;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.phys.Vec3;

import java.util.EnumSet;

public class WaterAvoidGoal extends Goal {
    private final PathfinderMob mob;
    private final double speedModifier;
    private final PathNavigation navigation;
    private int pathfindCooldown = 0; // 寻路冷却计数器

    public WaterAvoidGoal(PathfinderMob mob, double speedModifier) {
        this.mob = mob;
        this.speedModifier = speedModifier;
        this.navigation = mob.getNavigation();
        // 设置标志位，此 Goal 涉及移动 (MOVE)
        this.setFlags(EnumSet.of(Flag.MOVE));
    }

    @Override
    public boolean canUse() {
        // 如果生物已经处于水中，则启动此 AI 目标
        return this.mob.isInWater();
    }

    @Override
    public void start() {
        this.pathfindCooldown = 0; // 启动时立刻执行一次
    }

    @Override
    public void tick() {
        // 性能优化核心点：避免每 tick 都执行开销巨大的寻路算法。这里限制为每 10 tick（0.5秒）才寻路一次
        if (--this.pathfindCooldown <= 0) {
            this.pathfindCooldown = 10; // 重置冷却时间

            // 寻找远离水面的目标位置
            Vec3 escapePos = findEscapePosition();
            if (escapePos != null) {
                // 执行 A* 寻路移动
                this.navigation.moveTo(escapePos.x, escapePos.y, escapePos.z, this.speedModifier);
            }
        }
    }

    private Vec3 findEscapePosition() {
        // 寻找非水面干燥陆地的简单查找算法...
        return null;
    }

    @Override
    public boolean canContinueToUse() {
        // 如果没走到陆地且导航还在继续，则继续运行
        return this.mob.isInWater() && !this.navigation.isDone();
    }

    @Override
    public void stop() {
        this.navigation.stop(); // 停止导航
    }
}
```
通过这种**物理隔离（分端加载） + AI 频次冷却机制**，保证了模组即使在联机服务器中生成数百只怪物，也能保持平稳极佳的 TPS 性能表现。

---

## 5. 自定义生物自然生成规则 (neoforge:add_spawns)

在 1.21.1 中，控制自定义生物在世界的什么群系、以多少概率生成，完全通过**数据驱动的 Biome Modifier（群系修改器）**实现，无需编写任何 Java 代码。

### 5.1 编写生物生成修改器 JSON

*   **文件路径**：`src/main/resources/data/tutorialmod/neoforge/biome_modifier/spawn_my_entity.json`

> [!IMPORTANT]
> 在 1.21.1 NeoForge 中，文件夹路径必须存放在 **`neoforge/biome_modifier/`** 命名空间下。修改器的 `type` 类型必须为 **`neoforge:add_spawns`**（已废弃旧版 Forge 的 `forge:add_spawns`）。

```json
{
  "type": "neoforge:add_spawns",
  "biomes": "#minecraft:is_forest",
  "spawners": {
    "type": "tutorialmod:my_entity",
    "weight": 20,
    "minCount": 1,
    "maxCount": 4
  }
}
```

### 属性详解
*   `biomes`：指定在哪些群系生成。可以使用群系标签，例如 `#minecraft:is_forest`（所有森林类群系）、`#minecraft:is_overworld`（所有主世界群系）。也可以传入包含多个群系命名空间 ID 的列表（如 `["minecraft:plains", "minecraft:savanna"]`）。
*   `spawners`：定义生成规则。
    *   `type`：目标实体的注册 ID（`tutorialmod:my_entity`）。
    *   `weight`：生成权重。例如僵尸为 100，末影人为 10。这里设为 20 代表中等偏低的罕见度。
    *   `minCount` / `maxCount`：单次尝试生成时，该生物群落（群聚）的最小与最大数量（这里设为 1 ~ 4 只结伴生成）。

---

## 6. 自定义投掷物与箭矢实体 (Projectiles & Arrows)

制作手抛手榴弹、火球（投掷物）或者自定义射弹（箭矢）是模组开发中的高频需求。1.21.1 需要正确处理其网络封包同步与渲染。

### 6.1 自定义投掷物实体 (ThrowableItemProjectile)
```java
package com.tutorial.tutorialmod.entity;

import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.ThrowableItemProjectile;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.HitResult;

public class RubyGrenadeEntity extends ThrowableItemProjectile {

    public RubyGrenadeEntity(EntityType<? extends ThrowableItemProjectile> type, Level level) {
        super(type, level);
    }

    public RubyGrenadeEntity(Level level, LivingEntity shooter) {
        super(ModEntities.RUBY_GRENADE.get(), shooter, level);
    }

    // 指定该投掷物在渲染时展示的物品贴图 (即红宝石手榴弹物品)
    @Override
    protected Item getDefaultItem() {
        return ModItems.RUBY_GRENADE.get();
    }

    // 命中后的物理冲击逻辑
    @Override
    protected void onHit(HitResult result) {
        super.onHit(result);
        if (!this.level().isClientSide) {
            // 在命中点产生一个不破坏方块的 3.0 威力爆炸
            this.level().explode(this, this.getX(), this.getY(), this.getZ(), 3.0F, Level.ExplosionInteraction.NONE);
            this.discard(); // 销毁实体
        }
    }

    @Override
    protected void onHitEntity(EntityHitResult result) {
        super.onHitEntity(result);
        // 如果砸中生物，直接给予其 5 点伤害
        result.getEntity().hurt(this.damageSources().thrown(this, this.getOwner()), 5.0F);
    }
}
```

### 6.2 自定义箭矢实体 (AbstractArrow)
```java
package com.tutorial.tutorialmod.entity;

import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.AbstractArrow;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

public class RubyArrowEntity extends AbstractArrow {

    public RubyArrowEntity(EntityType<? extends AbstractArrow> type, Level level) {
        super(type, level);
    }

    public RubyArrowEntity(Level level, LivingEntity shooter, ItemStack pickupStack) {
        super(ModEntities.RUBY_ARROW.get(), shooter, level, pickupStack, null);
    }

    // 1.21.1 核心要求：当捡起箭矢时，返回什么 ItemStack 实例
    @Override
    protected ItemStack getDefaultPickupItem() {
        return new ItemStack(ModItems.RUBY_ARROW.get());
    }

    @Override
    public void tick() {
        super.tick();
        // 飞行时在尾部产生粒子特效
        if (this.level().isClientSide && !this.inGround) {
            this.level().addParticle(net.minecraft.core.particles.ParticleTypes.END_ROD, 
                    this.getX(), this.getY(), this.getZ(), 0.0, 0.0, 0.0);
        }
    }
}
```

---

## 7. 实体的 SyncedData 声明与多端同步 (Entity DataSync)

在 1.21.1 中，实体的状态字段（如：是否被激怒、当前蓄力百分比）需要实时从服务端同步给客户端，不能使用普通的成员变量，必须使用 **`SynchedEntityData`**。

### 7.1 使用 DataWatcher 定义与同步状态
```java
package com.tutorial.tutorialmod.entity;

import net.minecraft.network.syncher.EntityDataAccessor;
import net.minecraft.network.syncher.EntityDataSerializers;
import net.minecraft.network.syncher.SynchedEntityData;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.level.Level;

public class ModSyncedEntity extends Monster {

    // 1. 注册数据存取器 (EntityDataAccessor)
    // ⚠️ 1.21.1 泛型约束：defineId 必须传入当前实体类.class 以及对应类型的 Serializer 接口
    private static final EntityDataAccessor<Boolean> IS_ENRAGED = 
            SynchedEntityData.defineId(ModSyncedEntity.class, EntityDataSerializers.BOOLEAN);

    protected ModSyncedEntity(EntityType<? extends Monster> type, Level level) {
        super(type, level);
    }

    // 2. 初始化 DataWatcher (1.21.1 中此方法重构为 defineSynchedData，接收 Builder 参数)
    @Override
    protected void defineSynchedData(SynchedEntityData.Builder builder) {
        super.defineSynchedData(builder);
        // 初始化默认值为 false
        builder.define(IS_ENRAGED, false);
    }

    // === Getter & Setter (对数据存取器的安全封装) ===
    
    public boolean isEnraged() {
        return this.entityData.get(IS_ENRAGED);
    }

    public void setEnraged(boolean enraged) {
        // 服务端设置后，DataWatcher 会自动发送网络包通知所有附近客户端进行值更新
        this.entityData.set(IS_ENRAGED, enraged);
    }
}
```

---

## ⚠️ 1.21.1 自定义实体高频编译错误防御与自愈

*   **编译报错**：`method defineSynchedData() does not override a method from its superclass`
    *   ❌ 错误：在 1.21.1 中强行覆写 1.20 之前无参的 `protected void defineSynchedData()`。
    *   ✅ 修正：在 1.21.1 中，该方法已被重构并变更为接收 `SynchedEntityData.Builder` 参数。必须覆写为：
        ```java
        @Override
        protected void defineSynchedData(SynchedEntityData.Builder builder) {
            super.defineSynchedData(builder);
            builder.define(DATA_KEY, defaultValue);
        }
        ```
*   **编译报错**：`constructor AbstractArrow(EntityType,LivingEntity,Level) is removed / cannot find symbol`
    *   ❌ 错误：使用 `super(ModEntities.RUBY_ARROW.get(), shooter, level)` 构造箭矢实体。
    *   ✅ 修正：在 1.21.1 中，`AbstractArrow` 构造器发生重构，为了保证捡起逻辑的安全，**必须在构造中传入代表捡起物品的 ItemStack 参数**：
        ```java
        public RubyArrowEntity(Level level, LivingEntity shooter, ItemStack pickupStack) {
            super(ModEntities.RUBY_ARROW.get(), shooter, level, pickupStack, null);
        }
        ```
*   **编译报错**：`no suitable constructor found for ThrownEgg/ThrowableItemProjectile(EntityType,LivingEntity,Level)`
    *   ❌ 错误：在投掷实体类中编写旧版的双参数构造函数。
    *   ✅ 修正：1.21.1 的投掷物构造器现在需要显式调用三参数签名：`super(type, shooter, level)`。
*   **运行时崩溃**：`NullPointerException: Registry not present / Unbound values` (在主类初始化中注册投掷射弹渲染器时)
    *   ❌ 错误：直接在 `ClientEntityRendererRegistrar` 中使用原版的 `ThumbsUpRenderer` 或者是 `ThrownItemRenderer` 进行 `new`，未隔离客户端。
    *   ✅ 修正：射弹和投掷物的渲染器必须全部集中绑定在被 `@EventBusSubscriber(value = Dist.CLIENT)` 装饰的专属类中。对于简单的投掷物展示，可以在 `EntityRenderersEvent.RegisterRenderers` 中直接注册为 `ThrownItemRenderer::new` 委托给原版物品渲染：
        ```java
        event.registerEntityRenderer(ModEntities.RUBY_GRENADE.get(), ThrownItemRenderer::new);
        ```


