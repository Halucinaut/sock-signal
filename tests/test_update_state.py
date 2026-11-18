import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/update_state.py"


class StateTest(unittest.TestCase):
    def test_projects_are_independent_and_corrupt_state_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            projects = [root / "one", root / "two"]
            for project in projects:
                (project / "scripts").mkdir(parents=True)
                shutil.copy2(SCRIPT, project / "scripts/update_state.py")

            def run(project):
                return subprocess.run(
                    ["python3", str(project / "scripts/update_state.py"), "Codex"],
                    capture_output=True, text=True,
                )

            self.assertEqual(run(projects[0]).returncode, 0)
            self.assertEqual(run(projects[0]).returncode, 0)
            self.assertEqual(run(projects[1]).returncode, 0)
            states = [json.loads((project / "state.json").read_text()) for project in projects]
            self.assertEqual([state["agents"]["Codex"]["sessions"] for state in states], [2, 1])
            corrupt = projects[0] / "state.json"
            corrupt.write_text("broken")
            self.assertNotEqual(run(projects[0]).returncode, 0)
            self.assertEqual(corrupt.read_text(), "broken")


if __name__ == "__main__":
    unittest.main()
