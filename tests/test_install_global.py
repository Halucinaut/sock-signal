import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_global", SOURCE / "scripts/install_global.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTest(unittest.TestCase):
    def test_migration_repeat_and_uninstall(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            old = project / ".agents/skills/sock-signal"
            old.mkdir(parents=True)
            state = '{"version":1,"agents":{"Codex":{"sessions":2}}}'
            (old / "state.json").write_text(state)
            original_cwd = Path.cwd()
            try:
                os.chdir(project)
                with patch.object(installer, "HOME", root / "user"), patch.dict(os.environ, {"CODEX_HOME": str(root / "user/codex")}):
                    def run(*args):
                        with patch.object(sys, "argv", ["install_global.py", "--agents", "codex", *args]):
                            installer.main()

                    run()
                    target = root / "user/.agents/skills/sock-signal"
                    self.assertEqual((target / "state.json").read_text(), state)
                    run()
                    self.assertEqual((target / "state.json").read_text(), state)
                    self.assertFalse((target / ".agents").exists())
                    self.assertEqual((project / "AGENTS.md").read_text().count(installer.PROJECT_START), 1)
                    run("--uninstall")
                    self.assertNotIn(installer.PROJECT_START, (project / "AGENTS.md").read_text())
                    self.assertTrue((target / "state.json").exists())
                    self.assertTrue((old / "state.json").exists())
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
