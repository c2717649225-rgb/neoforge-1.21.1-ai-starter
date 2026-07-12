# NeoForge 1.21.1 高阶自定义方块（体积、朝向与充水状态）指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 本参考指南中所有示例代码的 `com.tutorial.tutorialmod` 均为占位。写入前必须根据 `gradle.properties` 的真实 Group ID，并执行 `init_workspace.py` 重构为当前项目的真实命名空间，严禁硬编码提交。

在 Minecraft 中，超过 90% 的设备、家具、祭坛、电缆或者镂空防爆网格等，都不是标准的正方体（1.0 x 1.0 x 1.0）。这些方块需要具备以下高阶特性：

1.  **自定义体积 (VoxelShape)**：只对模型实际存在的几何范围进行碰撞和遮挡判定（允许中空）。
2.  **放置朝向旋转 (FACING)**：方块在放置时，正面能始终朝向玩家。
3.  **可充水特性 (Waterlogging)**：当方块放在水下时，水能流过并充满中空体积，而不是在水底生成一个充满空气的透明方框。

以下是合并了上述三大特性的高阶自定义方块开发标准模版。

---

## 1. 编写高阶方块类 (VoxelShape + FACING + SimpleWaterloggedBlock)

方块需要实现 `SimpleWaterloggedBlock` 接口，并声明 `FACING` 和 `WATERLOGGED` 状态属性：

```java
package com.tutorial.tutorialmod.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.SimpleWaterloggedBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.level.material.FluidState;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.minecraft.world.phys.shapes.VoxelShape;

public class HighEndCustomBlock extends Block implements SimpleWaterloggedBlock {

    public static final DirectionProperty FACING = HorizontalDirectionalBlock.FACING;
    // 1. 声明 BooleanProperty 代表充水状态
    public static final BooleanProperty WATERLOGGED = BlockStateProperties.WATERLOGGED;

    // 2. 使用 Block.box(minX, minY, minZ, maxX, maxY, maxZ) 声明自定义体积
    // 盒装坐标从 0.0 ~ 16.0，这代表一个底盘 12x12，高 14 的中空祭坛底座体积
    private static final VoxelShape SHAPE = Block.box(2.0D, 0.0D, 2.0D, 14.0D, 14.0D, 14.0D);

    public HighEndCustomBlock(BlockBehaviour.Properties properties) {
        super(properties);
        // 初始化默认状态：朝向北方，且默认未充水
        this.registerDefaultState(this.stateDefinition.any()
                .setValue(FACING, Direction.NORTH)
                .setValue(WATERLOGGED, false));
    }

    // 3. 重写此方法，将自定义的体积形状返回给引擎用于射线检测和碰撞计算
    @Override
    public VoxelShape getShape(BlockState state, BlockGetter level, BlockPos pos, CollisionContext context) {
        // 如果方块的体积在不同朝向下完全一致，则直接返回静态常量。
        // 如果随朝向改变而改变，可以在此 state.getValue(FACING) 进行分支返回不同的 box 变形体。
        return SHAPE;
    }

    // 4. 当方块放置时的状态计算 (计算玩家站立朝向，并检测放置处是否有水源)
    @Override
    public BlockState getStateForPlacement(BlockPlaceContext context) {
        FluidState fluidState = context.getLevel().getFluidState(context.getClickedPos());
        // 判断放置位置的流体是否是水，如果是，则自动将 WATERLOGGED 设为 true
        boolean isWater = fluidState.getType() == Fluids.WATER;

        return this.defaultBlockState()
                .setValue(FACING, context.getHorizontalDirection().getOpposite()) // 朝向玩家的对面
                .setValue(WATERLOGGED, isWater);
    }

    // 5. 核心流体更新：当方块充水时，告知渲染引擎以水的物理性质渲染其背景流体
    @Override
    public FluidState getFluidState(BlockState state) {
        return state.getValue(WATERLOGGED) ? Fluids.WATER.getSource(false) : super.getFluidState(state);
    }

    // 6. 重写状态连接更新：当周围方块或流体发生改变时触发（例如水流过该方块，或者水被排干）
    @Override
    public BlockState updateShape(BlockState state, Direction direction, BlockState neighborState, 
                                  LevelAccessor level, BlockPos currentPos, BlockPos neighborPos) {
        if (state.getValue(WATERLOGGED)) {
            // 如果已经被充水，在周围方块改变时，向世界排程一个水流扩散更新，保证水流正确蔓延
            level.scheduleTick(currentPos, Fluids.WATER, Fluids.WATER.getTickDelay(level));
        }
        return super.updateShape(state, direction, neighborState, level, currentPos, neighborPos);
    }

    // 7. 将我们的两个状态值注入到 BlockState 生成定义中
    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, WATERLOGGED);
    }
}
```

---

## 2. 物理效果避坑总结

*   **渲染遮挡阻光 (Opacity)**：默认情况下，非完整立方体方块可能不需要阻挡视线或计算全阴影。请在注册方块属性时指定 `.noOcclusion()`，否则周围相邻的方块会因为渲染引擎的隐藏面消除算法（Culling）而变成黑色透明空洞：
    ```java
    BlockBehaviour.Properties.of()
        .strength(3.0F)
        .noOcclusion() // 必须添加：告知引擎此方块不完全遮光，允许渲染相邻面
    ```
*   **VoxelShape 的坐标定义范围**：`Block.box(minX, minY, minZ, maxX, maxY, maxZ)` 中的坐标点数值取值范围理论上应当在 `0` 到 `16` 之间。如果定义超过这个范围（如 `18.0D`），则代表该方块的物理盒超出了标准的 1 格大小限制。虽然 Minecraft 允许这样做，但会导致与活塞推动或区块边界产生未知的渲染穿模 Bug，除非是大型多方块结构，否则请控制在 0 到 16 内。
*   **水流 Tick 更新**：在 `updateShape` 中如果方块充水，调用 `level.scheduleTick(currentPos, Fluids.WATER, ...)` 是非常必要的。如果不排程此 Tick，当有水流漫过方块时，水在视觉上可能无法正确流入方块体积内部，造成流体贴图悬空截断。

---

## 3. 1.21.1 镂空半透明方块渲染机制

在 1.21.1 中，**彻底废除**了 Java 代码端配置渲染层（如 `ItemBlockRenderTypes.setRenderLayer`）的旧机制。
方块的半透明（如玻璃）或镂空（如树叶、草丛）效果，现在**必须直接在方块的模型 JSON 文件中定义**，或者在 DataGen 的 `BlockStateProvider` 中设置。

### 3.1 模型 JSON 声明
在方块的 `assets/tutorialmod/models/block/xxx.json` 模型文件中直接增加 `"render_type"` 字段：
```json
{
  "parent": "minecraft:block/cube_all",
  "render_type": "minecraft:cutout",
  "textures": {
    "all": "tutorialmod:block/custom_glass"
  }
}
```
*提示：镂空贴图通常使用 `"minecraft:cutout"`，半透明贴图（有透明度变化通道）使用 `"minecraft:translucent"`。*

---

## 4. 1.21.1 新版右键交互方法拆分 (Block Interaction)

1.21.1 彻底抛弃了传统的单参 `use(...)` 右键交互方法，将其重构拆分为两个具有明确职责的分支：

### 4.1 手持物品右键交互 (`useItemOn`) 与 空手右键交互 (`useWithoutItem`)
```java
    // 1. 当玩家手持物品右键该方块时触发 (注意：必须返回 ItemInteractionResult)
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, 
                                               Player player, InteractionHand hand, BlockHitResult hitResult) {
        if (!level.isClientSide()) {
            if (stack.is(Items.DIAMOND)) {
                // 消耗玩家手持的一个钻石并执行逻辑
                if (!player.getAbilities().instabuild) {
                    stack.shrink(1);
                }
                level.setBlockAndUpdate(pos, ModBlocks.RUBY_BLOCK.get().defaultBlockState());
                return ItemInteractionResult.SUCCESS; // 消耗并处理了物品，交互成功
            }
        }
        // 如果手持的不是钻石，将交互动作投递给空手交互分支 (useWithoutItem) 执行
        return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }

    // 2. 当 useItemOn 返回 PASS_TO_DEFAULT_BLOCK_INTERACTION 时触发 (返回传统的 InteractionResult)
    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, 
                                                Player player, BlockHitResult hitResult) {
        if (!level.isClientSide()) {
            player.sendSystemMessage(Component.literal("你空手右击了该方块！"));
        }
        return InteractionResult.sidedSuccess(level.isClientSide());
    }
```

---

## ⚠️ 1.21.1 自定义方块高频编译错误防御与自愈

*   **编译报错**：`method does not override or implement a method from a supertype` (在 `use` 方法上)
    *   ❌ 错误：在自定义方块中强行覆写 1.20 的 `use(BlockState, Level, BlockPos, Player, InteractionHand, BlockHitResult)`。
    *   ✅ 修正：在 1.21.1 中此方法已被完全删除。必须改写为覆写 `useItemOn` 和 `useWithoutItem`（详见第 4 节）。
*   **编译报错**：`cannot find symbol: class VoxelShapes location: package net.minecraft.world.phys.shapes`
    *   ❌ 错误：`import net.minecraft.world.phys.shapes.VoxelShapes;`。
    *   ✅ 修正：Mojang 官方映射中，碰撞箱合并工具类名称是 **`Shapes`**（如 `Shapes.or(...)`、`Shapes.empty()`），不存在 `VoxelShapes`。
*   **编译报错**：`cannot find symbol: constructor StairBlock(BlockState, Properties)`
    *   ❌ 错误：`new StairBlock(properties)`。
    *   ✅ 修正：1.21.1 的 `StairBlock` 构造函数签名强制更改，第一参数必须为基础方块的默认状态：
        ```java
        super(ModBlocks.BASE_BLOCK.get().defaultBlockState(), properties);
        ```
*   **编译报错**：`custom plant class is not abstract and does not override abstract method codec() in BushBlock`
    *   ❌ 错误：自定义草、花等继承 `BushBlock` (或 `CropBlock`) 的子类未重写 `codec()`。
    *   ✅ 修正：1.21.1 所有的方块行为子类必须覆写 `codec()` 返回其构造编解码器。
        ```java
        public static final MapCodec<MyFlowerBlock> CODEC = simpleCodec(MyFlowerBlock::new);

        @Override
        protected MapCodec<? extends BushBlock> codec() {
            return CODEC;
        }
        ```

