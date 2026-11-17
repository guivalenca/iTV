"""A rebuild must preserve the CLI used to restore the TV's home."""

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "itv_build", Path(__file__).resolve().parents[1] / "scripts/build.py"
)
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class RecoveryCliPreservationTests(unittest.TestCase):
    def test_incomplete_existing_environment_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            cli = Path(directory) / "cli"
            cli.mkdir()
            marker = cli / "keep-this-environment"
            marker.write_text("recovery environment")

            with patch.object(build, "CLI_VENV", cli), patch.object(build, "run") as run:
                with self.assertRaisesRegex(SystemExit, "existing environment was preserved"):
                    build.install_cli(False, None)

            run.assert_not_called()
            self.assertEqual(marker.read_text(), "recovery environment")

    def test_different_source_cannot_replace_existing_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cli = root / "cli"
            package = cli / "lib/python3.12/site-packages/aerotizen"
            package.mkdir(parents=True)
            installed = package / "__init__.py"
            installed.write_text("original recovery code")
            work = root / "work"
            source = work / "cli/src/aerotizen"
            source.mkdir(parents=True)
            (source / "__init__.py").write_text("different code")

            with (
                patch.object(build, "CLI_VENV", cli),
                patch.object(build, "WORK", work),
                patch.object(build, "run") as run,
            ):
                with self.assertRaisesRegex(SystemExit, "was preserved"):
                    build.install_cli(False, None)

            run.assert_not_called()
            self.assertEqual(installed.read_text(), "original recovery code")

    def test_failed_initial_install_removes_only_the_new_partial_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            cli = Path(directory) / "cli"

            def fail_install(command, **kwargs):
                if "venv" in command:
                    cli.mkdir()
                    (cli / "partial").write_text("unfinished install")
                    return
                raise subprocess.CalledProcessError(1, command)

            with patch.object(build, "CLI_VENV", cli), patch.object(build, "run", side_effect=fail_install):
                with self.assertRaises(subprocess.CalledProcessError):
                    build.install_cli(False, None)

            self.assertFalse(cli.exists())


class BuildApprovalTests(unittest.TestCase):
    def test_previous_receipt_is_archived_and_no_longer_approves_current_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = root / "dist/build-receipt.json"
            receipt.parent.mkdir()
            contents = b'{"previous": "verified build"}\n'
            receipt.write_bytes(contents)
            cache = root / "cache"

            with patch.object(build, "RECEIPT_PATH", receipt), patch.object(build, "CACHE", cache):
                build.archive_receipt()

            self.assertFalse(receipt.exists())
            archives = list((cache / "receipts").glob("*.json"))
            self.assertEqual(len(archives), 1)
            self.assertEqual(archives[0].read_bytes(), contents)

    def test_cli_source_changes_and_git_errors_stop_verification(self):
        for status in (1, 128):
            with self.subTest(status=status):
                result = subprocess.CompletedProcess([], status)
                with patch.object(build.subprocess, "run", return_value=result), patch.object(build, "run") as run:
                    with self.assertRaisesRegex(SystemExit, "Pinned CLI verification failed"):
                        build.verify_cli_source("reference")
                run.assert_not_called()

    def test_untracked_cli_source_cannot_bypass_verification(self):
        result = subprocess.CompletedProcess([], 0)
        with (
            patch.object(build.subprocess, "run", return_value=result),
            patch.object(build, "run", return_value="cli/new_source.py"),
        ):
            with self.assertRaisesRegex(SystemExit, "Unexpected CLI source files"):
                build.verify_cli_source("reference")


if __name__ == "__main__":
    unittest.main()
