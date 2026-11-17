#!/usr/bin/env python3
"""Run the frozen CLI with a guarded fallback for an empty HTTP model name."""

import hashlib
import os
from pathlib import Path
import re

from aerotizen import cli, home, remote

ORIGINAL_DEVICE_INFO = home.device_info


def device_info(session, host, *, backup=None, state_dir=None):
    info = ORIGINAL_DEVICE_INFO(session, host, backup=backup, state_dir=state_dir)
    if info.get("modelName") != "":
        return info

    identity = session.duid().strip()
    if not identity or "fail" in identity.lower():
        raise home.HomeError("Empty HTTP model and no valid live SDK identity; refusing fallback.")
    digest = hashlib.sha256(identity.encode()).hexdigest()
    directory = Path(state_dir) if state_dir is not None else Path(remote.CONFIG_DIR)
    path = Path(backup) if backup is not None else directory / "backups" / digest / "original-home.json"
    saved, _ = home._load_backup(path.expanduser(), digest)

    banner = session.banner
    match = re.fullmatch(r"device::([^:\r\n]+)::0", banner) if isinstance(banner, str) else None
    if match is None or match[1] != saved["device"]["model"]:
        raise home.HomeError("Live SDK model does not match the original backup; refusing fallback.")
    platform = info.get("model")
    if not isinstance(platform, str) or not platform or platform != saved["device"].get("platform"):
        raise home.HomeError("Live HTTP platform does not match the original backup; refusing fallback.")
    if session.duid().strip() != identity:
        raise home.HomeError("SDK identity changed while resolving the empty model; refusing fallback.")

    return {
        **info,
        "modelName": match[1],
        "_aerotizen_metadata_source": "live SDK banner; model and HTTP platform verified against identity-bound original backup",
    }


def main():
    os.umask(0o077)
    home.device_info = device_info
    try:
        cli.main()
    finally:
        home.device_info = ORIGINAL_DEVICE_INFO


if __name__ == "__main__":
    main()
