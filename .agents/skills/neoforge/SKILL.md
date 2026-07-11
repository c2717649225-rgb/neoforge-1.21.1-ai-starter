---
name: neoforge_modding
description: Expert Minecraft Java 1.21.1 NeoForge modding. Provides Registries, DataComponents, Attachments, Ticking BlockEntities, Capabilities, Network Payloads, Mixins, and Compile Repair.
---

# NeoForge 1.21.1 Modding Core Engine

Whenever implementing features or resolving bugs, you MUST strictly follow this guide, copy the standard skeletons below, and complete the validation loop.

---

## 🚨 1. 1.21.1 Core Development Constraints (Pre-emptive Defenses)

| 1.20.4 and Before (DEPRECATED) | 1.21.1 NeoForge Standard (MANDATORY) | Impact of Violation |
| :--- | :--- | :--- |
| `stack.getOrCreateTag()`, `getTag()` | `stack.getOrDefault(DataComponents.CUSTOM_DATA, ...)` | **Compile Error** / NPE |
| `stack.setHoverName(name)` | `stack.set(DataComponents.CUSTOM_NAME, name)` | **Compile Error** |
| `PotionUtils.getPotion(stack)` | `stack.get(DataComponents.POTION_CONTENTS)` | **Compile Error** |
| `new AttributeModifier(UUID, ...)` | `new AttributeModifier(ResourceLocation, ...)` | **Compile Error** |
| `DeferredRegister.create(DATA_COMP...)`| `DeferredRegister.createDataComponents(...)` | **Compile Error** |
| `bus = Bus.MOD` on `@EventBusSubscriber` | Omit `bus`. Autorouted by event class | Deprecation Warning |
| `enchantable(int)` in properties | Removed. Managed via Data-driven datapacks | **Compile Error** |
| Static `.get()` in class init | Lazy wrap inside `Supplier` or method call | Bound registry NPE |
| 手写 JSON in resources | 100% DataGen in `src/main/java` (例外见 AGENTS.md) | Missing textures / Black blocks |

*   **Codec Sequence Rule**: Field order in `RecordCodecBuilder.create` MUST match the record constructor parameter order exactly. A mismatch causes silent save corruption.
*   **StreamCodec Limit**: `StreamCodec.composite` supports up to 6 fields. For 7+ fields, you MUST use `StreamCodec.of(encoder, decoder)` manually.
*   **Network Buffers**: When syncing `ItemStack`, you MUST declare `StreamCodec<RegistryFriendlyByteBuf, T>`, not `ByteBuf`. Use `ItemStack.LIST_STREAM_CODEC` for lists.
*   **Physical Client Isolation**: Classes referencing `net.minecraft.client` MUST be isolated under `.client` package and marked with `@EventBusSubscriber(value = Dist.CLIENT)`. NEVER import `net.minecraft.client` in common classes (Server crash).
*   **Datapack Registry Reference**: Datapack-driven registries (e.g. Enchantments, ConfiguredFeatures) CANNOT be registered via Java `DeferredRegister`. You MUST reference them using `ResourceKey` (e.g. `ResourceKey.create(Registries.ENCHANTMENT, ...)`).

---

## 💡 2. Standard Few-Shot Skeletons (Copy & Adapt)

> [!IMPORTANT]
> **占位符自适应规则**：
> 下列骨架中的 `{{MOD_GROUP}}`、`{{MODID}}` 和 `{{MAIN_CLASS}}` 均为符号占位符。在将代码写入项目前，您**必须**先从 `gradle.properties` 和 `neoforge.mods.toml` 读取真实的包路径与 Mod ID，并将占位符替换为当前项目的真实命名空间，严禁机械化复制。
> *注：`references/` 目录下的所有 markdown 指南代码示例中的包名（如 `com.tutorial.tutorialmod`）一律视为示例，同样必须在写入前按当前项目进行替换。*

### 2.1 Block, Item, BlockEntity & Tab Registration
```java
package {{MOD_GROUP}}.registry;

public class ModBlocks {
    public static final DeferredRegister.Blocks BLOCKS = DeferredRegister.createBlocks({{MAIN_CLASS}}.MODID);
    public static final DeferredRegister.Items ITEMS = DeferredRegister.createItems({{MAIN_CLASS}}.MODID);
    
    // Auto-registers BOTH Block and its BlockItem
    public static final DeferredBlock<Block> RUBY_BLOCK = BLOCKS.registerSimpleBlock("ruby_block", 
            BlockBehaviour.Properties.of().mapColor(MapColor.COLOR_RED).strength(5.0f).sound(SoundType.METAL));
    public static final DeferredItem<BlockItem> RUBY_BLOCK_ITEM = ITEMS.registerSimpleBlockItem(RUBY_BLOCK);
}

// In main mod class (Creative Mode Tab injection listener)
private void addCreative(BuildCreativeModeTabContentsEvent event) {
    if (event.getTabKey() == CreativeModeTabs.INGREDIENTS) event.accept(ModItems.RUBY.get());
}
```

### 2.2 Data Components & Attachments (Entity/Chunk custom data)
```java
package {{MOD_GROUP}}.registry;

public class ModData {
    // 1. Data Components (Stored on ItemStacks)
    public static final DeferredRegister.DataComponents COMPONENTS = 
        DeferredRegister.createDataComponents(Registries.DATA_COMPONENT_TYPE, {{MAIN_CLASS}}.MODID);
        
    public static final DeferredHolder<DataComponentType<?>, DataComponentType<Integer>> MANA = 
        COMPONENTS.registerComponentType("mana", builder -> builder.persistent(Codec.INT).networkSynchronized(ByteBufCodecs.INT));

    // 2. Attachments (Stored on Entities, BlockEntities, or Chunks)
    public static final DeferredRegister<AttachmentType<?>> ATTACHMENTS = 
        DeferredRegister.create(NeoForgeRegistries.ATTACHMENT_TYPES, {{MAIN_CLASS}}.MODID);
        
    public static final Supplier<AttachmentType<Integer>> PLAYER_MANA = ATTACHMENTS.register("player_mana",
        () -> AttachmentType.builder(() -> 0).serialize(Codec.INT).copyOnDeath().build());
        // Usage: player.getData(PLAYER_MANA.get()); player.setData(PLAYER_MANA.get(), 100);
}
```

### 2.3 Ticking BlockEntity with Capability & Save/Load (Machines)
```java
package {{MOD_GROUP}}.block.entity;

public class MyMachineBlockEntity extends BlockEntity {
    private final ItemStackHandler inventory = new ItemStackHandler(1) {
        @Override protected void onContentsChanged(int slot) { setChanged(); }
    };
    public MyMachineBlockEntity(BlockPos pos, BlockState state) {
        super(ModBlockEntities.MY_MACHINE.get(), pos, state);
    }
    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.put("Inventory", this.inventory.serializeNBT(registries)); // MUST pass registries
    }
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.inventory.deserializeNBT(registries, tag.getCompound("Inventory")); // MUST pass registries
    }
    public static void tick(Level level, BlockPos pos, BlockState state, MyMachineBlockEntity be) {
        if (level.isClientSide()) return;
        // Server tick logic
    }
}

// Capability Registration (Listen on MOD event bus in Main Class constructor)
// modEventBus.addListener(CapabilityRegistrar::registerCaps);
public class CapabilityRegistrar {
    public static void registerCaps(RegisterCapabilitiesEvent event) {
        event.registerBlockEntity(Capabilities.ItemHandler.BLOCK, 
            ModBlockEntities.MY_MACHINE.get(), (be, side) -> be.inventory);
    }
}
```

### 2.4 RegistryFriendly Custom Network Payload
```java
package {{MOD_GROUP}}.network;

public record SyncDataPayload(ItemStack stack, int value) implements CustomPacketPayload {
    public static final Type<SyncDataPayload> TYPE = new Type<>(ResourceLocation.fromNamespaceAndPath({{MAIN_CLASS}}.MODID, "sync"));
    
    // MUST use RegistryFriendlyByteBuf when transmitting ItemStack
    public static final StreamCodec<net.minecraft.network.RegistryFriendlyByteBuf, SyncDataPayload> STREAM_CODEC = StreamCodec.composite(
        ItemStack.STREAM_CODEC, SyncDataPayload::stack,
        net.minecraft.network.codec.ByteBufCodecs.VAR_INT, SyncDataPayload::value,
        SyncDataPayload::new
    );
    @Override public Type<? extends CustomPacketPayload> type() { return TYPE; }
}
```

---

## 📂 3. 100% Valid Reference Index (0-Latency Lookup)

Directly `read` the exact file path below based on your current task (DO NOT call `glob`):

### 🧪 Core Systems & Registrations
| Task Category | Target File Path to READ |
| :--- | :--- |
| NBT Replacement & Custom Data Components | `references/data_components.md` |
| BlockEntity Inventory, Capability & Attachments | `references/capabilities_attachments.md` |
| BlockEntity Base, Syncing & BlockState Saving | `references/block_entities.md` |
| Advanced decoupling & Concurrency Safeties | `references/architecture_design.md` |
| Config specs & TOML Reload Listeners | `references/configuration.md` |
| Mod Access Transformers Configuration | `references/access_transformers.md` |

### 🧱 Block, Item & Loot Customizations
| Task Category | Target File Path to READ |
| :--- | :--- |
| Custom Blocks, Redstone, Doors & Crops | `references/custom_blocks.md` |
| Custom Gear, Swords, Armor, Bows & Tools | `references/custom_gear.md` |
| Item Properties, 2D Animation & Hover properties| `references/item_properties.md` |
| BlockStates / ItemModels / LootTables / DataGen | `references/blockstates_models_datagen.md` |
| Custom Recipes Serializers & MapCodecs | `references/custom_recipes.md` |
| Crafting/Cooking/Smithing recipes DataGen | `references/recipes_standard_datagen.md` |
| Custom Tooltips, Lore & Formatting | `references/item_tooltips.md` |
| Custom Damage Types & Damage Sources | `references/damage_types.md` |
| Block Colors & Custom Color Handlers | `references/color_handlers.md` |
| Sound Events Registration & Triggering | `references/sounds.md` |

### 🚀 Advanced Features (Worldgen, Mobs & Mixins)
| Task Category | Target File Path to READ |
| :--- | :--- |
| Configured Features & Placed Ores Generation | `references/worldgen_ores.md` |
| ASM Mixin Injection, Redirect & Accessors | `references/mixins.md` |
| Mob Entities, Attributes & Tick-Throttling AI | `references/custom_entities.md` |
| Client-only Menus, Screens & Container GUIs | `references/menus_screens.md` |
| Client-only HUD overlay rendering layers | `references/hud_overlay_layers.md` |
| Custom Dimensions, Teleporters & Portals | `references/custom_dimensions.md` |
| Custom Biomes & Climate properties | `references/custom_biomes.md` |
| Villager Trades & Profession Leveling | `references/villager_trades.md` |
| Global Loot Modifiers (GLM) for drops | `references/global_loot_modifiers.md` |
| Custom Keybindings & Input mapping | `references/keybindings_input.md` |
| JEI Mod Integration & Recipes displaying | `references/jei_integration.md` |
| Event System listeners & Priorities | `references/event_system.md` |
| Custom Particles & Particle Providers | `references/custom_particles.md` |
| Custom Fluids, Fluid Tanks & Buckets | `references/custom_fluids.md` |
| Datapack-driven Save Files & WorldData | `references/saved_data.md` |
| DataPack Custom Enchantments & RegistrySetBuilder | `references/custom_enchantments.md` |
| Potion Effects & Alchemical Brewing | `references/potions_brewing.md` |
| Advancements / Trigger Criteria DataGen | `references/advancements_datagen.md` |
| Custom Entity Models (.bbmodel) & Renderers | `references/custom_entity_models.md` |
| BlockEntity Special Renderers (BER) | `references/block_entity_renderers.md` |
| Custom Commands & Argument Parsers | `references/custom_commands.md` |
| Data Maps & Registry-driven metadata | `references/data_maps.md` |

| Blueprints & Examples | Target File Path to READ |
| :--- | :--- |
| Standard Items/Blocks registration | `examples/registration_example.md` |
| Registering Creative Tab | `examples/creative_tab_config_example.md` |
| Model, State, Block Loot DataGen | `examples/datagen_example.md` |
| Crafting Recipe, Tags DataGen | `examples/recipes_tags_example.md` |
| Multi-loader platform decoupling | `examples/platform_decoupling_example.md` |

---

## 🛠️ 4. Compulsory Toolchain Integration Loop (Validation)

To ensure high-quality delivery, you MUST integrate these local tools during your development:

1. **Verify via MCP**: You MUST call the local MCP tool `search_class` or `grep_source` to index and read the authoritative source code from Gradle caches immediately instead of guessing.
2. **Compile-and-Repair Loop**: Every time you modify or write a Java file, you **MUST** run the 自检脚本 BEFORE presenting changes to the user:
   * **无注册项或 DataGen Provider 变更时**：仅运行 `python .agents/skills/workspace_setup/scripts/compile_and_repair.py`（执行 `compileJava`，退出码 0 即为通过）。
   * **有注册项或 DataGen 相关更新时**：运行 `python .agents/skills/workspace_setup/scripts/compile_and_repair.py --with-data`（串行编译并触发 `runData` 更新 JSON 资源）。
