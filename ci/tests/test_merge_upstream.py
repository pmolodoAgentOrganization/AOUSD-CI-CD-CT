"""Exercise source removal and concurrent CI development with real Git merges."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "merge_upstream.py"


class MergeUpstreamTest(unittest.TestCase):
    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args], cwd=cwd or self.root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        ).stdout.strip()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-b", "upstream")
        self.git("config", "user.name", "CI test")
        self.git("config", "user.email", "ci@example.invalid")
        self.write("CMakeLists.txt", "project(OpenUSD)\n")
        self.write("pxr/source.cpp", "base source\n")
        self.write("build_scripts/driver.py", "base CI\n")
        self.base = self.commit("Upstream base")
        self.git("switch", "-c", "ci")
        self.git("-c", "protocol.file.allow=always", "submodule", "add",
                 str(self.root), "OpenUSD")
        self.git("rm", "-r", "pxr", "CMakeLists.txt")
        self.write("ci/local.txt", "AOUSD CI development\n")
        self.split = self.commit("Separate CI and source")
        self.git("switch", "upstream")
        self.write("pxr/source.cpp", "updated source\n")
        self.write("pxr/added.cpp", "added source\n")
        self.write("docs/added.md", "product docs\n")
        self.write("build_scripts/driver.py", "upstream CI\n")
        self.upstream = self.commit("Update source and CI")
        self.git("switch", "ci")

    def merge(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "upstream"], cwd=self.root,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def test_merge_preserves_ci_and_pins_source(self):
        result = self.merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root / "pxr").exists())
        self.assertFalse((self.root / "docs").exists())
        self.assertEqual((self.root / "build_scripts/driver.py").read_text(), "upstream CI\n")
        self.assertTrue((self.root / "ci/local.txt").is_file())
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.root / "OpenUSD"), self.upstream)
        self.assertEqual((self.root / "OpenUSD/pxr/added.cpp").read_text(), "added source\n")
        self.assertEqual(self.git("rev-parse", "HEAD"), self.split)
        self.assertEqual(self.git("rev-parse", "MERGE_HEAD"), self.upstream)
        self.git("commit", "-m", "Merge upstream")
        self.assertEqual(self.git("rev-parse", "HEAD^2"), self.upstream)
        self.assertEqual(self.merge().returncode, 0)

    def test_ci_conflict_is_not_overwritten(self):
        self.write("build_scripts/driver.py", "AOUSD CI\n")
        self.commit("Develop CI locally")
        result = self.merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("retained CI conflicts", result.stderr)
        self.assertEqual(self.git("diff", "--name-only", "--diff-filter=U"), "build_scripts/driver.py")
        self.assertFalse((self.root / "pxr").exists())

    def test_dirty_checkout_is_rejected(self):
        self.write("ci/local.txt", "uncommitted work\n")
        result = self.merge()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Commit or stash", result.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD"), self.split)

    def test_source_only_updates_merge_repeatedly(self):
        self.git("switch", "upstream")
        self.git("restore", "--source", self.base, "--", "build_scripts/driver.py")
        self.commit("Keep CI unchanged")
        self.git("switch", "ci")
        for index in range(2):
            self.git("switch", "upstream")
            self.write("pxr/source.cpp", f"source revision {index}\n")
            self.write(f"extras/new{index}.cpp", "new product file\n")
            revision = self.commit("Source-only development")
            self.git("switch", "ci")
            result = self.merge()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.git("diff", "--name-only", "--diff-filter=U"), "")
            self.assertFalse((self.root / "pxr").exists())
            self.assertFalse((self.root / "extras").exists())
            self.assertEqual((self.root / "build_scripts/driver.py").read_text(), "base CI\n")
            self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.root / "OpenUSD"), revision)
            self.git("commit", "-m", "Merge source update")

    def test_abort_restores_submodule_pin(self):
        result = self.merge()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.git("merge", "--abort")
        self.git("submodule", "update", "--init", "--recursive")
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.root / "OpenUSD"), self.base)
        self.assertEqual(self.git("status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
