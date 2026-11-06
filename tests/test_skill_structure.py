from __future__ import annotations

from pathlib import Path
import json
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
OPTIONAL = SKILLS / "task-router/references/optional-workflows.json"
CORE = {"task-router", "development-workflow", "finishing-development", "writing-plans",
        "delivery-handoff"}


def prose(text):
    return re.sub(r"(?ms)^(`{3,}|~{3,}).*?^\1[^\n]*$", "", text)


def local_references(text):
    text = prose(text)
    links = re.findall(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)", text)
    # Explicit relative resources in inline code are dependencies too.
    inline = re.findall(r"`((?:\.\.?/)[^`\s]+\.(?:md|py))`", text)
    return [p for p in links + inline if "://" not in p and "<" not in p]


def dependency_targets(root, source):
    text = source.read_text(encoding="utf-8")
    targets = {(source.parent / target).resolve() for target in local_references(text)}
    names = re.findall(r"relayforge:([a-z0-9-]+)", text)
    names += re.findall(r'Call the Skill tool with "([^" ]+)"', prose(text), re.I)
    targets.update((root / "skills" / name / "SKILL.md").resolve() for name in names)
    return targets


def audit_dependencies(root, optional):
    root = root.resolve()
    declared = {}
    errors = []
    for name, item in optional.items():
        if name in CORE or not (root / "skills" / name / "SKILL.md").is_file():
            errors.append(f"Invalid optional workflow: {name}")
        requirements = item.get("requires", [])
        if not requirements or not item.get("fallback"):
            errors.append(f"Missing optional requirement/fallback: {name}")
        declared[name] = set()
        for value in requirements:
            target = (root / value).resolve()
            if not target.is_relative_to(root) or not value.startswith("skills/"):
                errors.append(f"Unsafe optional requirement: {value}")
            else:
                declared[name].add(target)
    referenced = {name: set() for name in optional}
    for source in (root / "skills").rglob("*.md"):
        name = source.relative_to(root / "skills").parts[0]
        if name == "vercel-react-best-practices":
            continue  # vendor rule catalog, not a workflow dependency graph
        targets = dependency_targets(root, source)
        if name in referenced:
            referenced[name].update(targets)
        for target in targets:
            if not target.exists() and target not in declared.get(name, set()):
                errors.append(f"Undeclared missing dependency: {source.relative_to(root)} -> {target}")
    statuses = {}
    for name, requirements in declared.items():
        stale = requirements - referenced[name]
        if stale:
            errors.append(f"Optional declarations no longer referenced by {name}: {sorted(map(str, stale))}")
        missing = sorted(path.relative_to(root).as_posix() for path in requirements if not path.exists())
        statuses[name] = {"available": not missing, "missing": missing}
    return errors, statuses


class SkillStructureTests(unittest.TestCase):
    def test_frontmatter_identifies_each_skill(self):
        for path in SKILLS.glob("*/SKILL.md"):
            text = path.read_text(encoding="utf-8")
            match = re.match(r"---\n(.*?)\n---\n", text, re.S)
            self.assertIsNotNone(match, path)
            metadata = match[1]
            self.assertRegex(metadata, rf"(?m)^name: {re.escape(path.parent.name)}$")
            self.assertRegex(metadata, r"(?m)^description: \S.*")

    def test_packaged_dependencies_resolve(self):
        metadata = json.loads(OPTIONAL.read_text(encoding="utf-8"))
        self.assertEqual(metadata["schema_version"], 1)
        errors, statuses = audit_dependencies(ROOT, metadata["optional_workflows"])
        self.assertEqual(errors, [])
        for name, status in statuses.items():
            # Missing optional workflows are explicitly unavailable, never silently ready.
            self.assertEqual(status["available"], not status["missing"], name)

    def test_availability_tracks_actual_resources_and_rejects_unknown_gaps(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skills/optional"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("Read [reviewer](../review/reviewer.md).", encoding="utf-8")
            declaration = {"optional": {"requires": ["skills/review/reviewer.md"], "fallback": "core"}}
            errors, states = audit_dependencies(root, declaration)
            self.assertEqual(errors, [])
            self.assertEqual(states["optional"], {"available": False, "missing": ["skills/review/reviewer.md"]})
            review = root / "skills/review/reviewer.md"
            review.parent.mkdir()
            review.write_text("Reviewer", encoding="utf-8")
            self.assertEqual(audit_dependencies(root, declaration)[1]["optional"], {"available": True, "missing": []})
            (skill / "SKILL.md").write_text("Read [reviewer](../review/reviewer.md) and [other](missing.md).", encoding="utf-8")
            self.assertTrue(audit_dependencies(root, declaration)[0])
            (skill / "SKILL.md").write_text("No dependencies.", encoding="utf-8")
            self.assertTrue(audit_dependencies(root, declaration)[0])

    def test_optional_declaration_cannot_hide_a_core_missing_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skills/task-router"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("Read [required](missing.md).", encoding="utf-8")
            declared = {"task-router": {"requires": ["skills/task-router/missing.md"], "fallback": "skip"}}
            self.assertTrue(audit_dependencies(root, declared)[0])

    def test_dependency_parser_includes_inline_paths_but_not_example_commands(self):
        sample = "Read `../review/reviewer.md` and [protocol](refs/protocol.md).\n```text\n[example](missing.md)\n```"
        self.assertEqual(local_references(sample), ["refs/protocol.md", "../review/reviewer.md"])


if __name__ == "__main__":
    unittest.main()
