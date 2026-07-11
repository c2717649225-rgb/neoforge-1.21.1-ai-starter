# NeoForge 1.21.1 自定义生物模型 (EntityModels) 注册与渲染指南

在 Minecraft 中，除了使用原版现成的渲染器（如恶魂或僵尸渲染器），模组通常需要为自定义生物（如新宠物、新怪物）设计独特的 3D 几何模型。

从 Minecraft 1.17+ 到 1.21.1，官方采用了 **`HierarchicalModel`** 骨架分级模型体系，取代了传统的 `EntityModel` 直排骨骼。同时，必须在物理客户端使用事件进行骨骼图层定义与绑定注册。

---

## 1. 编写自定义模型类 (HierarchicalModel)

生物模型包含若干 `ModelPart`（骨骼部分，如头部、身体、四肢），并在 `setupAnim` 中动态计算关节摆动形成行走、攻击动画：

```java
package com.tutorial.tutorialmod.client.model;

import com.tutorial.tutorialmod.entity.RubyGhostEntity;
import net.minecraft.client.model.HierarchicalModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartDefinition;
import net.minecraft.client.model.geom.builders.*;
import net.minecraft.util.Mth;

public class RubyGhostModel<T extends RubyGhostEntity> extends HierarchicalModel<T> {

    // 1. 根骨骼部件，必须包含所有子部件的索引
    private final ModelPart root;
    private final ModelPart head;
    private final ModelPart body;

    public RubyGhostModel(ModelPart root) {
        this.root = root;
        // 使用 getChild 解析子骨骼节点
        this.head = root.getChild("head");
        this.body = root.getChild("body");
    }

    // 2. 核心骨骼网格定义 (通常由 Blockbench 软件导出)
    public static LayerDefinition createBodyLayer() {
        MeshDefinition meshdefinition = new MeshDefinition();
        PartDefinition partdefinition = meshdefinition.getRoot();

        // 声明 "head" 骨骼：立方体盒原点、UV映射、大小等
        partdefinition.addOrReplaceChild("head", 
                CubeListBuilder.create().texOffs(0, 0)
                        .addBox(-4.0F, -8.0F, -4.0F, 8.0F, 8.0F, 8.0F, new CubeDeformation(0.0F)), 
                PartPose.offset(0.0F, 0.0F, 0.0F));

        // 声明 "body" 骨骼
        partdefinition.addOrReplaceChild("body", 
                CubeListBuilder.create().texOffs(16, 16)
                        .addBox(-4.0F, 0.0F, -2.0F, 8.0F, 12.0F, 4.0F, new CubeDeformation(0.0F)), 
                PartPose.offset(0.0F, 0.0F, 0.0F));

        // 纹理的分辨率 (X, Y)。例如 64x32 或 64x64
        return LayerDefinition.create(meshdefinition, 64, 64);
    }

    // 3. 必须重写：返回根骨骼，以便引擎渲染基准点
    @Override
    public ModelPart root() {
        return this.root;
    }

    // 4. 关键动作逻辑：每帧都会被调用以渲染骨骼动画（如摆动头部、摆动四肢）
    @Override
    public void setupAnim(T entity, float limbSwing, float limbSwingAmount, 
                          float ageInTicks, float netHeadYaw, float headPitch) {
        // 让头部根据玩家视线转动
        this.head.yRot = netHeadYaw * ((float)Math.PI / 180F);
        this.head.xRot = headPitch * ((float)Math.PI / 180F);

        // 让身体随着行走步伐进行微弱的正弦自转摆动
        this.body.yRot = Mth.cos(limbSwing * 0.6662F) * 0.25F * limbSwingAmount;
    }
}
```

---

## 2. 编写实体渲染器类 (EntityRenderer)

渲染器负责将模型、贴图纹理、以及阴影尺寸与具体的生物实体类进行绑定：

```java
package com.tutorial.tutorialmod.client.renderer;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.client.model.RubyGhostModel;
import com.tutorial.tutorialmod.client.renderer.layers.ModModelLayers;
import com.tutorial.tutorialmod.entity.RubyGhostEntity;
import net.minecraft.client.renderer.entity.EntityRendererProvider;
import net.minecraft.client.renderer.entity.MobRenderer;
import net.minecraft.resources.ResourceLocation;

public class RubyGhostRenderer extends MobRenderer<RubyGhostEntity, RubyGhostModel<RubyGhostEntity>> {

    // 贴图文件的具体路径位置 (assets/tutorialmod/textures/entity/ruby_ghost.png)
    private static final ResourceLocation TEXTURE = 
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "textures/entity/ruby_ghost.png");

    public RubyGhostRenderer(EntityRendererProvider.Context context) {
        // 调用父构造器：绑定 context、我们的自定义模型、以及实体的地面阴影半径大小（0.5F 表示半格大）
        super(context, new RubyGhostModel<>(context.bakeLayer(ModModelLayers.RUBY_GHOST)), 0.5F);
    }

    // 重写获取贴图 ResourceLocation
    @Override
    public ResourceLocation getTextureLocation(RubyGhostEntity entity) {
        return TEXTURE;
    }
}
```

---

## 3. 定义与注册模型图层 (ModelLayers)

### 3.1 声明 ModelLayerLocation (常量声明)
```java
package com.tutorial.tutorialmod.client.renderer.layers;

import com.tutorial.tutorialmod.TutorialMod;
import net.minecraft.client.model.geom.ModelLayerLocation;
import net.minecraft.resources.ResourceLocation;

public class ModModelLayers {
    // 声明模型图层的唯一辨识键 (包含实体ID和图层名字)
    public static final ModelLayerLocation RUBY_GHOST = new ModelLayerLocation(
            ResourceLocation.fromNamespaceAndPath(TutorialMod.MODID, "ruby_ghost"),
            "main" // 默认主图层
    );
}
```

### 3.2 绑定骨骼与渲染器注册 (RegisterLayerDefinitions & RegisterRenderers)
这两个事件必须订阅在客户端 Mod 事件总线上，并且使用物理安全隔离：

```java
package com.tutorial.tutorialmod.client;

import com.tutorial.tutorialmod.TutorialMod;
import com.tutorial.tutorialmod.client.model.RubyGhostModel;
import com.tutorial.tutorialmod.client.renderer.RubyGhostRenderer;
import com.tutorial.tutorialmod.client.renderer.layers.ModModelLayers;
import com.tutorial.tutorialmod.entity.ModEntities;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;

@EventBusSubscriber(modid = TutorialMod.MODID, value = Dist.CLIENT) // 1.21.1+ 已废弃 bus 参数，系统会自动通过 IModBusEvent 路由
public class ClientEntityModelRegistrar {

    // 1. 注册模型骨骼骨架布局
    @SubscribeEvent
    public static void registerLayerDefinitions(EntityRenderersEvent.RegisterLayerDefinitions event) {
        event.registerLayerDefinition(
                ModModelLayers.RUBY_GHOST,
                RubyGhostModel::createBodyLayer // 绑定 createBodyLayer 静态方法
        );
    }

    // 2. 注册实体对应的具体渲染器
    @SubscribeEvent
    public static void registerRenderers(EntityRenderersEvent.RegisterRenderers event) {
        event.registerEntityRenderer(
                ModEntities.RUBY_GHOST.get(),
                RubyGhostRenderer::new
        );
    }
}
```

---

## 4. 物理隔离与防崩警告

*   **物理隔离红线**：`HierarchicalModel`、`ModelPart`、`MobRenderer`、`ModelLayerLocation` 包含大量的 OpenGL 与物理显卡交互逻辑，**在专用服务端 Jar 包中完全缺失**。
*   必须使用 `@EventBusSubscriber(value = Dist.CLIENT)` 进行彻底隔离。绝对禁止在服务端的 AI、数据包、或者公共方块/实体类中直接加载或引用 `RubyGhostRenderer` 或 `RubyGhostModel`。
