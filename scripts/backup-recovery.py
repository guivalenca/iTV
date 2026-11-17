#!/usr/bin/env python3
"""Create a private local ZIP; this never uploads files or connects to the TV."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / ".config/aerotizen"
ARCHIVE_KIND = "itv.recovery"
PREFIX = "iTV-recovery/"
CERTIFICATE_FILES = {"author.p12", "distributor.p12", "password.txt", "device-profile.xml"}


def create_archive(output):
    os.umask(0o077)
    payloads = {}
    for directory in ("backups", "certs"):
        parent = STATE / directory
        for path in sorted(parent.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Recovery files must not be symlinks: {path}")
            if path.is_file():
                payloads["aerotizen/" + path.relative_to(STATE).as_posix()] = path.read_bytes()
    baselines = [name for name in payloads if name.endswith("/original-home.json")]
    if not baselines:
        raise ValueError("No original-home baseline found; refusing to create an empty recovery ZIP.")
    certs = STATE / "certs"
    certificates_ready = certs.exists() and any(
        folder.is_dir() and CERTIFICATE_FILES.issubset({p.name for p in folder.iterdir() if p.is_file()})
        for folder in certs.iterdir()
    )
    tools = {
        "tools/upstream.lock.json": ROOT / "upstream.lock.json",
        "tools/build-receipt.json": ROOT / "dist/build-receipt.json",
        "tools/aerotizen-3.0.1-py3-none-any.whl": ROOT / ".cache/recovery/wheels/aerotizen-3.0.1-py3-none-any.whl",
        "tools/aerotizen-pinned-source.tar": ROOT / ".cache/recovery/aerotizen-pinned-source.tar",
        "tools/launcher.patch": ROOT / "patches/0001-launcher-no-automatic-update-check.patch",
        "tools/AeroTizen-LICENSE.txt": ROOT / "dist/AeroTizen-LICENSE.txt",
        "tools/aerotizen-home.py": ROOT / "scripts/aerotizen-home.py",
        "tools/home-metadata-fallback.md": ROOT / "docs/home-metadata-fallback.md",
    }
    for patch in sorted((ROOT / "patches").glob("*.patch")):
        tools["tools/patches/" + patch.name] = patch
    stock = ROOT / ".cache/releases/stock-aerotizen-3.2.0"
    for name in ("aerotizen-launcher-3.2.0.wgt", "build-receipt.json"):
        path = stock / name
        if path.is_file():
            tools["tools/stock-launcher/" + name] = path
    for name, path in tools.items():
        payloads[name] = path.read_bytes()
    instructions = """iTV recovery backup

Keep this ZIP private. It may contain signing keys and their local unlock password.
It does not contain your Samsung account password or browser sign-in token.

The complete aerotizen/backups folder must be preserved, including transactions/.
Certificates allow updates signed by the same author; never replace them casually.
Refresh this ZIP after certificates are issued and after Home apply/restore so the
transaction receipts are included. Upload the refreshed ZIP to your private backup.

Recovery on a Mac (only when needed):
1. Extract the ZIP to a writable folder. Keep the TV on the same firmware.
2. Enable Developer Mode with that Mac's current local IP. Restart the TV.
3. Create a Python 3.12+ environment and install the included CLI wheel:
   python3.12 -m venv recovery-tools
   recovery-tools/bin/python -m pip install tools/aerotizen-3.0.1-py3-none-any.whl
   Python dependencies still need to be available from a package registry/cache.
   The wheel already includes both source-built Home helpers; no .NET SDK is needed.
4. Use the extracted original-home.json in its complete, writable backup folder:
   recovery-tools/bin/aerotizen --tv TV_IP home restore --backup PATH/original-home.json
   The command above is a preview. When recovery is required, use the same command
   with --yes to restore, then disconnect TV power for 60 seconds and check Home.
   If Samsung returns an empty HTTP model and the regular command refuses the
   device comparison, use the included guarded wrapper with the same arguments:
   recovery-tools/bin/python -I tools/aerotizen-home.py --tv TV_IP home restore --backup PATH/original-home.json --yes
   It accepts an empty model only when the live SDK model and HTTP platform both
   match the original backup for the live SDK identity. Firmware checks still run.
   See tools/home-metadata-fallback.md. A different or unavailable model is refused.
5. If the saved signing profile is needed for app updates, restore aerotizen/certs
   into ~/.config/aerotizen/certs and restrict its folders/files to your account.

Never uninstall the launcher while Native Home is active. Restore Samsung Home first.
Never update firmware, run root/debloat, or install unpinned upstream releases as recovery.
The pinned source and build receipt are included for inspection and reconstruction.
All current launcher patches are included in tools/patches/.
If tools/stock-launcher/ is present, it contains the previously tested AeroTizen UI
and its original build receipt. To roll back only the custom interface, restore the
saved signing profile first and update in place (never uninstall):
   recovery-tools/bin/aerotizen --tv TV_IP install tools/stock-launcher/aerotizen-launcher-3.2.0.wgt
This UI rollback is separate from restoring Samsung Home with home restore.
"""
    if not certificates_ready:
        instructions += "\nPREPARATION SNAPSHOT: signing certificates are not complete yet. Refresh before relying on this as the final backup.\n"
    payloads["README.txt"] = instructions.encode()
    manifest = {
        "kind": ARCHIVE_KIND,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "certificates_complete": certificates_ready,
        "files": {name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
                  for name, data in sorted(payloads.items())},
    }
    payloads["MANIFEST.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    if output.exists():
        with zipfile.ZipFile(output) as old:
            if json.loads(old.read(PREFIX + "MANIFEST.json")).get("kind") != ARCHIVE_KIND:
                raise ValueError("The output file is not an iTV recovery archive; it was preserved.")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".itv-recovery-", suffix=".zip", dir=output.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for name, data in sorted(payloads.items()):
                    archive.writestr(PREFIX + name, data)
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("ZIP integrity verification failed.")
            for name, data in payloads.items():
                if archive.read(PREFIX + name) != data:
                    raise ValueError(f"ZIP content verification failed: {name}")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Saved verified recovery ZIP: {output}")
    print(f"Size: {output.stat().st_size:,} bytes")
    print(f"Signing certificates complete: {certificates_ready}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path.home() / "Desktop/iTV-Recovery.zip")
    create_archive(parser.parse_args().output.expanduser().absolute())
