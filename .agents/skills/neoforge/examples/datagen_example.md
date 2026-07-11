# NeoForge 1.21.1 Data Generation (DataGen) Example

In Minecraft 1.21.1 and NeoForge, hand-writing JSON files for blockstates, models, loot tables, and language files is strongly discouraged. Instead, use the **Data Generation** system via `GatherDataEvent`.

---

## 1. Mod Event Bus Subscriber Setup

Create a class (e.g., `DataGenerators`) to listen to `GatherDataEvent` on the **MOD** event bus.

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.DataGenerator;
import net.minecraft.data.PackOutput;
import net.minecraft.data.loot.LootTableProvider;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.common.data.ExistingFileHelper;
import net.neoforged.neoforge.data.event.GatherDataEvent;

import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CompletableFuture;

@EventBusSubscriber(modid = TutorialMod.MODID)
public class DataGenerators {

    @SubscribeEvent
    public static void gatherData(GatherDataEvent event) {
        DataGenerator generator = event.getGenerator();
        PackOutput packOutput = generator.getPackOutput();
        ExistingFileHelper existingFileHelper = event.getExistingFileHelper();
        CompletableFuture<HolderLookup.Provider> lookupProvider = event.getLookupProvider();

        // 1. Client Assets (BlockStates, ItemModels, Language)
        generator.addProvider(event.includeClient(), new ModBlockStateProvider(packOutput, existingFileHelper));
        generator.addProvider(event.includeClient(), new ModItemModelProvider(packOutput, existingFileHelper));
        generator.addProvider(event.includeClient(), new ModLanguageProvider(packOutput, "en_us"));
        generator.addProvider(event.includeClient(), new ModLanguageProvider(packOutput, "zh_cn")); // Chinese support

        // 2. Server Data (Loot Tables)
        generator.addProvider(event.includeServer(), new LootTableProvider(
                packOutput,
                Collections.emptySet(),
                List.of(new LootTableProvider.SubProviderEntry(ModBlockLootProvider::new, LootContextParamSets.BLOCK)),
                lookupProvider
        ));
    }
}
```

---

## 2. BlockState & Model Provider

Generates `assets/<modid>/blockstates/*.json` and `assets/<modid>/models/block/*.json`.

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import net.minecraft.data.PackOutput;
import net.neoforged.neoforge.client.model.generators.BlockStateProvider;
import net.neoforged.neoforge.common.data.ExistingFileHelper;

public class ModBlockStateProvider extends BlockStateProvider {
    public ModBlockStateProvider(PackOutput output, ExistingFileHelper exFileHelper) {
        super(output, TutorialMod.MODID, exFileHelper);
    }

    @Override
    protected void registerStatesAndModels() {
        // 1. Simple Block (Generates blockstate and model pointing to textures/block/ruby_block.png)
        simpleBlock(ModBlocks.RUBY_BLOCK.get());
        simpleBlockItem(ModBlocks.RUBY_BLOCK.get(), cubeAll(ModBlocks.RUBY_BLOCK.get()));
        
        // 2. Simple Ore Block
        simpleBlock(ModBlocks.RUBY_ORE.get());
        simpleBlockItem(ModBlocks.RUBY_ORE.get(), cubeAll(ModBlocks.RUBY_ORE.get()));
    }
}
```

---

## 3. Item Model Provider

Generates `assets/<modid>/models/item/*.json` for items that are not block items.

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.data.PackOutput;
import net.neoforged.neoforge.client.model.generators.ItemModelProvider;
import net.neoforged.neoforge.common.data.ExistingFileHelper;

public class ModItemModelProvider extends ItemModelProvider {
    public ModItemModelProvider(PackOutput output, ExistingFileHelper existingFileHelper) {
        super(output, TutorialMod.MODID, existingFileHelper);
    }

    @Override
    protected void registerModels() {
        // 1. 基础物品模型生成：自动在 models/item 下生成 ruby.json 并指向 textures/item/ruby.png
        basicItem(ModItems.RUBY.get());
        basicItem(ModItems.RAW_RUBY.get());

        // 2. 手持工具类物品模型生成：继承自 "minecraft:item/handheld" 以使工具在手持时呈前倾状态
        // 自动在 models/item 下生成 ruby_pickaxe.json 并且指定 layer0 为 textures/item/ruby_pickaxe.png
        withExistingParent(ModItems.RUBY_PICKAXE.getId().getPath(), mcLoc("item/handheld"))
                .texture("layer0", modLoc("item/ruby_pickaxe"));
    }
}
```

---

## 4. Block Loot Table Provider

Generates `data/<modid>/loot_tables/blocks/*.json` specifying what items blocks drop.

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.core.HolderLookup;
import net.minecraft.data.loot.BlockLootSubProvider;
import net.minecraft.world.flag.FeatureFlags;
import net.minecraft.world.level.block.Block;

import java.util.Collections;
import java.util.Set;
import java.util.stream.Collectors;

public class ModBlockLootProvider extends BlockLootSubProvider {

    protected ModBlockLootProvider(HolderLookup.Provider registries) {
        super(Collections.emptySet(), FeatureFlags.REGISTRY.allFlags(), registries);
    }

    @Override
    protected void generate() {
        // 1. Drop itself
        this.dropSelf(ModBlocks.RUBY_BLOCK.get());

        // 2. Drop a different item (e.g. ruby ore drops raw ruby)
        this.add(ModBlocks.RUBY_ORE.get(), block -> 
                createOreDrop(block, ModItems.RAW_RUBY.get()));
    }

    @Override
    protected Iterable<Block> getKnownBlocks() {
        // Retrieve and return all registered blocks for validation
        return ModBlocks.BLOCKS.getEntries().stream()
                .map(holder -> holder.get())
                .collect(Collectors.toList());
    }
}
```

---

## 5. Language Provider

Generates localizations `assets/<modid>/lang/en_us.json` and `assets/<modid>/lang/zh_cn.json`.

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.item.ModItems;
import net.minecraft.data.PackOutput;
import net.neoforged.neoforge.common.data.LanguageProvider;

public class ModLanguageProvider extends LanguageProvider {
    private final String locale;

    public ModLanguageProvider(PackOutput output, String locale) {
        super(output, TutorialMod.MODID, locale);
        this.locale = locale;
    }

    @Override
    protected void addTranslations() {
        if ("zh_cn".equals(this.locale)) {
            // Chinese translations
            add(ModItems.RUBY.get(), "红宝石");
            add(ModItems.RAW_RUBY.get(), "粗红宝石");
            add(ModBlocks.RUBY_BLOCK.get(), "红宝石块");
            add(ModBlocks.RUBY_ORE.get(), "红宝石矿石");
        } else {
            // English (default)
            add(ModItems.RUBY.get(), "Ruby");
            add(ModItems.RAW_RUBY.get(), "Raw Ruby");
            add(ModBlocks.RUBY_BLOCK.get(), "Ruby Block");
            add(ModBlocks.RUBY_ORE.get(), "Ruby Ore");
        }
    }
}
```

---

## 6. 朝向方块的注册与模型生成 (Directional Block DataGen)

在模组开发中，许多机器方块（如炉子、机器）都有一个正面（Front）、侧面（Side）和顶部（Top），并且在放置时需要**朝向玩家**。

以下是实现朝向方块的注册与自动生成其模型和 Blockstate JSON 的标准代码。

### 6.1 编写和注册朝向方块类

```java
package com.tutorial.tutorialmod.block;

import net.minecraft.core.Direction;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.DirectionProperty;

public class MyMachineBlock extends Block {
    // 1. 声明朝向与状态属性 (FACING 为东、南、西、北，LIT 表示运行/发光状态)
    public static final net.minecraft.world.level.block.state.properties.DirectionProperty FACING = HorizontalDirectionalBlock.FACING;
    public static final net.minecraft.world.level.block.state.properties.BooleanProperty LIT = net.minecraft.world.level.block.state.properties.BlockStateProperties.LIT;

    public MyMachineBlock(Properties properties) {
        super(properties);
        // 2. 设置默认状态：朝北，熄灭
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH).setValue(LIT, false));
    }

    // 3. 将属性加入到方块状态定义中 (必须重写)
    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, LIT);
    }

    // 4. 当玩家放置方块时，自动计算并将其朝向设置为玩家视线的相反方向 (正面朝向玩家)
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(FACING, context.getHorizontalDirection().getOpposite()).setValue(LIT, false);
    }
}
```

### 6.2 编写 BlockStateProvider 自动生成旋转模型

在 `ModBlockStateProvider` 中，我们需要使用 `horizontalBlock()` 方法来生成带有四个水平旋转角度的 `blockstates/<block_name>.json` 映射文件，并使用 `orientable` 模板指定多面贴图：

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.block.ModBlocks;
import com.tutorial.tutorialmod.block.MyMachineBlock;
import net.minecraft.data.PackOutput;
import net.neoforged.neoforge.client.model.generators.BlockStateProvider;
import net.neoforged.neoforge.client.model.generators.ModelFile;
import net.neoforged.neoforge.common.data.ExistingFileHelper;

public class ModBlockStateProvider extends BlockStateProvider {

    public ModBlockStateProvider(PackOutput output, ExistingFileHelper exFileHelper) {
        super(output, TutorialMod.MODID, exFileHelper);
    }

    @Override
    protected void registerStatesAndModels() {
        // 1. 简易朝向方块模型生成：自动生成包含 north, south, east, west 旋转定义的 blockstate JSON 文件
        // 自动生成 front, side, top 贴图定位的 models/block/my_machine.json 模型文件
        horizontalBlock(
                ModBlocks.MY_MACHINE.get(), 
                models().orientable(
                        "my_machine", // 生成的模型文件名
                        modLoc("block/my_machine_side"),  // 侧面与背面贴图
                        modLoc("block/my_machine_front"), // 正面贴图
                        modLoc("block/my_machine_top")    // 顶部与底部贴图
                )
        );

        // 2. 双属性状态方块模型生成 (朝向 FACING + 运行状态 LIT)：
        // 对于带点亮状态的机器，我们需要分别生成熄灭与点亮两个模型，并根据 8 种复合状态构建映射
        getVariantBuilder(ModBlocks.MY_COMPLEX_MACHINE.get()).forAllStates(state -> {
            net.minecraft.core.Direction dir = state.getValue(MyMachineBlock.FACING);
            boolean lit = state.getValue(MyMachineBlock.LIT);
            String modelName = lit ? "my_complex_machine_on" : "my_complex_machine";

            // 根据是否点亮加载不同的正面发光贴图
            net.neoforged.neoforge.client.model.generators.ModelFile model = models().orientable(
                    modelName,
                    modLoc("block/my_complex_machine_side"),
                    modLoc(lit ? "block/my_complex_machine_front_on" : "block/my_complex_machine_front"),
                    modLoc("block/my_complex_machine_top")
            );

            return net.neoforged.neoforge.client.model.generators.ConfiguredModel.builder()
                    .modelFile(model)
                    .rotationY(((int) dir.toYRot() + 180) % 360) // 根据朝向计算 Y 轴旋转度数
                    .build();
        });
    }
}
```
通过上述 DataGen 配置，运行 `gradlew runData` 将会自动生成对应的旋转与复合状态判定 JSON，完全无需手动拼接几十种状态坐标映射，同时确保了机器工作外观状态切换 100% 正确。

---

## 7. 声音配置数据生成 (SoundDefinitionsProvider)

手写 `sounds.json` 音频文件映射极易因为拼写错误导致音频加载失败。在 NeoForge 中，可以使用 `SoundDefinitionsProvider` 自动生成该 JSON 文件。

### 7.1 编写声音数据生成器类

```java
package com.tutorial.tutorialmod.datagen;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.sound.ModSounds;
import net.minecraft.data.PackOutput;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.common.data.ExistingFileHelper;
import net.neoforged.neoforge.common.data.SoundDefinition;
import net.neoforged.neoforge.common.data.SoundDefinitionsProvider;

public class ModSoundProvider extends SoundDefinitionsProvider {

    public ModSoundProvider(PackOutput output, ExistingFileHelper helper) {
        super(output, TutorialMod.MODID, helper);
    }

    @Override
    public void registerSounds() {
        // 注册并自动生成 "my_custom_sound" 的配置
        this.add(
                ModSounds.MY_CUSTOM_SOUND.get(), // 绑定的 SoundEvent Holder
                SoundDefinition.definition()
                        .withSubtitle("subtitles.tutorialmod.my_custom_sound") // 字幕键值
                        .with(
                                // 添加音频文件映射：指向 assets/tutorialmod/sounds/my_custom_sound_file.ogg
                                sound(ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "my_custom_sound_file"))
                                        .volume(0.8F) // 默认音量
                                        .pitch(1.0F)  // 默认音调
                                        .stream(false) // 是否为流式音乐 (大音乐设为 true)
                        )
        );
    }
}
```

### 7.2 在主数据生成类中注册该 Provider

在 `DataGenerators` 类的 `gatherData` 事件方法中进行挂载：
```java
// 挂载在 includeClient 分支（声音是客户端资源包的一部分）
generator.addProvider(
        event.includeClient(), 
        new ModSoundProvider(packOutput, existingFileHelper)
);
```
运行 `gradlew runData` 后，它将自动输出并合并出标准的 `assets/tutorialmod/sounds.json` 映射文件，确保了代码注册与资源绑定的 100% 吻合。
