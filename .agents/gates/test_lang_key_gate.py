import json
import sys
import tempfile
import unittest
from pathlib import Path

# Ensure module import works regardless of current working directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lang_key_gate import load_lang_keys, scan_java_sources, main


class TestLangKeyGate(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        # Create basic directory structure
        self.java_dir = self.root / "src" / "main" / "java" / "com" / "example"
        self.java_dir.mkdir(parents=True, exist_ok=True)

        self.lang_dir = self.root / "src" / "main" / "resources" / "assets" / "example" / "lang"
        self.lang_dir.mkdir(parents=True, exist_ok=True)

        # Write sample lang JSON
        lang_file = self.lang_dir / "en_us.json"
        with open(lang_file, "w", encoding="utf-8") as f:
            json.dump({"example.valid_key": "Valid Key"}, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_lang_keys(self):
        keys = load_lang_keys(self.root)
        self.assertIn("example.valid_key", keys)

    def test_scan_literal_and_dynamic_keys(self):
        sample_java = self.java_dir / "Sample.java"
        sample_java.write_text(
            """
            package com.example;
            import net.minecraft.network.chat.Component;

            public class Sample {
                public void test() {
                    Component c1 = Component.translatable("example.valid_key");
                    Component c2 = Component.translatable("example.missing_key");
                    Component c3 = Component.translatable(getDynamicKey());
                }
                private String getDynamicKey() { return "dyn"; }
            }
            """,
            encoding="utf-8",
        )

        literals, dynamics = scan_java_sources(self.java_dir)
        literal_keys = [k for _, _, k in literals]
        dynamic_exprs = [e for _, _, e in dynamics]

        self.assertIn("example.valid_key", literal_keys)
        self.assertIn("example.missing_key", literal_keys)
        self.assertTrue(len(dynamic_exprs) > 0)

    def test_main_pass_when_all_literals_present(self):
        sample_java = self.java_dir / "ValidSample.java"
        sample_java.write_text(
            """
            package com.example;
            import net.minecraft.network.chat.Component;

            public class ValidSample {
                public void test() {
                    Component c1 = Component.translatable("example.valid_key");
                }
            }
            """,
            encoding="utf-8",
        )

        exit_code = main(["--project-dir", str(self.root)])
        self.assertEqual(exit_code, 0)

    def test_main_fail_when_literal_missing(self):
        sample_java = self.java_dir / "MissingSample.java"
        sample_java.write_text(
            """
            package com.example;
            import net.minecraft.network.chat.Component;

            public class MissingSample {
                public void test() {
                    Component c1 = Component.translatable("example.non_existent_key");
                }
            }
            """,
            encoding="utf-8",
        )

        exit_code = main(["--project-dir", str(self.root)])
        self.assertEqual(exit_code, 1)

    def test_concat_prefix_is_dynamic(self):
        sample_java = self.java_dir / "ConcatSample.java"
        sample_java.write_text(
            """
            package com.example;
            import net.minecraft.network.chat.Component;

            public class ConcatSample {
                public void test(String mode) {
                    Component c1 = Component.translatable("gui.openmodularturrets.mode." + mode);
                }
            }
            """,
            encoding="utf-8",
        )

        literals, dynamics = scan_java_sources(self.java_dir)
        literal_keys = [k for _, _, k in literals]
        dynamic_exprs = [e for _, _, e in dynamics]

        # Must NOT be identified as a complete literal key "gui.openmodularturrets.mode."
        self.assertNotIn("gui.openmodularturrets.mode.", literal_keys)
        self.assertTrue(len(dynamic_exprs) > 0)

        # gate main() must PASS (exit code 0) when only dynamic concat prefix is present
        exit_code = main(["--project-dir", str(self.root)])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
