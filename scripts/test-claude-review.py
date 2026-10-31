#!/usr/bin/env python3
"""Exercise the review runner with a local fake Claude; no network or dependencies."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/claude-review.py"
FAKE = r'''#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time
from pathlib import Path
Path(os.environ["FAKE_LAUNCH"]).write_text("launched")
prompt = sys.stdin.read()
mode = os.environ.get("FAKE_MODE", "success")
if mode in ("hang", "orphan"):
    signal.signal(signal.SIGTERM, signal.SIG_IGN if mode == "hang" else signal.SIG_DFL)
    child_code = "import os,signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN if os.environ['FAKE_MODE']=='orphan' else signal.SIG_DFL);Path(os.environ['FAKE_CHILD_READY']).touch();time.sleep(30)"
    child = subprocess.Popen([sys.executable, "-c", child_code], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while not Path(os.environ["FAKE_CHILD_READY"]).exists():
        time.sleep(.01)
    Path(os.environ["FAKE_PIDS"]).write_text(f"{os.getpid()} {child.pid}")
    child.wait()
    time.sleep(30)
    sys.exit(0)
captured = {"argv": sys.argv[1:], "cwd": os.getcwd(), "prompt": prompt,
            "pid": os.getpid(), "pgid": os.getpgrp(),
            "files": sorted(str(p) for p in Path().rglob("*") if p.is_file()),
            "hashes": {str(p): __import__("hashlib").sha256(p.read_bytes()).hexdigest()
                       for p in Path().rglob("*") if p.is_file()},
            "effort": os.environ.get("CLAUDE_CODE_EFFORT_LEVEL"),
            "disable_mds": os.environ.get("CLAUDE_CODE_DISABLE_CLAUDE_MDS"),
            "auth": os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")}
response = {"result": json.dumps(captured), "modelUsage": {"claude-opus-5-5": {}}}
if mode == "no_opus": response["modelUsage"] = {"claude-sonnet-4-6": {}}
if mode == "missing_usage": response.pop("modelUsage")
if mode == "is_error": response["is_error"] = True
if mode == "permission_denials": response["permission_denials"] = [{"tool": "Read"}]
if mode == "empty": response["result"] = " "
if mode == "nonobject": response = []
if mode in ("invalid", "exit_invalid"):
    print("not JSON")
else:
    print(json.dumps(response))
sys.exit(7 if mode == "exit_invalid" else 0)
'''


class ReviewRunnerTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="review-test-", dir=ROOT / "work")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.bundle = self.directory / "input"
        self.bundle.mkdir()
        self.prompt = self.bundle / "prompt.md"
        self.prompt.write_text("Read candidate.txt and nested/evidence.txt. Review the candidate.\n")
        (self.bundle / "candidate.txt").write_text("candidate\n")
        (self.bundle / "nested").mkdir()
        (self.bundle / "nested/evidence.txt").write_bytes(b"evidence\x00\xff")
        self.output = self.directory / "receipt.json"
        self.launch = self.directory / "launched"
        self.pids = self.directory / "pids"
        self.binary = self.directory / "bin"
        self.binary.mkdir()
        (self.binary / "claude").write_text(FAKE)
        (self.binary / "claude").chmod(0o755)
        self.environment = dict(os.environ, PATH=str(self.binary) + os.pathsep + os.environ["PATH"],
                                FAKE_LAUNCH=str(self.launch), FAKE_PIDS=str(self.pids),
                                FAKE_CHILD_READY=str(self.directory / "child-ready"),
                                CLAUDE_CODE_EFFORT_LEVEL="low", CLAUDE_CODE_DISABLE_CLAUDE_MDS="0",
                                CLAUDE_CODE_OAUTH_TOKEN="fake-subscription-token")

    def command(self, prompt=None, output=None):
        return [sys.executable, str(RUNNER), str(prompt or self.prompt), str(output or self.output)]

    def run_review(self, mode="success", prompt=None, output=None):
        return subprocess.run(self.command(prompt, output), env=dict(self.environment, FAKE_MODE=mode),
                              text=True, capture_output=True, timeout=8)

    def receipt(self):
        return json.loads(self.output.read_text())

    def test_success_uses_only_snapshot_and_requested_configuration(self):
        before = {str(p.relative_to(self.bundle)): p.read_bytes()
                  for p in self.bundle.rglob("*") if p.is_file()}
        (self.directory / "previous-scores.json").write_text("do not copy")
        result = self.run_review()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = self.receipt()
        captured = json.loads(receipt["response"]["result"])
        config = json.loads((ROOT / ".claude/settings.json").read_text())
        self.assertEqual(receipt["requested_model"], config["model"])
        self.assertEqual(receipt["requested_effort"], config["effortLevel"])
        self.assertEqual(captured["effort"], config["effortLevel"])
        self.assertEqual(captured["disable_mds"], "1")
        self.assertEqual(captured["auth"], "fake-subscription-token")
        argv = captured["argv"]
        for flag, value in (("--permission-mode", "dontAsk"), ("--model", config["model"]),
                            ("--effort", config["effortLevel"]), ("--tools", "Read,Glob,Grep"),
                            ("--allowedTools", "Read,Glob,Grep"), ("--output-format", "json")):
            self.assertEqual(argv[argv.index(flag) + 1], value)
        self.assertEqual(json.loads(argv[argv.index("--settings") + 1]),
                         {"autoMemoryEnabled": False, "disableAllHooks": True})
        self.assertEqual(json.loads(argv[argv.index("--mcp-config") + 1]), {"mcpServers": {}})
        for flag in ("--restricted", "--strict-mcp-config", "--disable-slash-commands",
                     "--no-session-persistence", "-p"):
            self.assertIn(flag, argv)
        for flag in ("--bare", "--resume", "--continue", "--fallback-model"):
            self.assertNotIn(flag, argv)
        self.assertEqual(receipt["command"][1:], argv)
        self.assertEqual(receipt["input_directory"], str(self.bundle.resolve()))
        self.assertEqual(captured["files"], sorted(before))
        self.assertEqual(receipt["input_sha256"], captured["hashes"])
        self.assertEqual(receipt["input_sha256"], {p: hashlib.sha256(data).hexdigest() for p, data in before.items()})
        self.assertEqual(before, {str(p.relative_to(self.bundle)): p.read_bytes()
                                  for p in self.bundle.rglob("*") if p.is_file()})
        snapshot = Path(captured["cwd"])
        self.assertFalse(snapshot.resolve().is_relative_to(ROOT))
        self.assertEqual(Path(receipt["snapshot_directory"]).resolve(), snapshot.resolve())
        self.assertFalse(snapshot.exists())
        self.assertIn(self.prompt.read_text(), captured["prompt"])
        self.assertIn("Do not start workflows or subagents", captured["prompt"])
        self.assertIn("You cannot execute tests or commands", captured["prompt"])
        self.assertIn("Claude reviewer PID/PGID:", result.stderr)
        self.assertEqual(receipt["child_pid"], captured["pid"])
        self.assertEqual(receipt["child_pgid"], captured["pgid"])
        self.assertIsNone(receipt["error"])

    def test_cleanup_permission_error_preserves_diagnostics(self):
        spec = importlib.util.spec_from_file_location("claude_review", RUNNER)
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, "dont_write_bytecode", True):
            spec.loader.exec_module(module)
        process = Mock(pid=123456)
        process.communicate.return_value = "partial output", "partial error"
        with patch.object(module.os, "killpg", side_effect=PermissionError("denied")):
            stdout, stderr = module.stop_process(process)
        self.assertEqual(stdout, "partial output")
        self.assertIn("partial error", stderr)
        self.assertIn("Could not signal Claude process group 123456", stderr)
        self.assertIn("Could not kill Claude process group 123456", stderr)

    def test_incomplete_cleanup_keeps_partial_output(self):
        spec = importlib.util.spec_from_file_location("claude_review", RUNNER)
        module = importlib.util.module_from_spec(spec)
        with patch.object(sys, "dont_write_bytecode", True):
            spec.loader.exec_module(module)
        process = Mock(pid=123456)
        process.communicate.side_effect = [
            subprocess.TimeoutExpired("claude", 1),
            subprocess.TimeoutExpired("claude", 1, output=b"partial\xffoutput", stderr=b"partial error"),
        ]
        with patch.object(module.os, "killpg", side_effect=PermissionError("denied")):
            stdout, stderr = module.stop_process(process)
        self.assertEqual(stdout, "partial\ufffdoutput")
        self.assertIn("partial error", stderr)
        self.assertIn("Cleanup incomplete", stderr)

    def test_invalid_responses_keep_failure_receipt(self):
        for mode, expected in (("no_opus", "Opus"), ("missing_usage", "Opus"),
                               ("is_error", "reported an error"), ("permission_denials", "permission denials"),
                               ("empty", "no review result"), ("nonobject", "JSON object"),
                               ("invalid", "invalid JSON"), ("exit_invalid", "status 7")):
            with self.subTest(mode=mode):
                self.output = self.directory / (mode + ".json")
                result = self.run_review(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, self.receipt()["error"])
                self.assertIn(expected, result.stderr)
                if mode == "exit_invalid":
                    self.assertEqual(self.receipt()["returncode"], 7)
                    self.assertEqual(self.receipt()["raw_stdout"], "not JSON\n")

    def test_existing_output_is_never_overwritten_or_launched(self):
        self.output.write_text("existing receipt")
        result = self.run_review()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.output.read_text(), "existing receipt")
        self.assertFalse(self.launch.exists())

    def test_output_in_bundle_and_root_prompt_are_refused(self):
        for prompt, output in ((self.prompt, self.bundle / "output.json"), (ROOT / "README.md", self.output)):
            with self.subTest(prompt=prompt, output=output):
                self.assertNotEqual(self.run_review(prompt=prompt, output=output).returncode, 0)
                self.assertFalse(self.launch.exists())
                self.assertFalse(output.exists())

    def test_symlinks_and_git_entries_are_refused(self):
        for name, kind in (("link", "file"), ("link", "directory"), (".git", "file"), (".git", "directory")):
            with self.subTest(name=name, kind=kind):
                entry = self.bundle / name
                if name == "link":
                    entry.symlink_to(self.prompt if kind == "file" else self.directory, target_is_directory=kind == "directory")
                elif kind == "directory":
                    entry.mkdir()
                else:
                    entry.touch()
                self.output = self.directory / (kind + name + ".json")
                self.assertNotEqual(self.run_review().returncode, 0)
                self.assertFalse(self.launch.exists())
                self.assertIn("forbidden entry", self.receipt()["error"])
                if entry.is_dir() and not entry.is_symlink():
                    entry.rmdir()
                else:
                    entry.unlink()

    def check_interruption(self, signum, repeated=False, mode="hang"):
        process = subprocess.Popen(self.command(), env=dict(self.environment, FAKE_MODE=mode),
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        pids = []
        try:
            deadline = time.monotonic() + 5
            while not self.pids.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(self.pids.exists(), "fake Claude did not become ready")
            pids = list(map(int, self.pids.read_text().split()))
            process.send_signal(signum)
            if repeated:
                time.sleep(.1)
                process.send_signal(signum)
            _stdout, stderr = process.communicate(timeout=6)
            self.assertNotEqual(process.returncode, 0, stderr)
            receipt = self.receipt()
            self.assertEqual(receipt["error"], "Review interrupted")
            self.assertEqual(receipt["signal"], signum)
            self.assertEqual(receipt["child_pid"], pids[0])
            self.assertIn(f"Claude reviewer PID/PGID: {pids[0]}", stderr)
            self.assertNotEqual(receipt["returncode"], 0)
            for pid in pids:
                deadline = time.monotonic() + 1
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    status = Path(f"/proc/{pid}/stat")
                    if status.exists() and status.read_text().split(") ", 1)[1].startswith("Z"):
                        break
                    self.assertLess(time.monotonic(), deadline, f"owned process {pid} remains alive")
                    time.sleep(.02)
        finally:
            if pids:
                try:
                    os.killpg(pids[0], signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if process.poll() is None:
                process.kill()
            process.communicate()

    def test_sigint_cleans_owned_process_group(self):
        self.check_interruption(signal.SIGINT)

    def test_sigterm_cleans_owned_process_group(self):
        self.check_interruption(signal.SIGTERM)

    def test_repeated_signal_keeps_failure_receipt(self):
        self.check_interruption(signal.SIGTERM, repeated=True)

    def test_descendant_cannot_survive_claude_exiting_first(self):
        self.check_interruption(signal.SIGTERM, mode="orphan")


if __name__ == "__main__":
    unittest.main()
