# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class HistoricalRoutingTests(unittest.TestCase):
    def verify_workflow(self, name, step):
        source = (ROOT/'.github/workflows'/name).read_text()
        self.assertIn('git worktree add --detach "$RUNNER_TEMP/freedos-pc88va" f0edeaa35126cf6d027adac0316df5056f7b1ddb', source)
        section = source.split('- name: '+step, 1)[1].split('- name:', 1)[0]
        self.assertIn('working-directory: ${{ env.HISTORICAL_ROOT || github.workspace }}', section)
        self.assertNotIn('continue-on-error', source)

    def test_m07r3_immutable_prerequisites(self):
        self.verify_workflow('m07r3-fdd-boot-path.yml', 'Rebuild accepted public prerequisites')

    def test_m07r4_immutable_prerequisites(self):
        self.verify_workflow('m07r4-boot-reconstruction.yml', 'Rebuild accepted public prerequisites')

    def test_m07_completion_immutable_prerequisites(self):
        self.verify_workflow('m07-completion.yml', 'Regenerate immutable M05 and M06 prerequisites')
