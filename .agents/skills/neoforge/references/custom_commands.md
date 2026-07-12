# NeoForge 1.21.1 游戏内自定义指令 (Commands) 指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


在模组开发过程中，注册自定义游戏内指令（Commands）是进行**数据调试、管理员管理、或者触发特定测试动作**最有效的方式。

Minecraft 官方内置了 **Brigadier** 命令行语法解析库。在 1.21.1 中，我们需要在游戏事件总线上监听指令注册事件，并使用 Brigadier 构造出分支指令树。

---

## 1. 注册指令事件 (RegisterCommandsEvent)

指令是纯服务端的逻辑结构。我们需要在 **GAME 事件总线**（`NeoForge.EVENT_BUS`）上监听 `RegisterCommandsEvent` 事件，获取 `CommandDispatcher` 进行注册。

以下是实现 `/tutorialmod <setlevel|getlevel> <value>` 指令的标准实现：

```java
package com.tutorial.tutorialmod.command;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

@EventBusSubscriber(modid = TutorialMod.MODID)
public class ModCommandRegistrar {

    @SubscribeEvent
    public static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();

        // 使用 Commands.literal 开始构建指令树
        dispatcher.register(
                Commands.literal("tutorialmod")
                        // 权限等级要求：2级代表普通管理员 (1为无视领地，2为作弊指令，3为封禁指令，4为控制台)
                        .requires(source -> source.hasPermission(2))
                        
                        // 分支一：子命令 "setlevel" 后跟一个整数参数 "level"
                        .then(Commands.literal("setlevel")
                                .then(Commands.argument("level", IntegerArgumentType.integer(0, 100)) // 限制参数范围 0 ~ 100
                                        .executes(context -> {
                                            // 执行具体逻辑，并获取玩家参数
                                            int levelValue = IntegerArgumentType.getInteger(context, "level");
                                            return executeSetLevel(context.getSource(), levelValue);
                                        })
                                )
                        )
                        
                        // 分支二：子命令 "getlevel"
                        .then(Commands.literal("getlevel")
                                .executes(context -> {
                                    return executeGetLevel(context.getSource());
                                })
                        )
        );
    }

    private static int executeSetLevel(CommandSourceStack source, int levelValue) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        // 1. 获取执行命令的玩家
        ServerPlayer player = source.getPlayerOrException();

        // 2. 在这里执行您的核心业务逻辑（例如修改玩家或宠物的战斗等级）
        // MyAttachmentData.setLevel(player, levelValue);

        // 3. 向执行者发送绿色（AQUA）成功回执（第二个参数为 false 表示不广播给其他管理员）
        source.sendSuccess(() -> Component.translatable("command.tutorialmod.setlevel.success", levelValue), false);
        
        return 1; // 返回正数代表执行成功，返回 0 或负数代表失败
    }

    private static int executeGetLevel(CommandSourceStack source) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        ServerPlayer player = source.getPlayerOrException();
        
        int currentLevel = 10; // 假数据，通常从玩家能力附件中读取

        source.sendSuccess(() -> Component.translatable("command.tutorialmod.getlevel.result", currentLevel), false);
        return 1;
    }
}
```

---

## 2. 常用 Brigadier 参数类型 (Arguments)

Brigadier 提供了极其强大的参数自动补全和格式校验器，可以防止非法参数传入执行体：

### 2.1 数值类型
*   **整数**：`IntegerArgumentType.integer(min, max)`（限制最大/最小值）。
*   **浮点数**：`DoubleArgumentType.doubleArg(min, max)` / `FloatArgumentType.floatArg(min, max)`。

### 2.2 游戏实体与玩家参数 (EntityArgument)
*   **单个玩家**：`EntityArgument.player()`。
*   **多个玩家**：`EntityArgument.players()`。
*   **任意实体（含怪物）**：`EntityArgument.entity()`。
*   *在执行体中提取*：
    ```java
    // 提取单个玩家
    ServerPlayer targetPlayer = EntityArgument.getPlayer(context, "player_argument_name");
    ```

### 2.3 文本与字符串类型
*   **单个单词**：`StringArgumentType.word()` (如 `my_arg`，不带空格)。
*   **带双引号的短语**：`StringArgumentType.string()`。
*   **整行文本（支持空格）**：`StringArgumentType.greedyString()` (必须放在命令行的最后一位，会吞噬后面所有的输入，适合输入公告消息等)。

---

## 3. 本地化翻译配置 (zh_cn.json)

指令回执的文本也必须加入到语言文件中以支持多语言：

```json
{
  "command.tutorialmod.setlevel.success": "已将您的等级设置为 %s",
  "command.tutorialmod.getlevel.result": "您的当前等级为: %s"
}
```
通过使用 Brigadier 指令框架，您可以为模组量身定做出严密、自动补全、抗注入攻击的控制台指令树，极大地加速了游戏内联机调试的效率。