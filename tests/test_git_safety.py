from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from repogc.git_info import _git, repository_info, last_touch


class GitSafetyTests(unittest.TestCase):
    def test_git_reads_disable_helpers_writes_and_environment_redirection(self):
        with patch.dict(os.environ, {"GIT_DIR": "/unrelated", "GIT_INDEX_FILE": "/unrelated/index",
                                     "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor",
                                     "GIT_CONFIG_VALUE_0": "untrusted"}):
            with patch("repogc.git_info.subprocess.run") as run:
                _git(Path("/fixture"), "status", "--porcelain=v1")
        argv = run.call_args.args[0]
        env = run.call_args.kwargs["env"]
        self.assertIn("core.fsmonitor=false", argv)
        self.assertIn("core.hooksPath=" + os.devnull, argv)
        self.assertIn("protocol.allow=never", argv)
        self.assertIn("log.showSignature=false", argv)
        self.assertEqual(env["GIT_OPTIONAL_LOCKS"], "0")
        self.assertEqual(env["GIT_NO_LAZY_FETCH"], "1")
        for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_CONFIG_COUNT", "GIT_CONFIG_VALUE_0"):
            self.assertNotIn(name, env)

    def test_disabled_git_never_invokes_subprocess(self):
        with patch("repogc.git_info.subprocess.run") as run:
            repository_info(Path("/fixture"), False)
            self.assertIsNone(last_touch(Path("/fixture"), "file.md", False))
            run.assert_not_called()

    def test_configured_filter_skips_status_and_keeps_dirty_unknown(self):
        def git_reply(root, *args):
            values = {"rev-parse": "true\n" if "--is-inside-work-tree" in args else "commit\n",
                      "branch": "main\n", "config": "filter.fixture.clean\n"}
            self.assertNotEqual(args[0], "status")
            return subprocess.CompletedProcess(args, 0, values[args[0]], "")
        with patch("repogc.git_info._git", side_effect=git_reply):
            info, reason = repository_info(Path("/fixture"), True)
        self.assertIsNone(info["dirty"])
        self.assertIn("content filters", reason)

    def test_real_repository_helper_is_not_invoked_and_index_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def setup(*args):
                subprocess.run(["git", "-c", "init.templateDir=", "-c",
                                "core.hooksPath=" + os.devnull, "-C", str(root), *args],
                               check=True, capture_output=True)
            setup("init")
            (root / "README.md").write_text("# Fixture\n", encoding="utf-8")
            setup("add", "README.md")
            setup("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                  "commit", "-m", "fixture", "--no-gpg-sign")
            helper = root / "helper.sh"
            helper.write_text("#!/bin/sh\nprintf invoked > helper-invoked\n", encoding="utf-8")
            helper.chmod(0o700)
            setup("config", "core.fsmonitor", str(helper))
            index = root / ".git/index"
            before = index.read_bytes()
            before_mtime = index.stat().st_mtime_ns
            info, error = repository_info(root, True)
            self.assertIsNone(error)
            self.assertTrue(info["commit"])
            self.assertIsNotNone(last_touch(root, "README.md", True))
            self.assertFalse((root / "helper-invoked").exists())
            self.assertEqual(index.read_bytes(), before)
            self.assertEqual(index.stat().st_mtime_ns, before_mtime)
            setup("config", "filter.fixture.clean", str(helper))
            (root / ".gitattributes").write_text("*.md filter=fixture\n", encoding="utf-8")
            (root / "README.md").write_text("changed for filter test\n", encoding="utf-8")
            info, reason = repository_info(root, True)
            self.assertIsNone(info["dirty"])
            self.assertIn("content filters", reason)
            self.assertFalse((root / "helper-invoked").exists())
