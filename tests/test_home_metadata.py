"""Empty model recovery must preserve the real Home preflight's refusal cases."""

import copy
from contextlib import nullcontext, redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from aerotizen import cli, home, home_control

SPEC = importlib.util.spec_from_file_location(
    "itv_home", Path(__file__).resolve().parents[1] / "scripts/aerotizen-home.py"
)
wrapper = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wrapper)


class ModelMetadataTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name)
        self.identity = "TEST-TV-DUID"
        self.digest = hashlib.sha256(self.identity.encode()).hexdigest()
        self.session = Mock(banner="device::TEST-TV::0")
        self.session.duid.return_value = self.identity
        self.status = {
            "schema_version": 1,
            "queried_at": "2026-11-16T00:00:00+00:00",
            "complete": True,
            "device": {
                "identity_sha256": self.digest,
                "model": "TEST-TV",
                "platform": "TEST-PLATFORM",
                "firmware_build": "TEST-FIRMWARE",
                "cpu_arch": "armv7",
                "os_version": "9.0.0",
            },
            "home": {
                "operation": home.OPERATION,
                "main_operation": {"type": "string", "status": "ok", "value": "com.samsung.tv.csfs"},
                "settings": {
                    key: {"type": kind, "status": "ok", "value": 0 if kind == "int" else "com.samsung.tv.csfs"}
                    for key, kind in home.SETTINGS.items()
                },
            },
            "launcher": {"installed": True},
            "evidence": {
                "access": "sdk_uid_901", "uid": 901, "authenticated": True,
                "sdk_staging_cleaned": True, "query_staging_cleaned": True,
                "helper_sha256": "b" * 64,
            },
        }
        saved = home.save_backup(self.status, state_dir=self.state)
        self.backup = Path(saved["path"])
        self.original_bytes = self.backup.read_bytes()
        self.original, _ = home._load_backup(self.backup, self.digest)

    def resolve(self, info=None, **kwargs):
        if info is None:
            info = {"modelName": "", "model": "TEST-PLATFORM"}
        with patch.object(wrapper, "ORIGINAL_DEVICE_INFO", return_value=info):
            return wrapper.device_info(self.session, "192.0.2.1", state_dir=self.state, **kwargs)

    def assert_preflight(self, info, **changes):
        status = copy.deepcopy(self.status)
        status["device"].update(model=info.get("modelName"), **changes)
        return home_control._check_preflight(status, self.original)

    def test_empty_http_model_uses_live_sdk_model_and_passes_real_preflight(self):
        info = {"modelName": "", "model": "TEST-PLATFORM", "other": "preserved"}
        resolved = self.resolve(info)
        self.assertTrue(self.assert_preflight(resolved))
        self.assertEqual(resolved["other"], "preserved")
        self.assertIn("SDK", resolved["_aerotizen_metadata_source"])
        self.assertEqual(info["modelName"], "")
        self.assertEqual(self.backup.read_bytes(), self.original_bytes)

    def test_nonempty_http_model_is_never_overridden(self):
        info = {"modelName": "OTHER-TV", "model": "TEST-PLATFORM"}
        self.assertIs(self.resolve(info), info)
        self.session.duid.assert_not_called()
        with self.assertRaises(home.HomeError):
            self.assert_preflight(info)

    def test_firmware_os_architecture_and_identity_changes_still_fail(self):
        resolved = self.resolve()
        for key, value in (("firmware_build", "NEW-FIRMWARE"), ("os_version", "10.0.0"),
                           ("cpu_arch", "aarch64"), ("identity_sha256", "c" * 64)):
            with self.subTest(key=key), self.assertRaises(home.HomeError):
                self.assert_preflight(resolved, **{key: value})

    def test_missing_or_nonstring_http_models_are_not_repaired(self):
        for value in (None, 0, " "):
            with self.subTest(value=value):
                info = {"modelName": value, "model": "TEST-PLATFORM"}
                self.assertIs(self.resolve(info), info)
                with self.assertRaises(home.HomeError):
                    self.assert_preflight(info)

    def test_invalid_sdk_banner_is_refused(self):
        for banner in ("", "device::TEST-TV::1", "device::TEST-TV::0\n", "device::OTHER-TV::0"):
            with self.subTest(banner=banner):
                self.session.banner = banner
                with self.assertRaises(home.HomeError):
                    self.resolve()

    def test_platform_mismatch_is_refused(self):
        with self.assertRaises(home.HomeError):
            self.resolve({"modelName": "", "model": "OTHER-PLATFORM"})

    def test_missing_saved_platform_is_refused(self):
        for platform in (None, ""):
            with self.subTest(platform=platform):
                document = copy.deepcopy(self.original)
                document["device"]["platform"] = platform
                self.backup.write_text(json.dumps(document))
                with self.assertRaises(home.HomeError):
                    self.resolve()
        document["device"].pop("platform")
        self.backup.write_text(json.dumps(document))
        with self.assertRaises(home.HomeError):
            self.resolve()

    def test_missing_backup_is_refused_without_creating_one(self):
        self.backup.unlink()
        with self.assertRaises(home.HomeError):
            self.resolve()
        self.assertFalse(self.backup.exists())

    def test_corrupt_or_other_device_backup_is_refused(self):
        for raw in (b"not-json", self.original_bytes.replace(self.digest.encode(), b"c" * 64)):
            with self.subTest(raw=raw[:8]):
                self.backup.write_bytes(raw)
                with self.assertRaises(home.HomeError):
                    self.resolve()

    def test_sdk_identity_change_during_resolution_is_refused(self):
        self.session.duid.side_effect = [self.identity, "ANOTHER-DUID"]
        with self.assertRaises(home.HomeError):
            self.resolve()

    def test_invalid_sdk_identity_is_refused(self):
        for identity in ("", "fail"):
            with self.subTest(identity=identity):
                self.session.duid.return_value = identity
                with self.assertRaises(home.HomeError):
                    self.resolve()

    def test_explicit_backup_is_supported(self):
        explicit = self.state / "exported/original-home.json"
        explicit.parent.mkdir()
        explicit.write_bytes(self.original_bytes)
        self.backup.unlink()
        self.assertTrue(self.assert_preflight(self.resolve(backup=explicit)))

    def test_upstream_metadata_errors_propagate(self):
        with patch.object(wrapper, "ORIGINAL_DEVICE_INFO", side_effect=home.HomeError("offline")):
            with self.assertRaisesRegex(home.HomeError, "offline"):
                wrapper.device_info(self.session, "192.0.2.1", state_dir=self.state)

    def run_cli(self, action):
        with (
            patch.object(cli, "STATE_DIR", str(self.state)),
            patch.object(cli, "require_sdb", return_value=nullcontext(self.session)),
            patch.object(cli.diagnostics, "run_logged", side_effect=lambda args, fn, state: fn(args)),
            patch.object(wrapper.remote, "info", return_value={"modelName": "", "model": "TEST-PLATFORM"}),
            patch.object(wrapper.os, "umask"),
            patch("sys.argv", ["aerotizen", "--tv", "192.0.2.1", "home", action, "--yes", "--json"]),
            redirect_stdout(io.StringIO()),
        ):
            wrapper.main()

    def test_real_cli_routes_guarded_metadata_to_apply_and_restore(self):
        original_function = home.device_info
        for action in ("apply", "restore"):
            with self.subTest(action=action), patch.object(home_control, "change", return_value={"success": True}) as change:
                self.run_cli(action)
                self.assertEqual(change.call_args.args[2], action)
                self.assertTrue(self.assert_preflight(change.call_args.args[1]))
                self.assertIs(home.device_info, original_function)

    def test_real_cli_refuses_bad_model_before_change_and_restores_function(self):
        original_function = home.device_info
        self.session.banner = "device::OTHER-TV::0"
        with patch.object(home_control, "change") as change:
            with self.assertRaises(SystemExit):
                self.run_cli("apply")
            change.assert_not_called()
        self.assertIs(home.device_info, original_function)


if __name__ == "__main__":
    unittest.main()
