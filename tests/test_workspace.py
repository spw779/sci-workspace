"""CLI regression tests; all generated projects live in temporary directories."""

import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "workspace.py"
TOP_LEVEL = {"01_reference", "02_manuscript", "03_chapter", "04_data", "05_results"}
SECTIONS = {"Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusions"}
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

    def test_default_scaffold_has_six_chapters_and_no_placeholder_documents(self):
        report = self.init("--project-name", "示例项目")
        self.assertEqual(len(report["created"]), 14)
        self.assertEqual({p.relative_to(self.root).as_posix() for p in self.root.rglob("*")},
                         TOP_LEVEL | DOCUMENTS | {"03_chapter/" + name for name in SECTIONS})
        self.assertTrue(all((self.root / name).is_dir() for name in TOP_LEVEL))
        for name in DOCUMENTS:
            template = SCRIPT.parents[1] / "assets" / (Path(name).stem + ".template.md")
            self.assertEqual((self.root / name).read_text(encoding="utf-8"),
                             template.read_text(encoding="utf-8").replace("{{PROJECT_NAME}}", "示例项目"))

    def test_custom_chapters_extend_defaults_and_material_subdirectories_are_opt_in(self):
        self.init("--sections", "methods", "补充 分析")
        self.assertEqual({p.name for p in (self.root / "03_chapter").iterdir()}, SECTIONS | {"补充 分析"})
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
        draft = self.root / "03_chapter" / "Introduction" / "Introduction_v1.docx"
        draft.write_bytes(b"existing manuscript; do not replace")
        protected = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (guide, original, draft)}
        (self.root / "05_results").rmdir()
        (self.root / "03_chapter" / "Results").rmdir()
        self.assertEqual(self.init()["created"],
                         [str(self.root / "05_results"), str(self.root / "03_chapter" / "Results")])
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
        self.assertEqual(len(report["would_create"]), 20)
        self.assertFalse(target.parent.exists())
        self.assertEqual(snapshot(self.base), before)

    def test_dry_run_leaves_an_existing_workspace_unchanged(self):
        self.init()
        before = snapshot(self.root)
        report = self.init("--sections", "Acknowledgements", "--with-subdirs", "--dry-run")
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
        self.assertEqual({Path(row["path"]).name for row in report["chapters"]}, SECTIONS | {chapter.name})
        self.assertTrue(all(row["state"] == "present" for row in report["chapters"]))
        self.assertEqual(snapshot(self.root), before)
        (self.root / "03_chapter" / "Results").rmdir()
        before = snapshot(self.root)
        report = self.cli("status", "--root", self.root)
        result = next(row for row in report["chapters"] if Path(row["path"]).name == "Results")
        self.assertEqual(result["state"], "missing")
        self.assertFalse(result["optional"])
        self.assertEqual(report["warnings"], ["Required workspace item is missing: " + result["path"]])
        self.assertEqual(snapshot(self.root), before)
        missing = self.base / "absent parent" / "absent root"
        self.assertIn("does not exist", self.cli("status", "--root", missing, success=False)["error"])
        self.assertFalse(missing.parent.exists())

    def test_status_reports_empty_draft_groups_without_selecting_a_current_draft(self):
        self.init()
        report = self.cli("status", "--root", self.root)
        self.assertEqual(report["layout"], "standard")
        self.assertIn("not parsed", report["layout_note"])
        self.assertIn("Draft warnings", report["layout_note"])
        self.assertEqual({group["name"] for group in report["drafts"]["chapters"]}, SECTIONS)
        for group in [report["drafts"]["manuscript"], *report["drafts"]["chapters"]]:
            self.assertEqual(group["state"], "present")
            self.assertEqual(group["versioned_files"], [])
            self.assertIsNone(group["highest_version"])
            self.assertEqual(group["other_files"], [])
            self.assertEqual(group["warnings"], [])
            self.assertNotIn("current", group)

    def test_status_lists_numeric_versions_and_legacy_names_without_opening_or_changing_files(self):
        self.init("--sections", "补充 分析")
        manuscript = self.root / "02_manuscript"
        for name in ("manuscript_v2.docx", "manuscript_v10.docx", "MANUSCRIPT_V1.DOCX",
                     "manuscript.docx", "old draft.doc", "manuscript_v100.doc", "notes.txt",
                     "~$manuscript_v999.docx"):
            (manuscript / name).write_bytes(b"\x00\xffopaque document contents")
        archive = manuscript / "archive"
        archive.mkdir()
        (archive / "manuscript_v999.docx").write_bytes(b"nested draft")
        methods = self.root / "03_chapter" / "Methods" / "Methods_v3.docx"
        methods.write_bytes(b"methods draft")
        extra = self.root / "03_chapter" / "补充 分析" / "补充 分析_v4.docx"
        extra.write_bytes(b"custom chapter draft")
        before = snapshot(self.root)
        module = runpy.run_path(str(SCRIPT))
        with mock.patch.object(Path, "open", side_effect=AssertionError("status must not open files")):
            report = module["status"](SimpleNamespace(root=self.root))
        self.assertEqual(snapshot(self.root), before)
        group = report["drafts"]["manuscript"]
        self.assertEqual([item["version"] for item in group["versioned_files"]], [1, 2, 10])
        self.assertEqual([Path(item["path"]).name for item in group["versioned_files"]],
                         ["MANUSCRIPT_V1.DOCX", "manuscript_v2.docx", "manuscript_v10.docx"])
        self.assertEqual(group["highest_version"], 10)
        self.assertEqual({Path(path).name for path in group["other_files"]},
                         {"manuscript.docx", "old draft.doc", "manuscript_v100.doc"})
        self.assertEqual(group["warnings"], [])
        chapters = {item["name"]: item for item in report["drafts"]["chapters"]}
        self.assertEqual(chapters["Methods"]["versioned_files"], [{"path": str(methods), "version": 3}])
        self.assertEqual(chapters["补充 分析"]["versioned_files"], [{"path": str(extra), "version": 4}])

    def test_status_reports_draft_file_and_directory_conflicts_without_counting_them(self):
        self.init()
        manuscript = self.root / "02_manuscript"
        (manuscript / "manuscript_v2.docx").write_bytes(b"valid draft")
        (manuscript / "manuscript_v50.docx").mkdir()
        (manuscript / "legacy.doc").mkdir()
        methods = self.root / "03_chapter" / "Methods"
        methods.rmdir()
        methods.write_bytes(b"not a chapter directory")
        (self.root / "03_chapter" / "Results").rmdir()
        before = snapshot(self.root)
        report = self.cli("status", "--root", self.root)
        self.assertEqual(snapshot(self.root), before)
        group = report["drafts"]["manuscript"]
        self.assertEqual(group["highest_version"], 2)
        self.assertEqual(len(group["versioned_files"]), 1)
        self.assertEqual(group["other_files"], [])
        self.assertEqual(len(group["warnings"]), 2)
        self.assertTrue(all("Expected a file" in warning for warning in group["warnings"]))
        chapters = {item["name"]: item for item in report["drafts"]["chapters"]}
        self.assertEqual(chapters["Methods"]["state"], "conflict")
        self.assertIn("Expected a directory", chapters["Methods"]["warnings"][0])
        self.assertEqual(chapters["Results"]["state"], "missing")
        for name in ("Methods", "Results"):
            self.assertEqual(chapters[name]["versioned_files"], [])
            self.assertIsNone(chapters[name]["highest_version"])

    def test_status_excludes_external_and_dangling_draft_links(self):
        self.init()
        outside = self.base / "outside"
        outside.mkdir()
        external = outside / "external.docx"
        external.write_bytes(b"external document")
        internal = self.root / "04_data" / "source.docx"
        internal.write_bytes(b"internal document")
        manuscript = self.root / "02_manuscript"
        try:
            (manuscript / "manuscript_v99.docx").symlink_to(external)
            (manuscript / "manuscript_v100.docx").symlink_to(self.root / "absent.docx")
            (manuscript / "manuscript_v3.docx").symlink_to(internal)
            (self.root / "03_chapter" / "External").symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            if os.name == "nt":
                self.skipTest("Windows cannot create this symlink: {}".format(error))
            raise
        before, outside_before = snapshot(self.root), snapshot(outside)
        report = self.cli("status", "--root", self.root)
        self.assertEqual(snapshot(self.root), before)
        self.assertEqual(snapshot(outside), outside_before)
        group = report["drafts"]["manuscript"]
        self.assertEqual(group["highest_version"], 3)
        self.assertEqual(group["versioned_files"],
                         [{"path": str(manuscript / "manuscript_v3.docx"), "version": 3}])
        self.assertEqual(len(group["warnings"]), 2)
        self.assertTrue(any("escapes the project" in warning for warning in group["warnings"]))
        self.assertTrue(any("Dangling" in warning for warning in group["warnings"]))
        external_group = next(item for item in report["drafts"]["chapters"] if item["name"] == "External")
        self.assertEqual(external_group["state"], "conflict")
        self.assertEqual(external_group["versioned_files"], [])
        self.assertIsNone(external_group["highest_version"])
        self.assertIn("escapes the project", external_group["warnings"][0])

    def test_json_success_and_error_output_survive_non_utf8_encoding(self):
        env = {**os.environ, "PYTHONIOENCODING": "ascii"}
        process = subprocess.run([sys.executable, str(SCRIPT), "init", "--root", str(self.root)],
                                 capture_output=True, encoding="ascii", env=env, timeout=15)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertEqual(json.loads(process.stdout)["root"], str(self.root))
        self.assertTrue((self.root / "WORKSPACE_GUIDE.md").is_file())
        missing = self.base / "缺失项目"
        process = subprocess.run([sys.executable, str(SCRIPT), "status", "--root", str(missing)],
                                 capture_output=True, encoding="ascii", env=env, timeout=15)
        self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
        self.assertIn(str(missing), json.loads(process.stderr)["error"])
        self.assertFalse(missing.exists())

    def test_type_conflicts_are_rejected_before_any_initialization_write(self):
        cases = [("03_chapter", False, ()), ("03_chapter/Results", False, ()),
                 ("WORKSPACE_GUIDE.md", True, ()),
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
                rows = (report["directories"] + report["documents"]
                        + report["chapters"] + report["optional_subdirectories"])
                self.assertEqual(next(row["state"] for row in rows if Path(row["path"]) == target), "conflict")

    def test_invalid_sections_are_rejected_without_writes(self):
        before = snapshot(self.base)
        for name in ("../escape", "..\\escape", "CON"):
            with self.subTest(section=name):
                self.assertIn("Invalid section name", self.init("--sections", name, success=False)["error"])
                self.assertEqual(snapshot(self.base), before)
        for names in (("Appendix", "appendix"), ("Methods", "methods")):
            with self.subTest(sections=names):
                self.assertIn("must be unique", self.init("--sections", *names, success=False)["error"])
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
