from __future__ import annotations

import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def skill_files():
    return sorted(SKILLS.glob("*/SKILL.md"))


def frontmatter(text: str) -> str:
    assert text.startswith("---\n")
    end = text.find("\n---\n", 4)
    assert end >= 0
    return text[4:end]


class SkillStructureTests(unittest.TestCase):
    def test_skill_names_match_directories_and_descriptions_exist(self):
        for path in skill_files():
            metadata = frontmatter(path.read_text(encoding="utf-8"))
            name = re.search(r"^name:\s*([^\n]+)$", metadata, re.MULTILINE)
            description = re.search(r"^description:\s*(.*)$", metadata, re.MULTILINE)
            self.assertIsNotNone(name, path)
            self.assertIsNotNone(description, path)
            self.assertEqual(name.group(1).strip(), path.parent.name, path)

    def test_relayforge_skill_references_resolve(self):
        available = {path.parent.name for path in skill_files()}
        missing = []
        for path in skill_files():
            for name in re.findall(r"relayforge:([a-z0-9-]+)", path.read_text(encoding="utf-8")):
                if name not in available:
                    missing.append(f"{path.relative_to(ROOT)} -> {name}")
        self.assertEqual(missing, [])

    def test_skill_markdown_links_resolve(self):
        missing = []
        for path in skill_files():
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)", text):
                if "://" in target:
                    continue
                if not (path.parent / target).resolve().exists():
                    missing.append(f"{path.relative_to(ROOT)} -> {target}")
        self.assertEqual(missing, [])

    def test_core_router_is_stack_neutral(self):
        router = (SKILLS / "task-router" / "SKILL.md").read_text(encoding="utf-8").lower()
        for technology in ("react", "spring", "postgres", "mybatis", "express", "next.js"):
            self.assertNotIn(technology, router)
        self.assertIn("quick", router)
        self.assertIn("standard", router)
        self.assertIn("large", router)

    def test_finishing_requires_an_explicit_choice(self):
        finishing = (SKILLS / "finishing-development" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Silence is not a selection", finishing)
        self.assertIn("do not emit a final workflow-status line", finishing)

    def test_router_avoids_redundant_generic_debugging_load(self):
        router = (SKILLS / "task-router" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Do not add a generic debugging skill", router)
        self.assertIn("do not repeat equivalent", router)

        debugging = (SKILLS / "systematic-debugging" / "SKILL.md").read_text(encoding="utf-8")
        metadata = frontmatter(debugging)
        self.assertIn("Do not use for a simple local bug", metadata)

    def test_large_execution_avoids_unrequested_plan_and_trivial_frontend_skill(self):
        planning = frontmatter((SKILLS / "writing-plans" / "SKILL.md").read_text(encoding="utf-8"))
        frontend = frontmatter((SKILLS / "frontend-patterns" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("Do not use for an already-approved task", planning)
        self.assertIn("Never use for a mechanical copy", frontend)

        backend = frontmatter((SKILLS / "backend-patterns" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("Never use for Java or Spring code", backend)

    def test_router_does_not_bias_large_routes_toward_data(self):
        router = (SKILLS / "task-router" / "SKILL.md").read_text(encoding="utf-8")
        self.assertRegex(router, r"Include `data` only for a\s+real persistence")
        self.assertRegex(router, r"use `integration` for a shared\s+contract")

    def test_full_stack_backend_handoff_precedes_dependent_frontend_work(self):
        router = (SKILLS / "task-router" / "SKILL.md").read_text(encoding="utf-8")
        workflow = (SKILLS / "development-workflow" / "SKILL.md").read_text(encoding="utf-8")
        handoff = (
            SKILLS
            / "development-workflow"
            / "references"
            / "backend-frontend-handoff.md"
        ).read_text(encoding="utf-8")

        self.assertIn("Mark the handoff as `full-stack` only when", router)
        self.assertIn("automatically export a frontend handoff", workflow)
        self.assertIn("before contract-dependent frontend", workflow)
        self.assertIn(".relayforge/handoffs/<task-slug>/backend-to-frontend.md", handoff)
        self.assertIn("Do not copy whole source files", handoff)

    def test_task_branch_is_default_and_worktrees_require_true_parallelism(self):
        workflow = (SKILLS / "development-workflow" / "SKILL.md").read_text(encoding="utf-8")
        router = (SKILLS / "task-router" / "SKILL.md").read_text(encoding="utf-8")
        branch_protocol = (
            SKILLS
            / "development-workflow"
            / "references"
            / "task-branch.md"
        ).read_text(encoding="utf-8")
        parallel_protocol = (
            SKILLS
            / "development-workflow"
            / "references"
            / "parallel-worktrees.md"
        ).read_text(encoding="utf-8")
        script = (
            SKILLS
            / "development-workflow"
            / "scripts"
            / "parallel_worktree.py"
        ).read_text(encoding="utf-8")

        standard = workflow.split("## Standard", 1)[1].split("## Large", 1)[0]
        self.assertIn("do not create implementation agents, worktrees", standard)
        self.assertIn("Never create a worktree for Quick work", router)
        self.assertIn("Use one task branch as the normal isolation boundary", branch_protocol)
        self.assertIn("handoff is sequential", parallel_protocol)
        self.assertIn('["git", "worktree", "add", "--detach"', script)
        self.assertIn('["git", "worktree", "remove", "--force"', script)
        self.assertNotIn('"prune"', script)


if __name__ == "__main__":
    unittest.main()
