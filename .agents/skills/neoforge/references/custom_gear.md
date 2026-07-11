# NeoForge 1.21.1 自定义装备 (工具等级、工具物品与护甲材质) 指南

在 Minecraft 1.20.5+ 和 1.21.1 中，装备系统的代码定义和资源文件加载规则发生了根本性变化。

以前的“采掘等级整数值（如 0, 1, 2, 3）”和“多参数工具构造器”均已**被完全移除**；而护甲材质 `ArmorMaterial` 也已变成**非注册的静态配置类**。以下是编写 1.21.1 工具和护甲的完整标准蓝图。

---

## 1. 自定义工具等级 (Tool Tiers)

1.21.1 的工具等级通过 `SimpleTier` 定义。其第一个参数必须是 `TagKey<Block>`，用于定义该工具**不具备采掘能力（Incorrect blocks）**的方块标签（例如：红宝石工具强度等同于钻石，则不适用于挖掘下界合金级别的方块）：

```java
package com.tutorial.tutorialmod.item;

import net.minecraft.tags.BlockTags;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.Tier;
import net.minecraft.world.item.crafting.Ingredient;
import net.neoforged.neoforge.common.SimpleTier;

public class ModTiers {
    // 声明自定义的红宝石 (Ruby) 工具等级
    public static final Tier RUBY = new SimpleTier(
            // 1. 采掘黑名单 Tag (声明它不能采掘什么。例如不属于钻石等级可采掘的方块)
            BlockTags.INCORRECT_FOR_DIAMOND_TOOL,
            // 2. 耐久度 (使用次数)
            1200,
            // 3. 采掘速度 (1.0F 是徒手，8.0F 是钻石，9.0F 是红宝石)
            9.0F,
            // 4. 武器/工具的基础攻击力伤害加成 (添加在基础值上的数值)
            3.5F,
            // 5. 附魔亲和度/附魔等级
            18,
            // 6. 修复原材料的 Supplier
            () -> Ingredient.of(ModItems.RUBY.get())
    );
}
```

---

## 2. 注册自定义工具物品 (Tools Registration)

在 1.21.1 中，所有的工具类（如 `PickaxeItem`）构造器只接收 `(Tier tier, Item.Properties properties)`。以前的攻速和伤害参数不再在构造器里填入，而是会自动根据 Tier 的属性和物品的基础属性进行计算：

```java
package com.tutorial.tutorialmod.item;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.item.*;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModItems {
    public static final DeferredRegister<Item> ITEMS =
            DeferredRegister.create(Registries.ITEM, TutorialMod.MODID);

    // 1. 注册稿子 (PickaxeItem)
    public static final DeferredHolder<Item, PickaxeItem> RUBY_PICKAXE = ITEMS.register("ruby_pickaxe",
            () -> new PickaxeItem(ModTiers.RUBY, new Item.Properties()));

    // 2. 注册剑 (SwordItem)
    public static final DeferredHolder<Item, SwordItem> RUBY_SWORD = ITEMS.register("ruby_sword",
            () -> new SwordItem(ModTiers.RUBY, new Item.Properties()));

    // 3. 注册铲子 (ShovelItem)
    public static final DeferredHolder<Item, ShovelItem> RUBY_SHOVEL = ITEMS.register("ruby_shovel",
            () -> new ShovelItem(ModTiers.RUBY, new Item.Properties()));

    // 4. 注册斧头 (AxeItem)
    public static final DeferredHolder<Item, AxeItem> RUBY_AXE = ITEMS.register("ruby_axe",
            () -> new AxeItem(ModTiers.RUBY, new Item.Properties()));

    // 5. 注册锄头 (HoeItem)
    public static final DeferredHolder<Item, HoeItem> RUBY_HOE = ITEMS.register("ruby_hoe",
            () -> new HoeItem(ModTiers.RUBY, new Item.Properties()));
}
```

---

## 3. 自定义护甲材质与注册表声明 (Armor Materials & Registry)

在 1.21.1 中，`ArmorMaterial` 从以往的 Enum 结构彻底转变为**注册表对象**（基于 `BuiltInRegistries.ARMOR_MATERIAL` 注册表），其实体数据结构为 Java Record。

我们必须使用 `DeferredRegister` 注册自定义的护甲材质，以便游戏能够正确进行跨模组材质检索和数据合并。

```java
package com.tutorial.tutorialmod.item;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.Util;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.crafting.Ingredient;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import java.util.EnumMap;
import java.util.List;

public class ModArmorMaterials {
    // 1. 创建护甲材质延迟注册表
    public static final DeferredRegister<ArmorMaterial> ARMOR_MATERIALS =
            DeferredRegister.create(Registries.ARMOR_MATERIAL, TutorialMod.MODID);

    // 2. 注册红宝石 (Ruby) 材质
    public static final DeferredHolder<ArmorMaterial, ArmorMaterial> RUBY = ARMOR_MATERIALS.register("ruby",
            () -> new ArmorMaterial(
                    // 各个部位的防御点数映射 (ArmorItem.Type.class)
                    Util.make(new EnumMap<>(ArmorItem.Type.class), map -> {
                        map.put(ArmorItem.Type.BOOTS, 3);      // 靴子防御 3 点 (1.5心)
                        map.put(ArmorItem.Type.LEGGINGS, 6);   // 护腿防御 6 点 (3心)
                        map.put(ArmorItem.Type.CHESTPLATE, 8); // 胸甲防御 8 点 (4心)
                        map.put(ArmorItem.Type.HELMET, 3);     // 头盔防御 3 点 (1.5心)
                    }),
                    // 装备附魔亲和度
                    15,
                    // 穿戴装备时的音效 (SoundEvents.ARMOR_EQUIP_DIAMOND 返回的是 Holder<SoundEvent>)
                    SoundEvents.ARMOR_EQUIP_DIAMOND,
                    // 修复原材料的 Supplier
                    () -> Ingredient.of(ModItems.RUBY.get()),
                    List.of(new ArmorMaterial.Layer(
                            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_armor"),
                            "",
                            false
                    )),
                    // 护甲韧性 (Toughness)
                    2.0F,
                    // 击退抗性 (Knockback Resistance)
                    0.0F
            )
    );
}
```
*注意：必须在模组构造器（主类）中调用 `ModArmorMaterials.ARMOR_MATERIALS.register(modEventBus)` 激活注册。*

---

## 4. 注册自定义护甲物品 (Armor Items)

在 1.21.1 中，`ArmorItem` 构造器接收 `(Holder<ArmorMaterial> material, Type type, Properties properties)`。由于 `DeferredHolder` 本身就实现了 `Holder` 接口，我们可以直接将刚刚注册的材质 `ModArmorMaterials.RUBY` 传入，无需任何包装：

```java
package com.tutorial.tutorialmod.item;

import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.Item;
import net.neoforged.neoforge.registries.DeferredHolder;

public class ModArmorItems {

    // 1. 注册红宝石头盔 (HELMET)
    public static final DeferredHolder<Item, ArmorItem> RUBY_HELMET = ModItems.ITEMS.register("ruby_helmet",
            () -> new ArmorItem(
                    ModArmorMaterials.RUBY, // 直接传入 DeferredHolder 即可
                    ArmorItem.Type.HELMET, 
                    new Item.Properties().durability(ArmorItem.Type.HELMET.getDurability(33)) // 根据防御倍率计算耐久度
            ));

    // 2. 注册红宝石胸甲 (CHESTPLATE)
    public static final DeferredHolder<Item, ArmorItem> RUBY_CHESTPLATE = ModItems.ITEMS.register("ruby_chestplate",
            () -> new ArmorItem(
                    ModArmorMaterials.RUBY,
                    ArmorItem.Type.CHESTPLATE,
                    new Item.Properties().durability(ArmorItem.Type.CHESTPLATE.getDurability(33))
            ));

    // 3. 注册红宝石护腿 (LEGGINGS)
    public static final DeferredHolder<Item, ArmorItem> RUBY_LEGGINGS = ModItems.ITEMS.register("ruby_leggings",
            () -> new ArmorItem(
                    ModArmorMaterials.RUBY,
                    ArmorItem.Type.LEGGINGS,
                    new Item.Properties().durability(ArmorItem.Type.LEGGINGS.getDurability(33))
            ));

    // 4. 注册红宝石靴子 (BOOTS)
    public static final DeferredHolder<Item, ArmorItem> RUBY_BOOTS = ModItems.ITEMS.register("ruby_boots",
            () -> new ArmorItem(
                    ModArmorMaterials.RUBY,
                    ArmorItem.Type.BOOTS,
                    new Item.Properties().durability(ArmorItem.Type.BOOTS.getDurability(33))
            ));
}
```


---

## 5. 材质物理路径避坑红线 (1.21.1 与 1.21.2+ 的绝对区别)

这是所有 1.21.1 开发者和美术资源设计师最容易混淆的痛点：

*   **在 1.21.1 物理客户端中**：
    由于我们在 `ArmorMaterial.Layer` 中指定的 ResourceLocation 是 `tutorialmod:ruby_armor`。
    游戏会**严格到旧版路径**下寻找 PNG 贴图文件：
    *   **头盔、胸甲、靴子模型贴图**：`src/main/resources/assets/tutorialmod/textures/models/armor/ruby_armor_layer_1.png`
    *   **护腿模型贴图**：`src/main/resources/assets/tutorialmod/textures/models/armor/ruby_armor_layer_2.png`
    *   *注：此时绝对不使用 1.21.2+ 的 `assets/<modid>/equipment/` 渲染 JSON 目录配置，写了也没用！*
*   **如果您在 1.21.2+ 或 1.21.4+ 环境下开发**：
    贴图才会被移入 `textures/entity/equipment/humanoid/ruby_armor.png` 并由 `equipment` 文件夹下的 JSON 重新映射。如果将 1.21.2 的新路径套用到当前的 1.21.1 模组中，**会导致玩家在穿戴红宝石护甲时，身上的护甲贴图完全隐形变成空气**。

---

## 6. 自定义物品属性加成 (Item Attribute Modifiers)

如果您想制作一个自定义武器（例如：一把不继承 `SwordItem` 的法杖、或者带有防御属性加成的戒指），在 1.21.1 中，**不能再重写 `getDefaultAttributeModifiers` 方法**，因为该方法已被完全重构为 Data Component。

必须通过 `Item.Properties().attributes(...)` 配合 `ItemAttributeModifiers` 来声明属性加成。

### 6.1 注册带有属性的物品
在注册物品时，直接在属性构建器中声明属性加成：

```java
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlotGroup;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.item.component.ItemAttributeModifiers;

public static final DeferredHolder<Item, Item> RUBY_DAGGER = ITEMS.register("ruby_dagger",
        () -> new Item(new Item.Properties()
                // 1. 使用 ItemAttributeModifiers 构造器声明属性
                .attributes(ItemAttributeModifiers.builder()
                        // 2. 添加攻击伤害：基础增加 5 点伤害
                        // ⚠️ 1.21.1 核心改变：AttributeModifier 构造器不再接收 UUID 和 String 名字，改为接收 ResourceLocation 标志键名
                        .add(Attributes.ATTACK_DAMAGE, 
                             new AttributeModifier(
                                     ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "weapon_damage"), 
                                     5.0D, 
                                     AttributeModifier.Operation.ADD_VALUE
                             ), 
                             EquipmentSlotGroup.MAINHAND // 指定在主手持有时生效
                        )
                        // 3. 增加移速：当副手持有或装备时速度提升 10%
                        .add(Attributes.MOVEMENT_SPEED, 
                             new AttributeModifier(
                                     ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "accessory_speed"), 
                                     0.10D, 
                                     AttributeModifier.Operation.ADD_MULTIPLIED_BASE
                             ), 
                             EquipmentSlotGroup.ANY // 任何装备或手持栏位都会生效
                        )
                        .build()
                )
        ));
```

### 6.2 关键版本对比与红线避坑

1.  **构造函数签名变更**：
    *   *1.20.4 旧版*：`new AttributeModifier(UUID.fromString("..."), "Modifier Name", 5.0D, Operation.ADDITION)`
    *   *1.21.1 新版*：`new AttributeModifier(ResourceLocation, double, Operation)`
    *   在 1.21.1 中，Mojang **彻底移除了 UUID 参数和 String 名字参数**，如果写入 UUID 或 String 会导致项目根本无法编译。
2.  **槽位组 Enum 升级**：
    *   *1.20.4 旧版*：使用 `EquipmentSlot`（如 `EquipmentSlot.MAINHAND`）。
    *   *1.21.1 新版*：使用 **`EquipmentSlotGroup`**（如 `EquipmentSlotGroup.MAINHAND` 或 `EquipmentSlotGroup.ANY`），用于适应更多的手持/护甲复合插槽环境。

---

## 7. ⚠️ 1.21.1 自定义装备高频编译错误防御与自愈

*   **编译报错**：`constructor SwordItem cannot be applied to given types; required: Tier,Properties found: Tier,int,float,Properties`
    *   ❌ 错误：在 1.21.1 中强行按照旧版本多参构造器声明工具类物品，如 `new SwordItem(tier, 3, -2.4f, properties)`。
    *   ✅ 修正：在 1.21.1 中，所有的 `SwordItem` 与 `DiggerItem` 子类（稿、斧、铲、锄）的构造器**均不再接收任何攻击力与速度参数**，只接收 `(Tier, Properties)`。修改参数必须通过 `attributes()` 方法链注入（详见第 2 节与第 6 节）。
*   **编译报错**：`ModTiers.Ruby is not abstract and does not override abstract method getIncorrectBlocksForDrops() in Tier` (或者是缺少/多余 getLevel 方法)
    *   ❌ 错误：在自定义 `Tier` 类中，重写并编写 `@Override public int getLevel() { return 3; }`。
    *   ✅ 修正：在 1.21.1 中，`Tier` 接口**彻底移除了 getLevel() 方法**！采掘白/黑名单完全通过标签系统检测。必须删除 getLevel()，改为覆写并返回对应的采掘黑名单标签：
        ```java
        @Override
        public TagKey<Block> getIncorrectBlocksForDrops() {
            return BlockTags.INCORRECT_FOR_DIAMOND_TOOL; // 对应采掘强度为钻石级
        }
        ```
*   **编译报错**：`cannot find symbol: class LivingHurtEvent location: package net.neoforged.neoforge.event.entity.living`
    *   ❌ 错误：试图通过 `@SubscribeEvent public static void onHurt(LivingHurtEvent event)` 拦截实体受到伤害的事件。
    *   ✅ 修正：1.21.1 已**彻底删除并更名了该事件**。伤害前置逻辑拦截必须改用 **`LivingIncomingDamageEvent`**。
*   **编译报错**：`constructor AttributeModifier(UUID, String, double, Operation) is removed / cannot find symbol`
    *   ❌ 错误：使用 `new AttributeModifier(UUID.randomUUID(), "Dagger Damage", 5.0, Operation.ADD_VALUE)` 声明属性修饰符。
    *   ✅ 修正：1.21.1 彻底移除了基于 UUID 和 String 构造属性修饰符的 API。必须传入唯一标识符 `ResourceLocation`：
        ```java
        new AttributeModifier(ResourceLocation.fromNamespaceAndPath("tutorialmod", "dagger_damage"), 5.0, AttributeModifier.Operation.ADD_VALUE)
        ```


