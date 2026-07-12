# NeoForge 1.21.1 声音系统 (Sounds) 注册与播放指南

> [!WARNING]
> **⚠️ 示例包名禁原样粘贴**：
> 下方所有示例及 references 中的 `com.tutorial.tutorialmod` 均为占位。写入前必须通过读取 `gradle.properties`（获取真实 Group/MOD ID）并执行 `init_workspace.py` 动态重构为当前项目的真实命名空间，严禁硬编码提交。


几乎所有 Minecraft 模组都需要自定义声音效果（例如：武器挥砍、机器运转、生物低吼、UI 点击）。在 NeoForge 1.21.1 中，声音的开发由 **注册类 (SoundEvent)**、**声音配置表 (sounds.json)** 和 **双端播放 API** 组成。

以下是实现自定义声音的完整标准闭环。

---

## 1. 注册 SoundEvent

声音事件需要在模组启动时注册。在代码中，声音事件在本质上代表一个 `ResourceLocation`：

```java
package com.tutorial.tutorialmod.sound;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.sounds.SoundEvent;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

public class ModSounds {
    public static final DeferredRegister<SoundEvent> SOUND_EVENTS =
            DeferredRegister.create(Registries.SOUND_EVENT, TutorialMod.MODID);

    // 注册一个名为 "my_custom_sound" 的声音事件
    public static final DeferredHolder<SoundEvent, SoundEvent> MY_CUSTOM_SOUND =
            SOUND_EVENTS.register("my_custom_sound", () -> 
                    SoundEvent.createVariableRangeEvent(
                            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "my_custom_sound")
                    )
            );
}
```
*切记在主类构造器中调用注册总线：*
`ModSounds.SOUND_EVENTS.register(modEventBus);`

---

## 2. 编写声音配置表 (sounds.json)

仅在 Java 中注册了事件，游戏依然无法播放声音。您必须在模组资源包的根目录下配置 `sounds.json`，将注册的 SoundEvent ID 与实际的 OGG 音频文件进行映射。

*   **文件路径**：`src/main/resources/assets/tutorialmod/sounds.json`
*   **音频路径**：`src/main/resources/assets/tutorialmod/sounds/my_custom_sound_file.ogg` (注意：声音文件必须为 `.ogg` 格式！)

```json
{
  "my_custom_sound": {
    "category": "neutral",
    "subtitle": "subtitles.tutorialmod.my_custom_sound",
    "sounds": [
      {
        "name": "tutorialmod:my_custom_sound_file",
        "stream": false
      }
    ]
  }
}
```

### 参数详解
*   `category`：声音的默认分类（如 `master`, `player`, `block`, `neutral`），玩家可以在游戏内的“声音设置”中按分类独立调整音量。
*   `subtitle`：字幕翻译键名。当玩家开启“显示字幕”选项时，屏幕右下角显示的提示文字。
*   `name`：指向 OGG 文件的 ResourceLocation。`tutorialmod:my_custom_sound_file` 对应 `assets/tutorialmod/sounds/my_custom_sound_file.ogg`。
*   `stream`：如果你的声音是背景音乐（BGM）或长度超过几秒的复杂音乐，必须设为 `true`，以流式方式按需从磁盘读取，防止由于一次性加载大音频文件导致游戏瞬间卡顿或内存溢出。

---

## 3. 播放声音 (Play Sound API)

在 Minecraft 中，播放声音有几种不同的 API，它们的**网络分发和同步逻辑**完全不同：

### 3.1 服务端播放并全服同步 (最常用)

若要在服务端触发某个动作（例如点击方块、受到伤害）并让**世界上的所有人**都听到声音：

```java
// 玩家 null 代表声音会对该区域的所有人播发，包括触发此动作的玩家自己
level.playSound(
        (Player) null,                               // 排除的玩家 (传入 null 播放给所有人)
        pos.getX(), pos.getY(), pos.getZ(),           // 播放坐标
        ModSounds.MY_CUSTOM_SOUND.get(),             // 注册的声音事件
        SoundSource.BLOCKS,                          // 声音分类
        1.0F,                                        // 音量 (1.0F 为标准音量)
        1.0F                                         // 音调/语速 (0.5F ~ 2.0F，1.0F 为标准)
);
```

#### 💡 避坑指南：排除特定玩家 (除触发者外所有人听到)
如果您在**客户端**已经播放了该音效（例如右键物品，客户端先播放了），为了防止该玩家在服务端同步时**听到重叠的二次杂音**，在服务端的 `use` / `interact` 方法中调用 `playSound` 时，第一个参数传入当前的 `ServerPlayer`：
```java
// 第一个参数传入 player，这样游戏会自动跳过给这个玩家发送声音包，而周围其他玩家依然能听到
level.playSound(player, pos, ModSounds.MY_CUSTOM_SOUND.get(), SoundSource.PLAYERS, 1.0F, 1.0F);
```

---

### 3.2 客户端本地播放 (Client Only)

仅在客户端播放（例如玩家点击 UI 按钮的反馈音效，或者某些纯视觉特效的伴随音效），这不需要通过网络同步：

```java
// 仅在本地播放（只有当前客户端玩家能听到，不会通知服务器，不会同步给他人）
level.playLocalSound(
        pos.getX(), pos.getY(), pos.getZ(),
        ModSounds.MY_CUSTOM_SOUND.get(),
        SoundSource.PLAYERS,
        1.0F,
        1.0F,
        false // 是否延迟/等待其它声音
);
```

或者使用 SoundManager（更适合 UI 按钮等非世界实体发出的声音）：
```java
import net.minecraft.client.Minecraft;
import net.minecraft.client.resources.sounds.SimpleSoundInstance;

// 播放一个无空间定位的 UI 按钮音效
Minecraft.getInstance().getSoundManager().play(
        SimpleSoundInstance.forUI(ModSounds.MY_CUSTOM_SOUND.get(), 1.0F)
);
```
通过以上三种播放 API 的合理选型，可为模组构筑起轻量、顺畅且绝无重音或卡顿问题的立体声音效体验。