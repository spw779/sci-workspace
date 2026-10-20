"""CLI regression tests; all generated projects live in temporary directories."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workspace.py"
TOP_LEVEL = {"01_reference", "02_manuscript", "03_chapter", "04_data", "05_results"}
DOCUMENTS = {"AGENTS.md", "WORKSPACE_GUIDE.md"}
SUBDIRS = {"04_data/raw", "04_data/processed", "04_data/metadata",
           "05_results/statistics", "05_results/tables", "05_results/figures"}


def snapshot(root):
    result = {}
    for path in [root, *root.rglob("*")]:
        if path.is_symlink():
            content = ("symlink", str(path.readlink()))
        elif path.is_dir():
            content = ("directory",)
        else:
            content = ("file", path.read_bytes())
        result[str(path.relative_to(root))] = (*content, path.lstat().st_mtime_ns)
    return result


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="sci-workspace-test-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / "科研 project"

    def cli(self, *args, success=True):
        process = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)], capture_output=True,
            encoding="utf-8", timeout=15,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertNotIn("Traceback", process.stderr)
        self.assertEqual(process.returncode == 0, success, process.stdout + process.stderr)
        return json.loads(process.stdout if success else process.stderr)

    def init(self, *args, root=None, success=True):
        return self.cli("init", "--root", root or self.root, *args, success=success)

    def test_default_scaffold_has_no_chapters_or_placeholder_documents(self):
        report = self.init("--project-name", "示例项目")
        self.assertEqual(len(report["created"]), 8)
        self.assertEqual({p.relative_to(self.root).as_posix() for p in self.root.rglob("*")},
                         TOP_LEVEL | DOCUMENTS)
        self.assertTrue(all((self.root / name).is_dir() for name in TOP_LEVEL))
        for name in DOCUMENTS:
            template = SCRIPT.parents[1] / "assets" / (Path(name).stem + ".template.md")
            self.assertEqual((self.root / name).read_text(encoding="utf-8"),
                             template.read_text(encoding="utf-8").replace("{{PROJECT_NAME}}", "示例项目"))

    def test_chapters_and_six_subdirectories_are_opt_in(self):
        self.init("--sections", "Methods", "补充 分析")
        self.assertEqual({p.name for p in (self.root / "03_chapter").iterdir()}, {"Methods", "补充 分析"})
        self.assertEqual(list((self.root / "04_data").iterdir()), [])
        self.assertEqual(list((self.root / "05_results").iterdir()), [])
        report = self.init("--with-subdirs")
        self.assertEqual({Path(p).relative_to(self.root).as_posix() for p in report["created"]}, SUBDIRS)
        self.assertTrue(all((self.root / name).is_dir() for name in SUBDIRS))

    def test_repeat_fills_missing_items_and_preserves_existing_content(self):
        self.init()
        guide = self.root / "WORKSPACE_GUIDE.md"
        guide.write_text("人工维护的 Guide\n保留此内容。\n", encoding="utf-8")
        original = self.root / "04_data" / "original.bin"
        original.write_bytes(b"\x00\xfforiginal data")
        protected = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (guide, original)}
        (self.root / "05_results").rmdir()
        self.assertEqual(self.init()["created"], [str(self.root / "05_results")])
        self.assertEqual({p: (p.read_bytes(), p.stat().st_mtime_ns) for p in protected}, protected)
        before = snapshot(self.root)
        self.assertEqual(self.init()["created"], [])
        self.assertEqual(snapshot(self.root), before)

    def test_dry_run_does_not_create_a_new_root_or_parent(self):
        target = self.base / "missing parent" / "missing root"
        before = snapshot(self.base)
        report = self.init("--sections", "Results", "--with-subdirs", "--dry-run", root=target)
        self.assertTrue(report["dry_run"])
        self.assertEqual(report["created"], [])
        self.assertEqual(len(report["would_create"]), 15)
        self.assertFalse(target.parent.exists())
        self.assertEqual(snapshot(self.base), before)

    def test_dry_run_leaves_an_existing_workspace_unchanged(self):
        self.init()
        before = snapshot(self.root)
        report = self.init("--sections", "Conclusions", "--with-subdirs", "--dry-run")
        self.assertEqual(report["created"], [])
        self.assertEqual(len(report["would_create"]), 7)
        self.assertEqual(snapshot(self.root), before)

    def test_status_is_read_only_and_absent_optional_directories_are_normal(self):
        self.init()
        chapter = self.root / "03_chapter" / "Legacy Notes (custom)"
        chapter.mkdir()
        (chapter / "ignored_v999.docx").write_bytes(b"opaque content; do not inspect")
        before = snapshot(self.root)
        report = self.cli("status", "--root", self.root)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(len(report["directories"]), 5)
        self.assertEqual(len(report["documents"]), 2)
        self.assertTrue(all(row["state"] == "present" for row in report["directories"] + report["documents"]))
        self.assertEqual({row["state"] for row in report["optional_subdirectories"]}, {"not_created"})
        self.assertEqual([Path(row["path"]).name for row in report["chapters"]], [chapter.name])
        self.assertEqual(snapshot(self.root), before)
        missing = self.base / "absent parent" / "absent root"
        self.assertIn("does not exist", self.cli("status", "--root", missing, success=False)["error"])
        self.assertFalse(missing.parent.exists())

    def test_type_conflicts_are_rejected_before_any_initialization_write(self):
        cases = [("03_chapter", False, ()), ("WORKSPACE_GUIDE.md", True, ()),
                 ("04_data/raw", False, ("--with-subdirs",))]
        for index, (relative, directory, options) in enumerate(cases):
            with self.subTest(path=relative):
                root = self.base / ("conflict-" + str(index))
                target = root / relative
                target.parent.mkdir(parents=True)
                if directory:
                    target.mkdir()
                else:
                    target.write_bytes(b"existing file")
                before = snapshot(root)
                self.assertIn("Expected a", self.init(*options, root=root, success=False)["error"])
                self.assertEqual(snapshot(root), before)
                report = self.cli("status", "--root", root)
                rows = report["directories"] + report["documents"] + report["optional_subdirectories"]
                self.assertEqual(next(row["state"] for row in rows if Path(row["path"]) == target), "conflict")

    def test_invalid_sections_are_rejected_without_writes(self):
        before = snapshot(self.base)
        for name in ("../escape", "..\\escape", "CON"):
            with self.subTest(section=name):
                self.assertIn("Invalid section name", self.init("--sections", name, success=False)["error"])
                self.assertEqual(snapshot(self.base), before)

    def test_external_directory_and_document_symlinks_are_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        document = outside / "guide.md"
        document.write_bytes(b"outside content")
        for directory in (True, False):
            with self.subTest(directory_link=directory):
                root = self.base / ("link-dir" if directory else "link-file")
                root.mkdir()
                link = root / ("01_reference" if directory else "WORKSPACE_GUIDE.md")
                try:
                    link.symlink_to(outside if directory else document, target_is_directory=directory)
                except (OSError, NotImplementedError) as error:
                    if os.name == "nt":
                        self.skipTest("Windows cannot create this symlink: {}".format(error))
                    raise
                before, outside_before = snapshot(root), snapshot(outside)
                self.assertIn("escapes the project", self.init(root=root, success=False)["error"])
                self.assertEqual(snapshot(root), before)
                self.assertEqual(snapshot(outside), outside_before)


if __name__ == "__main__":
    unittest.main()
