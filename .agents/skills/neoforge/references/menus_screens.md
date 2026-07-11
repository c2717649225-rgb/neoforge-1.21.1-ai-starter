# NeoForge 1.21.1 容器与 GUI 屏幕 (Menus & Screens) 参考指南

制作带界面的方块（如自定义熔炉、发电机、储物箱等）涉及**双端通信机制**：
* **服务端 (Server)**：管理容器逻辑（`AbstractContainerMenu`），负责处理物品槽的数据交互、槽位判定、Shift 点击转移等核心逻辑。
* **客户端 (Client)**：管理视觉渲染（`AbstractContainerScreen`），负责绘制背景贴图、绘制进度条、处理鼠标交互和渲染 Tooltips。

---

## 1. 注册 `MenuType`（使用 `IContainerFactory`）

如果界面在初始化时需要知道对应的方块位置（`BlockPos`）或其它数据，必须使用 `IContainerFactory` 在客户端构造 Menu 时读取网络缓存。

```java
package com.tutorial.tutorialmod.menu;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.world.inventory.MenuType;
import net.neoforged.neoforge.common.extensions.IMenuTypeExtension;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModMenuTypes {
    public static final DeferredRegister<MenuType<?>> MENU_TYPES =
            DeferredRegister.create(Registries.MENU, TutorialMod.MODID);

    // 注册自定义机器的 MenuType (使用 IMenuTypeExtension.create 绑定 IContainerFactory)
    public static final DeferredHolder<MenuType<?>, MenuType<MyMachineMenu>> MY_MACHINE_MENU =
            MENU_TYPES.register("my_machine_menu", () ->
                    IMenuTypeExtension.create((windowId, inv, data) -> {
                        // 在客户端读取服务端通过 writeExtraData 发送的 BlockPos
                        return new MyMachineMenu(windowId, inv, data.readBlockPos());
                    })
            );
}
```

---

## 2. 服务端容器类 (`AbstractContainerMenu`)

容器类主要负责分配物品槽位 (Slots)。槽位索引的划分非常关键，也是实现 Shift-Click（快捷移动）逻辑的基础。

```java
package com.tutorial.tutorialmod.menu;

import com.tutorial.tutorialmod.block.entity.MyMachineBlockEntity;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.*;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.items.IItemHandler;
import net.neoforged.neoforge.items.SlotItemHandler;

public class MyMachineMenu extends AbstractContainerMenu {
    private final MyMachineBlockEntity blockEntity;
    private final ContainerLevelAccess levelAccess;

    // 客户端构造器 (通过 IContainerFactory 调用)
    public MyMachineMenu(int containerId, Inventory playerInv, BlockPos pos) {
        this(containerId, playerInv, (MyMachineBlockEntity) playerInv.player.level().getBlockEntity(pos));
    }

    // 主构造器 (双端共用)
    public MyMachineMenu(int containerId, Inventory playerInv, MyMachineBlockEntity blockEntity) {
        super(ModMenuTypes.MY_MACHINE_MENU.get(), containerId);
        this.blockEntity = blockEntity;
        this.levelAccess = ContainerLevelAccess.create(blockEntity.getLevel(), blockEntity.getBlockPos());

        // 1. 绑定机器本身的物品槽 (假设机器有 1 个输入槽和 1 个输出槽，使用 Capability/Attachment 里的 IItemHandler)
        IItemHandler handler = blockEntity.getItemHandler(null);
        if (handler != null) {
            // 参数：数据源, 槽位索引, 屏幕上的 X 坐标, Y 坐标
            this.addSlot(new SlotItemHandler(handler, 0, 56, 35)); // 输入槽
            this.addSlot(new SlotItemHandler(handler, 1, 116, 35)); // 输出槽
        }

        // 2. 绑定玩家的主背包 (共 3 行，每行 9 格，索引 9-35)
        for (int row = 0; row < 3; ++row) {
            for (int col = 0; col < 9; ++col) {
                this.addSlot(new Slot(playerInv, col + row * 9 + 9, 8 + col * 18, 84 + row * 18));
            }
        }

        // 3. 绑定玩家的快捷栏 (共 9 格，索引 0-8)
        for (int col = 0; col < 9; ++col) {
            this.addSlot(new Slot(playerInv, col, 8 + col * 18, 142));
        }
    }

    @Override
    public boolean stillValid(Player player) {
        // 安全检测：如果玩家离机器太远，自动关闭界面
        return stillValid(this.levelAccess, player, blockEntity.getBlockState().getBlock());
    }

    // 4. Shift 点击快速移动槽位算法 (防死锁八股文代码)
    // 槽位索引划分：0-1 为机器槽，2-28 为玩家背包，29-37 为玩家快捷栏
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        ItemStack itemstack = ItemStack.EMPTY;
        Slot slot = this.slots.get(index);
        
        if (slot != null && slot.hasItem()) {
            ItemStack itemstack1 = slot.getItem();
            itemstack = itemstack1.copy();
            
            if (index < 2) { // 机器内部槽位 -> 玩家背包或快捷栏
                if (!this.moveItemStackTo(itemstack1, 2, 38, true)) {
                    return ItemStack.EMPTY;
                }
            } else { // 玩家背包或快捷栏 -> 机器内部槽位
                // 优先移动到机器输入槽 (索引 0)
                if (!this.moveItemStackTo(itemstack1, 0, 1, false)) {
                    // 背包与快捷栏之间互转
                    if (index < 29) { // 玩家背包 -> 快捷栏
                        if (!this.moveItemStackTo(itemstack1, 29, 38, false)) {
                            return ItemStack.EMPTY;
                        }
                    } else { // 快捷栏 -> 玩家背包
                        if (!this.moveItemStackTo(itemstack1, 2, 29, false)) {
                            return ItemStack.EMPTY;
                        }
                    }
                }
            }

            if (itemstack1.isEmpty()) {
                slot.setByPlayer(ItemStack.EMPTY);
            } else {
                slot.setChanged();
            }

            if (itemstack1.getCount() == itemstack.getCount()) {
                return ItemStack.EMPTY;
            }

            slot.onTake(player, itemstack1);
        }

        return itemstack;
    }
}
```

---

## 3. 客户端屏幕类 (`AbstractContainerScreen`)

屏幕类负责 UI 的动态绘制和交互显示。

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.menu.MyMachineMenu;
import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.renderer.GameRenderer;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

public class MyMachineScreen extends AbstractContainerScreen<MyMachineMenu> {
    // 绑定 UI 的纹理贴图路径 (assets/tutorialmod/textures/gui/container/my_machine.png)
    private static final ResourceLocation TEXTURE =
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "textures/gui/container/my_machine.png");

    public MyMachineScreen(MyMachineMenu menu, Inventory playerInv, Component title) {
        super(menu, playerInv, title);
        this.imageWidth = 176;  // 贴图宽度
        this.imageHeight = 166; // 贴图高度
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        this.renderBackground(graphics, mouseX, mouseY, partialTick); // 渲染半透明背景
        super.render(graphics, mouseX, mouseY, partialTick);
        this.renderTooltip(graphics, mouseX, mouseY);                // 渲染物品悬浮提示
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float partialTick, int mouseX, int mouseY) {
        RenderSystem.setShader(GameRenderer::getPositionTexShader);
        RenderSystem.setShaderColor(1.0F, 1.0F, 1.0F, 1.0F);
        RenderSystem.setShaderTexture(0, TEXTURE);

        // 计算 UI 在屏幕中央渲染的起算点
        int x = (this.width - this.imageWidth) / 2;
        int y = (this.height - this.imageHeight) / 2;

        // 绘制背景大纹理
        graphics.blit(TEXTURE, x, y, 0, 0, this.imageWidth, this.imageHeight);

        // 动态绘制进度条示例 (假设机器能量有变化，在这里计算并遮罩绘制)
        // int progress = this.menu.getScaledProgress();
        // graphics.blit(TEXTURE, x + 79, y + 34, 176, 14, progress, 17);
    }

    @Override
    protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        // 渲染前景文字（标题和玩家背包名称）
        graphics.drawString(this.font, this.title, this.titleLabelX, this.titleLabelY, 4210752);
        graphics.drawString(this.font, this.playerInventoryTitle, this.inventoryLabelX, this.inventoryLabelY, 4210752);
    }
}
```

---

## 4. 方块实体集成与打开界面

方块实体必须实现 NeoForge 的 `IMenuProvider` 接口以支持网络发送额外数据：

```java
package com.tutorial.tutorialmod.block.entity;

import com.tutorial.tutorialmod.menu.MyMachineMenu;
import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import org.jetbrains.annotations.Nullable;

public class MyMachineBlockEntity extends BlockEntity implements MenuProvider {

    public MyMachineBlockEntity(BlockPos pos, BlockState state) {
        super(ModBlockEntities.MY_MACHINE.get(), pos, state);
    }

    @Override
    public Component getDisplayName() {
        return Component.translatable("container.tutorialmod.my_machine");
    }

    @Nullable
    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory playerInv, Player player) {
        // 实例化服务端 Menu 容器
        return new MyMachineMenu(containerId, playerInv, this);
    }

    // 关键：通过网络缓冲区将 BlockPos 发送给客户端构造 Menu (使用 NeoForge 1.21.1 专用的 writeClientSideData)
    @Override
    public void writeClientSideData(net.minecraft.world.inventory.AbstractContainerMenu menu, net.minecraft.network.RegistryFriendlyByteBuf buffer) {
        buffer.writeBlockPos(this.worldPosition);
    }
}
```

在方块的右键交互事件中执行打开界面：
```java
// 在 Block 类的 useWithoutItem 方法中：
if (!level.isClientSide()) {
    BlockEntity be = level.getBlockEntity(pos);
    if (be instanceof MyMachineBlockEntity machine) {
        // ServerPlayer.openMenu 会自动序列化 writeExtraData 并通知客户端打开界面
        player.openMenu(machine);
    }
}
```

---

## 5. 客户端 Screen 绑定注册

所有的 Screen 绑定都必须在客户端事件总线上进行注册：

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.menu.ModMenuTypes;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterMenuScreensEvent;

@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT)
public class ClientMenuScreenRegistrar {

    @SubscribeEvent
    public static void registerScreens(RegisterMenuScreensEvent event) {
        // 绑定注册 MyMachineMenu 关联的界面为 MyMachineScreen
        event.register(ModMenuTypes.MY_MACHINE_MENU.get(), MyMachineScreen::new);
    }
}
```

---

## 6. 使用 ContainerData 进行动态数值同步（防溢出拆分）

在 GUI 界面中，经常需要同步动态数值（例如：机器的冶炼进度、发电机剩余电量）。Minecraft 原版提供的解决方案是 `ContainerData` 数据通道。

> [!IMPORTANT]
> **原版网络封包限制**：原版底层同步 `ContainerData` 的数据包（`ClientboundContainerSetDataPacket`）在网络传输时会将值强制缩剪为 **16 位有符号短整型（`short`，范围为 -32768 ~ 32767）**。
> 如果您的电能或进度最大值超过了 32767（如 100,000 电量），直接写入会发生**数据截断溢出**，在客户端界面显示成错乱的负数。

### 6.1 工业级解决方案：32位整型拆分为双16位短整型

我们可以用**两个数据通道槽位**组合来同步一个 32 位的 `int` 变量。

#### 1. 在方块实体 (Block Entity) 中声明和拆分数据

```java
import net.minecraft.world.inventory.ContainerData;

public class MyMachineBlockEntity extends BlockEntity {
    private int energy = 0; // 32位整型，可能高达数百万
    
    // 声明一个包含 2 个插槽的数据通道 (0号存放低16位，1号存放高16位)
    protected final ContainerData dataAccess = new ContainerData() {
        @Override
        public int get(int index) {
            switch (index) {
                case 0:
                    // 提取低 16 位
                    return (short) (MyMachineBlockEntity.this.energy & 0xFFFF);
                case 1:
                    // 提取高 16 位并移位
                    return (short) ((MyMachineBlockEntity.this.energy >> 16) & 0xFFFF);
                default:
                    return 0;
            }
        }

        @Override
        public void set(int index, int value) {
            // 在写入时（主要由客户端收到同步包时触发），重构 32 位整型
            switch (index) {
                case 0:
                    // 使用 0xFFFF 遮罩消除符号位拓展污染
                    MyMachineBlockEntity.this.energy = (MyMachineBlockEntity.this.energy & 0xFFFF0000) | (value & 0xFFFF);
                    break;
                case 1:
                    MyMachineBlockEntity.this.energy = (MyMachineBlockEntity.this.energy & 0x0000FFFF) | ((value & 0xFFFF) << 16);
                    break;
            }
        }

        @Override
        public int getCount() {
            return 2; // 总插槽数为 2
        }
    };
    
    // ... 将 dataAccess 传递给 Menu 构造器
}
```

#### 2. 在容器 (Menu) 中注册数据通道

在服务端的 Menu 构造器中注册该数据通道，以便游戏底层的网络代码自动同步：

```java
public class MyMachineMenu extends AbstractContainerMenu {
    private final ContainerData data;

    // 服务端构造器
    public MyMachineMenu(int containerId, Inventory playerInv, MyMachineBlockEntity blockEntity) {
        super(ModMenuTypes.MY_MACHINE_MENU.get(), containerId);
        this.data = blockEntity.dataAccess;
        
        // 关键：在 Menu 中注册数据通道，绑定后服务端会自动监控其 get() 变化并发送包
        this.addDataSlots(this.data);
    }
    
    // 提供给客户端 Screen 的快捷数据读取方法
    public int getEnergy() {
        // 在客户端读取时，利用位运算重构还原 32 位大整数
        int low = this.data.get(0);
        int high = this.data.get(1);
        
        // 注意：low & 0xFFFF 遮罩绝对不能省！Java 会自动将 short 强转为 int，若低16位最高位为1，不加遮罩会导致符号位自动填充 1 污染高位
        return (high << 16) | (low & 0xFFFF);
    }
}
```

#### 3. 在客户端 (Screen) 中渲染读取的值

在 `MyMachineScreen` 的 `renderBg` 方法中，可以直接通过 `menu.getEnergy()` 渲染出无精度损耗的高精度进度条或电量值：

```java
@Override
protected void renderBg(GuiGraphics graphics, float partialTick, int mouseX, int mouseY) {
    // ... 绘制背景
    int currentEnergy = this.menu.getEnergy();
    // 渲染电能槽...
}
```
通过这种**位移和遮罩防污染拆分方案**，可以完全免去手写网络发包的麻烦，实现对高达 2,147,483,647 大数值的动态零延迟同步。

---

## 7. 高性能机器工作状态 (LIT) 切换规范

科技或熔炼机器在工作时（如发电机燃烧、熔炉冶炼），需要改变方块外观（如发出亮光、正面材质发红、冒烟）。在 Minecraft 中，这通过方块状态属性 `BlockStateProperties.LIT`（是否点亮）实现。

> [!WARNING]
> **性能致命红线**：
> 改变方块状态（`level.setBlock`）会强制客户端**重新渲染当前区块（Chunk Redraw）**。
> 如果您在方块实体的 `tick()` 逻辑中，每 tick 都无条件调用 `level.setBlock` 切换状态，**会导致客户端帧率（FPS）瞬间跌个位数，产生极其严重的卡顿！**
> 必须使用以下**“差值防抖切换算法”**：仅在状态真正发生变化（如从工作切换为停机，或反之）的 tick，才调用一次 `setBlock`。

### 7.1 朝向与 LIT 机器方块定义

在方块类中，除了注册 `FACING`（朝向），还要注册 `LIT`（状态），并根据 `LIT` 值动态调整方块发光度：

```java
package com.tutorial.tutorialmod.block;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.HorizontalDirectionalBlock;
import net.minecraft.world.level.block.state.BlockBehaviour;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;

public class MyMachineBlock extends Block {
    public static final DirectionProperty FACING = HorizontalDirectionalBlock.FACING;
    // 1. 声明 LIT 状态属性
    public static final BooleanProperty LIT = BlockStateProperties.LIT;

    public MyMachineBlock(Properties properties) {
        // 在属性构建中：根据 LIT 状态动态返回亮度值。若 LIT 为 true 提供 13 级光照，否则为 0
        super(properties.lightLevel(state -> state.getValue(LIT) ? 13 : 0));
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH).setValue(LIT, false));
    }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(FACING, LIT); // 同时注入两个状态
    }

    // 2. 客户端粒子特效渲染 (仅在物理客户端触发，高频 tick)
    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        // 仅当机器处于点亮（工作）状态时，才在正面生成燃烧烟雾粒子
        if (state.getValue(LIT)) {
            double x = pos.getX() + 0.5D;
            double y = pos.getY();
            double z = pos.getZ() + 0.5D;

            if (random.nextDouble() < 0.1D) {
                // 播放温和的炉子噼啪声
                level.playLocalSound(x, y, z, SoundEvents.FURNACE_FIRE_CRACKLE, SoundSource.BLOCKS, 1.0F, 1.0F, false);
            }

            Direction direction = state.getValue(FACING);
            Direction.Axis axis = direction.getAxis();
            double offset = random.nextDouble() * 0.6D - 0.3D;
            
            // 根据朝向，计算正面面板的位置偏移，生成烟雾与小火花粒子
            double offX = axis == Direction.Axis.X ? direction.getStepX() * 0.52D : offset;
            double offY = random.nextDouble() * 6.0D / 16.0D;
            double offZ = axis == Direction.Axis.Z ? direction.getStepZ() * 0.52D : offset;

            level.addParticle(ParticleTypes.SMOKE, x + offX, y + offY, z + offZ, 0.0D, 0.0D, 0.0D);
            level.addParticle(ParticleTypes.FLAME, x + offX, y + offY, z + offZ, 0.0D, 0.0D, 0.0D);
        }
    }
}
```

### 7.2 方块实体端的“防抖状态切换”

在机器的 Tick 逻辑中，实现性能安全的切换代码：

```java
package com.tutorial.tutorialmod.block.entity;

import com.tutorial.tutorialmod.block.MyMachineBlock;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.entity.BlockEntity;

public class MyMachineBlockEntity extends BlockEntity {
    private int burnTime = 0; // 剩余工作时间

    public MyMachineBlockEntity(BlockPos pos, BlockState state) {
        super(MyBlockEntities.MY_MACHINE_TYPE.get(), pos, state);
    }

    public void tickServer() {
        boolean isWorking = this.burnTime > 0;
        boolean hasChanged = false; // 用于追踪内部数据是否发生变化
        
        if (isWorking) {
            this.burnTime--;
            hasChanged = true; // 只要消耗了燃料/进度，就必须标记变化！
        }

        BlockState currentState = this.getBlockState();
        
        // 性能防抖核心：仅当“当前 BlockState 中的 LIT 状态”与“机器实际运行状态 (isWorking)”不一致时，才调用一次 setBlock
        if (currentState.getValue(MyMachineBlock.LIT) != isWorking) {
            
            // 标志位 3 代表：同步给客户端，且通知周围方块更新，同时触发区块重绘
            this.level.setBlock(
                    this.worldPosition, 
                    currentState.setValue(MyMachineBlock.LIT, isWorking), 
                    3
            );
            hasChanged = true;
        }

        // 严重警告：如果内部变量（如 burnTime）发生了变化，必须调用 setChanged()！
        // 否则如果在此时区块卸载或服务器重启，burnTime 的消耗将不会保存到磁盘，导致刷燃料/刷电刷进度的恶性 Bug！
        if (hasChanged) {
            this.setChanged(); 
        }
    }
}
```
通过这种**状态属性对比切换算法**，您的机器不仅拥有完美的火焰音效和冒烟粒子，还能保障服务器和客户端 100% 毫无卡顿地运行。
