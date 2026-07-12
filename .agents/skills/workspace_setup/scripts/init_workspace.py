import os
import re
import json
import shutil

def main():
    print("==================================================")
    print("Starting Mod Workspace Auto-Refactoring Engine...")
    print("==================================================")

    # 1. 获取路径 (自适应深度：.agents/skills/workspace_setup/scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__)) # scripts/
    workspace_setup_dir = os.path.dirname(script_dir)       # workspace_setup/
    skills_dir = os.path.dirname(workspace_setup_dir)       # skills/
    agents_dir = os.path.dirname(skills_dir)               # .agents/
    project_dir = os.path.dirname(agents_dir)             # 项目根目录

    gradle_properties_path = os.path.join(project_dir, "gradle.properties")
    agents_md_path = os.path.join(agents_dir, "AGENTS.md")

    if not os.path.exists(gradle_properties_path):
        print(f"Error: gradle.properties not found at {gradle_properties_path}")
        return

    # 2. 解析 gradle.properties
    props = {}
    with open(gradle_properties_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()

    mod_id = props.get("mod_id", "tutorialmod")
    mod_name = props.get("mod_name", "Tutorial Mod")
    mod_group_id = props.get("mod_group_id", "com.tutorial.tutorialmod")

    print(f"[Properties] Mod ID: {mod_id}")
    print(f"[Properties] Mod Name: {mod_name}")
    print(f"[Properties] Mod Package: {mod_group_id}")

    # 3. 扫描主包目录定位被 @Mod 修饰的入口类
    base_package_path = os.path.join(project_dir, "src", "main", "java", *mod_group_id.split("."))
    main_class_file = None
    main_class_full_path = None
    main_class_rel_path = f"./src/main/java/{mod_group_id.replace('.', '/')}/TutorialMod.java" # 默认回退相对路径

    if os.path.exists(base_package_path):
        for root, _, files in os.walk(base_package_path):
            for file in files:
                if file.endswith(".java"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8", errors="replace") as jf:
                        content = jf.read()
                        if "@Mod(" in content:
                            main_class_file = file
                            main_class_full_path = full_path
                            main_class_rel_path = "./" + os.path.relpath(full_path, project_dir).replace("\\", "/")
                            break
            if main_class_file:
                break

    print(f"[Java Main Class] Located: {main_class_rel_path}")

    # 4. 【重命名】资源包物理目录并更新本地化 JSON
    resources_dir = os.path.join(project_dir, "src", "main", "resources")
    assets_dir = os.path.join(resources_dir, "assets")
    
    # 查找 assets/ 下的非法或过期目录名（不等于当前 mod_id 的那个）
    if os.path.exists(assets_dir):
        subdirs = [d for d in os.listdir(assets_dir) if os.path.isdir(os.path.join(assets_dir, d))]
        for sub in subdirs:
            if sub != mod_id:
                old_path = os.path.join(assets_dir, sub)
                new_path = os.path.join(assets_dir, mod_id)
                if os.path.exists(new_path):
                    # 如果新文件夹已存在，合并他们或删除旧的
                    print(f"[Assets] Merging folder {sub} into {mod_id}...")
                    for root, dirs, files in os.walk(old_path):
                        for f in files:
                            src_file = os.path.join(root, f)
                            rel_to_old = os.path.relpath(src_file, old_path)
                            dest_file = os.path.join(new_path, rel_to_old)
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                            shutil.copy2(src_file, dest_file)
                    shutil.rmtree(old_path)
                else:
                    print(f"[Assets] Renaming folder {sub} -> {mod_id}")
                    shutil.move(old_path, new_path)

    # 自动替换语言 JSON 内部的 namespace 前缀键值
    lang_dir = os.path.join(assets_dir, mod_id, "lang")
    if os.path.exists(lang_dir):
        for file in os.listdir(lang_dir):
            if file.endswith(".json"):
                json_path = os.path.join(lang_dir, file)
                try:
                    with open(json_path, "r", encoding="utf-8") as jf:
                        lang_data = json.load(jf)
                    
                    new_lang_data = {}
                    for k, v in lang_data.items():
                        new_k = re.sub(r'\bexamplemod\b', mod_id, k)
                        new_lang_data[new_k] = v
                    
                    with open(json_path, "w", encoding="utf-8") as jf:
                        json.dump(new_lang_data, jf, indent=2, ensure_ascii=False)
                    print(f"[Language JSON] Aligned namespaces in {file}")
                except Exception as e:
                    print(f"Error processing language json {file}: {e}")

    # 4b. 【数据命名空间重命名与单数规范修正】
    data_dir = os.path.join(resources_dir, "data")
    if os.path.exists(data_dir):
        # 查找 data/ 下的非法或过期目录名（不等于当前 mod_id 的那个，如 examplemod）
        subdirs = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
        for sub in subdirs:
            if sub != mod_id and sub not in ("minecraft", "c"):
                old_path = os.path.join(data_dir, sub)
                new_path = os.path.join(data_dir, mod_id)
                if os.path.exists(new_path):
                    print(f"[Data] Merging data folder {sub} into {mod_id}...")
                    for root, _, files in os.walk(old_path):
                        for f in files:
                            src_file = os.path.join(root, f)
                            rel_to_old = os.path.relpath(src_file, old_path)
                            dest_file = os.path.join(new_path, rel_to_old)
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                            shutil.copy2(src_file, dest_file)
                    shutil.rmtree(old_path)
                else:
                    print(f"[Data] Renaming data folder {sub} -> {mod_id}")
                    shutil.move(old_path, new_path)

        # 自动修正 1.21.1 命名单数规约 (recipes -> recipe, loot_tables -> loot_table, advancements -> advancement)
        target_data_ns = os.path.join(data_dir, mod_id)
        if os.path.exists(target_data_ns):
            plural_to_singular = {
                "recipes": "recipe",
                "loot_tables": "loot_table",
                "advancements": "advancement"
            }
            for plural, singular in plural_to_singular.items():
                plural_path = os.path.join(target_data_ns, plural)
                if os.path.exists(plural_path):
                    singular_path = os.path.join(target_data_ns, singular)
                    if os.path.exists(singular_path):
                        for root, _, files in os.walk(plural_path):
                            for f in files:
                                src_file = os.path.join(root, f)
                                dest_file = os.path.join(singular_path, os.path.relpath(src_file, plural_path))
                                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                                shutil.copy2(src_file, dest_file)
                        shutil.rmtree(plural_path)
                        print(f"[Singular Rule] Merged and singularized {plural} -> {singular}")
                    else:
                        os.rename(plural_path, singular_path)
                        print(f"[Singular Rule] Renamed {plural} -> {singular}")

    # 4c. 【元数据残留清理】
    pack_mcmeta_path = os.path.join(resources_dir, "pack.mcmeta")
    if os.path.exists(pack_mcmeta_path):
        try:
            with open(pack_mcmeta_path, "r", encoding="utf-8") as f:
                mcmeta_content = f.read()
            new_mcmeta = re.sub(r'\bexamplemod\b', mod_id, mcmeta_content)
            if new_mcmeta != mcmeta_content:
                with open(pack_mcmeta_path, "w", encoding="utf-8") as f:
                    f.write(new_mcmeta)
                print("[META-INF] Aligned namespaces in pack.mcmeta")
        except Exception as e:
            print(f"Error alignment in pack.mcmeta: {e}")

    # 5. 【解密模板】Uncomment neoforge.mods.toml 的 mixins 占位符
    mods_toml_template = os.path.join(project_dir, "src", "main", "templates", "META-INF", "neoforge.mods.toml")
    if os.path.exists(mods_toml_template):
        with open(mods_toml_template, "r", encoding="utf-8") as tf:
            toml_content = tf.read()
        
        if "#[[mixins]]" in toml_content:
            toml_content = toml_content.replace("#[[mixins]]", "[[mixins]]")
            toml_content = toml_content.replace('#config="${mod_id}.mixins.json"', 'config="${mod_id}.mixins.json"')
            with open(mods_toml_template, "w", encoding="utf-8") as tf:
                tf.write(toml_content)
            print("[META-INF Template] Activated Mixin blocks in neoforge.mods.toml")

    # 6. 【自动生成】创建对应的 {mod_id}.mixins.json 配置文件
    mixin_config_path = os.path.join(resources_dir, f"{mod_id}.mixins.json")
    if not os.path.exists(mixin_config_path):
        mixin_data = {
            "required": True,
            "minVersion": "0.8",
            "package": f"{mod_group_id}.mixin",
            "compatibilityLevel": "JAVA_21",
            "refmap": f"{mod_id}.refmap.json",
            "mixins": [],
            "client": [],
            "injectors": {
                "defaultRequire": 1
            }
        }
        with open(mixin_config_path, "w", encoding="utf-8") as mf:
            json.dump(mixin_data, mf, indent=2, ensure_ascii=False)
        print(f"[Mixin Config] Created {mod_id}.mixins.json")

    # 7. 【重写代码】更新入口 Java 主类中的 MODID 常量及旧注释
    if main_class_full_path and os.path.exists(main_class_full_path):
        with open(main_class_full_path, "r", encoding="utf-8") as jf:
            java_content = jf.read()
        
        new_java_content = re.sub(
            r'public static final String MODID = "[^"]*";',
            f'public static final String MODID = "{mod_id}";',
            java_content
        )
        new_java_content = re.sub(r'\bexamplemod\b', mod_id, new_java_content)
        
        if new_java_content != java_content:
            with open(main_class_full_path, "w", encoding="utf-8") as jf:
                jf.write(new_java_content)
            print(f"[Java Code] Updated MODID constant & comments in {main_class_file}")

    # 8. 【对齐规约】更新 AGENTS.md 顶部的动态元数据
    if os.path.exists(agents_md_path):
        with open(agents_md_path, "r", encoding="utf-8") as f:
            agents_content = f.read()

        updated_content = re.sub(
            r'- \*\*参考 Mod ID\*\*: .*',
            f'- **参考 Mod ID**: {mod_id} (已由初始化引擎自动对齐)',
            agents_content
        )
        updated_content = re.sub(
            r'- \*\*参考 Mod Name\*\*: .*',
            f'- **参考 Mod Name**: {mod_name} (已由初始化引擎自动对齐)',
            updated_content
        )
        
        main_class_name = os.path.basename(main_class_rel_path) if main_class_file else "TutorialMod.java"
        updated_content = re.sub(
            r'- \*\*参考基类路径\*\*: .*',
            f'- **参考基类路径**: [{main_class_name}]({main_class_rel_path})',
            updated_content
        )

        with open(agents_md_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        print("[AGENTS.md] Rules specification metadata aligned.")

    print("==================================================")
    print("Refactoring Complete! Mod Workspace is ready.")
    print("==================================================")

if __name__ == "__main__":
    main()
