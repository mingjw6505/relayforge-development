from pathlib import Path
import hashlib
import json
import unittest

from test_skill_structure import audit_dependencies


ROOT = Path(__file__).resolve().parents[1]


class UpstreamDependenciesTests(unittest.TestCase):
    def test_imported_files_match_pinned_upstream_blobs(self):
        inventory = json.loads((ROOT / 'third-party/upstream-dependencies.json').read_text(encoding='utf-8'))
        self.assertEqual(inventory['schema_version'], 1)
        self.assertTrue(inventory['sources'])
        seen = set()
        for source in inventory['sources']:
            self.assertRegex(source['commit'], r'^[0-9a-f]{40}$')
            self.assertTrue(source['files'])
            self.assertTrue(any(item['upstream_path'] == 'LICENSE' for item in source['files']))
            for item in source['files']:
                relative = item['local_path']
                with self.subTest(source=source['repository'], path=relative):
                    path = (ROOT / relative).resolve()
                    self.assertTrue(path.is_relative_to(ROOT.resolve()))
                    self.assertNotIn(relative, seen)
                    seen.add(relative)
                    content = path.read_bytes()
                    blob = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
                    self.assertEqual(blob, item['git_blob_sha1'], 'Upstream content changed; update the pinned import explicitly')

    def test_restored_workflows_have_all_packaged_dependencies(self):
        metadata = json.loads((ROOT / 'skills/task-router/references/optional-workflows.json').read_text(encoding='utf-8'))
        errors, statuses = audit_dependencies(ROOT, metadata['optional_workflows'])
        self.assertEqual(errors, [])
        for name in ('improve-codebase-architecture', 'subagent-driven-development'):
            self.assertEqual(statuses[name], {'available': True, 'missing': []}, name)


if __name__ == '__main__':
    unittest.main()
