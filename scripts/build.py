#!/usr/bin/env python3
"""Build the pinned AeroTizen launcher, Home helpers and CLI on this Mac.

Nothing here talks to a TV. The script clones the pinned commit from the local source
cache into an ignored working copy, applies patches/*.patch, builds the launcher with
the upstream lockfile, builds the read-only Home query and guarded Home control .NET
helpers with the upstream helper scripts, installs the CLI from source into a venv and
writes dist/build-receipt.json.

  python3.12 scripts/build.py --preflight      check tools; works without dotnet
  python3.12 scripts/build.py --fetch-dotnet   download the pinned .NET SDK into .cache/
  python3.12 scripts/build.py [--dotnet PATH]  build everything
"""

import argparse
import base64
import hashlib
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "upstream.lock.json"
PATCHES = ROOT / "patches"
CACHE = ROOT / ".cache"
SOURCE = CACHE / "aerotizen-source"
BUILD = CACHE / "build"
WORK = BUILD / "aerotizen"
DEV_VENV = BUILD / "dev-venv"
DIST = ROOT / "dist"
LAUNCHER_OUT = DIST / "launcher"
WGT_OUT = DIST / "wgt"
CLI_VENV = DIST / "aerotizen-cli"
RECEIPT_PATH = DIST / "build-receipt.json"

# CONTRIBUTING.md: "CI uses SDK 6.0.428". Hashes copied from Microsoft's official
# release metadata, https://builds.dotnet.microsoft.com/dotnet/release-metadata/6.0/releases.json
# (release 6.0.36, sdk 6.0.428).
DOTNET_SDK_VERSION = "6.0.428"
DOTNET_SDK_DIR = CACHE / f"dotnet-sdk-{DOTNET_SDK_VERSION}"
DOTNET_SDK_ARCHIVES = {
    "arm64": (
        "https://builds.dotnet.microsoft.com/dotnet/Sdk/6.0.428/dotnet-sdk-6.0.428-osx-arm64.tar.gz",
        "b60e74b56efc5bdb05be9c954bca6fddbc6baa79213b120fd803c75252c54cf4"
        "a6f45255b532c18ceae8c4c1c2a60d2702309156f9ab1436bd71f68947c37215",
    ),
    "x86_64": (
        "https://builds.dotnet.microsoft.com/dotnet/Sdk/6.0.428/dotnet-sdk-6.0.428-osx-x64.tar.gz",
        "ffd6d342cc700cad4fe8fd6a29896d55f8bd7f687f5c2ef9ae68449c3c1cee48"
        "97d2318505075bab2a92538e0db8605df13559923d861d9123ba59c5fb0e5bd2",
    ),
}

# The two Home helpers: upstream build script, the files its manifest must hold, and the
# sources it hashes into source_sha256 (same order, NUL-joined, as the upstream script).
# The root runtime (build_root_runtime.py) is deliberately not built: root is out of scope.
HELPERS = {
    "home-query.json": (
        "cli/tools/build_home_query.py",
        ("AeroTizenHomeQuery.dll", "AeroTizenHomeQuery.runtimeconfig.json"),
        ("home-query/HomeQuery.cs", "home-query/HomeQuery.csproj", "home-common/Installation.cs"),
    ),
    "home-control.json": (
        "cli/tools/build_home_control.py",
        ("AeroTizenHomeControl.dll", "AeroTizenHomeControl.runtimeconfig.json"),
        (
            "home-control/HomeControl.cs",
            "home-control/ControlPolicy.cs",
            "home-control/Compatibility.cs",
            "home-control/HomeControl.csproj",
            "home-common/Installation.cs",
        ),
    ),
}
HELPER_TARGET_FRAMEWORK = "netcoreapp3.1"
# Host-side harness over the same policy sources (tests/test_home_control.py expects this line).
POLICY_PROJECT = "tests/native-home/PolicyTests.csproj"
POLICY_PASSED = "POLICY_TESTS_PASSED=114"

# Upstream checks for the launcher (CONTRIBUTING.md). `npm run build` runs typecheck first.
NPM_CHECKS = ("format:check", "lint", "test", "test:components", "test:service")
# Python tests for the built helpers and the install path. Tests that need root-runtime.json
# or the standalone binary (test_packaging, test_release_build, test_root_*) are left out.
CLI_TESTS = (
    "tests/test_home.py",
    "tests/test_home_control.py",
    "tests/test_home_probe.py",
    "tests/test_sdk.py",
    "tests/test_sdb.py",
    "tests/test_install.py",
    "tests/test_signer.py",
)
# Browser flows for the custom Home and the retained offline update behaviour.
BROWSER_TESTS = ("tests/browser/itv_home.spec.cjs", "tests/browser/launcher_updates.spec.cjs")

# The CLI venv is created with this interpreter. python.org 3.12 on this Mac has a working CA
# file; the 3.10 install's CA file is not reliable, and `certs` signs in over HTTPS.
MIN_PYTHON = (3, 12)
NODE_REQUIREMENT = "^20.19.0 || >=22.12.0"
NOTE = (
    "Source revision, patches and outputs are recorded here. Byte reproducibility is not claimed: "
    "npm packages follow the upstream lockfile, but Python packages (pip) and NuGet reference packs "
    "resolve at build time, and the launcher and helpers were built with the toolchain listed."
)


def environment(dotnet=None):
    """Keep caches and tool state under .cache/ instead of the user's global folders."""
    env = {
        **os.environ,
        "npm_config_cache": str(CACHE / "npm"),
        "npm_config_update_notifier": "false",
        "npm_config_fund": "false",
        "npm_config_audit": "false",
        "PIP_CACHE_DIR": str(CACHE / "pip"),
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PLAYWRIGHT_BROWSERS_PATH": str(CACHE / "ms-playwright"),
        "DOTNET_CLI_HOME": str(BUILD / "dotnet-home"),
        "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
        "DOTNET_NOLOGO": "1",
        "DOTNET_MULTILEVEL_LOOKUP": "0",
        "MSBUILDDISABLENODEREUSE": "1",
        "NUGET_PACKAGES": str(BUILD / "nuget-packages"),
        "NUGET_HTTP_CACHE_PATH": str(BUILD / "nuget-http-cache"),
        "NUGET_PLUGINS_CACHE_PATH": str(BUILD / "nuget-plugins-cache"),
    }
    if dotnet:
        env["AEROTIZEN_DOTNET"] = str(dotnet)
    return env


def run(command, *, cwd=WORK, env=None, capture=False):
    print("+", " ".join(str(part) for part in command), flush=True)
    result = subprocess.run(
        [str(part) for part in command],
        cwd=cwd,
        env=env or environment(),
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else None


def output_of(command):
    """First line of a tool's output, or None if it is not runnable."""
    try:
        text = subprocess.run(
            command, capture_output=True, text=True, timeout=60, check=True, env=environment()
        ).stdout
        return text.strip().splitlines()[0] if text.strip() else ""
    except (OSError, subprocess.SubprocessError):
        return None


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hashes(directory):
    """Per-file SHA-256 and one digest over the sorted (path, file hash) list."""
    files = {
        path.relative_to(directory).as_posix(): sha256_file(path)
        for path in sorted(directory.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    }
    listing = "".join(f"{name}\0{digest}\n" for name, digest in sorted(files.items()))
    return {"tree_sha256": hashlib.sha256(listing.encode()).hexdigest(), "files": files}


def read_lock():
    lock = json.loads(LOCK_PATH.read_text())
    for field in ("commit", "cli_tag_commit"):
        if not re.fullmatch(r"[0-9a-f]{40}", lock.get(field, "")):
            sys.exit(f"{LOCK_PATH}: '{field}' must be a full 40-character commit hash.")
    return lock


def node_satisfies(version):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version or "")
    if not match:
        return False
    major, minor, _ = (int(part) for part in match.groups())
    return (major == 20 and minor >= 19) or (major, minor) >= (22, 12)


def resolve_dotnet(explicit):
    """--dotnet, then AEROTIZEN_DOTNET, then the SDK fetched into .cache/, then PATH."""
    candidates = [
        explicit,
        os.environ.get("AEROTIZEN_DOTNET"),
        DOTNET_SDK_DIR / "dotnet",
        shutil.which("dotnet"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    return None


def dotnet_problem(dotnet):
    if dotnet is None:
        return (
            f".NET SDK {DOTNET_SDK_VERSION} not found. Pass --dotnet PATH, set AEROTIZEN_DOTNET, "
            "or run --fetch-dotnet."
        )
    version = output_of([str(dotnet), "--version"])
    if version != DOTNET_SDK_VERSION:
        return f"{dotnet} reports SDK {version!r}; this build requires {DOTNET_SDK_VERSION}."
    return None


def preflight(lock, dotnet):
    """Report every missing requirement at once. Returns True when a build can start."""
    checks = []
    cafile = ssl.get_default_verify_paths().cafile
    python_ok = sys.version_info >= MIN_PYTHON and bool(cafile) and Path(cafile).is_file()
    checks.append(("python", f"{sys.version.split()[0]} (CA file {cafile})", python_ok,
                   f"run with python{'.'.join(map(str, MIN_PYTHON))}+ that has a CA file, "
                   "e.g. /usr/local/bin/python3.12"))
    git_version = output_of(["git", "--version"])
    checks.append(("git", git_version, git_version is not None, "install git"))
    node_version = output_of(["node", "--version"])
    checks.append(("node", node_version, node_satisfies(node_version), f"needs {NODE_REQUIREMENT}"))
    npm_version = output_of(["npm", "--version"])
    checks.append(("npm", npm_version, npm_version is not None, "install npm with Node"))
    has_commit = (
        output_of(["git", "-C", str(SOURCE), "cat-file", "-t", lock["commit"] + "^{commit}"]) == "commit"
    )
    checks.append(("source", f"{SOURCE.relative_to(ROOT)} @ {lock['commit'][:12]}", has_commit,
                   f"clone {lock['repository']} into {SOURCE.relative_to(ROOT)}"))
    patches = sorted(PATCHES.glob("*.patch"))
    checks.append(("patches", ", ".join(p.name for p in patches) or "none", True, ""))
    problem = dotnet_problem(dotnet)
    checks.append(("dotnet", str(dotnet) if dotnet else "missing", problem is None, problem or ""))
    for name, value, ok, hint in checks:
        print(f"{'ok ' if ok else 'NO '} {name:8} {value}" + ("" if ok else f"  -> {hint}"))
    return all(ok for _, _, ok, _ in checks)


def fetch_dotnet():
    """Download the pinned SDK archive, verify SHA-512, then extract into .cache/."""
    if sys.platform != "darwin" or platform.machine() not in DOTNET_SDK_ARCHIVES:
        sys.exit(f"--fetch-dotnet supports macOS arm64/x86_64 only; install .NET SDK {DOTNET_SDK_VERSION} "
                 "yourself and pass --dotnet PATH.")
    url, expected = DOTNET_SDK_ARCHIVES[platform.machine()]
    downloads = CACHE / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    archive = downloads / url.rsplit("/", 1)[1]
    if not archive.exists() or hashlib.sha512(archive.read_bytes()).hexdigest() != expected:
        print(f"Downloading {url}", flush=True)
        partial = archive.with_suffix(".partial")
        with urllib.request.urlopen(url, timeout=60) as response, open(partial, "wb") as stream:
            shutil.copyfileobj(response, stream, 1 << 20)
        partial.replace(archive)
    actual = hashlib.sha512(archive.read_bytes()).hexdigest()
    if actual != expected:
        archive.unlink()
        sys.exit(f"SHA-512 mismatch for {archive.name}: expected {expected}, got {actual}. Deleted.")
    print(f"SHA-512 verified: {archive.name}")
    if DOTNET_SDK_DIR.exists():
        shutil.rmtree(DOTNET_SDK_DIR)
    DOTNET_SDK_DIR.mkdir(parents=True)
    run(["tar", "-xzf", archive, "-C", DOTNET_SDK_DIR], cwd=ROOT)
    version = output_of([str(DOTNET_SDK_DIR / "dotnet"), "--version"])
    if version != DOTNET_SDK_VERSION:
        sys.exit(f"Extracted SDK reports {version!r}, expected {DOTNET_SDK_VERSION}.")
    print(f"dotnet {version}: {DOTNET_SDK_DIR / 'dotnet'}")


def prepare_source(lock):
    """Fresh working copy of the pinned commit plus patches. The source cache is only read."""
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", "--quiet", "--no-checkout", SOURCE, WORK], cwd=ROOT)
    run(["git", "checkout", "--quiet", "--detach", lock["commit"]])
    head = run(["git", "rev-parse", "HEAD"], capture=True)
    if head != lock["commit"]:
        sys.exit(f"Working copy is at {head}, expected {lock['commit']}.")
    launcher_version = re.search(r'<widget [^>]*\bversion="([^"]+)"', (WORK / "launcher/config.xml").read_text())[1]
    cli_version = re.search(r'__version__ = "([^"]+)"', (WORK / "cli/src/aerotizen/__init__.py").read_text())[1]
    if (launcher_version, cli_version) != (lock["launcher_version"], lock["cli_version"]):
        sys.exit(f"Versions {launcher_version}/{cli_version} do not match the lock file.")
    applied = []
    for patch in sorted(PATCHES.glob("*.patch")):
        run(["git", "apply", "--check", patch])
        run(["git", "apply", patch])
        applied.append({"name": patch.name, "sha256": sha256_file(patch)})
    # Compare after patching so a patch cannot silently change the recovery CLI.
    verify_cli_source(lock["cli_tag_commit"])
    return {
        "repository": lock["repository"],
        "commit": head,
        "launcher_version": launcher_version,
        "cli_version": cli_version,
        "cli_unchanged_since": {"tag": lock.get("cli_tag"), "commit": lock.get("cli_tag_commit"),
                                "unchanged": True},
        "patches": applied,
    }


def verify_cli_source(reference):
    result = subprocess.run(["git", "-C", WORK, "diff", "--quiet", reference, "--", "cli/"])
    if result.returncode != 0:
        sys.exit(f"Pinned CLI verification failed (git exit {result.returncode}); no package is approved.")
    if run(["git", "ls-files", "--others", "--exclude-standard", "--", "cli/"], capture=True):
        sys.exit("Unexpected CLI source files after patching; no package is approved.")


def archive_receipt():
    """Invalidate the current approval before rebuilding; retain the old provenance."""
    if RECEIPT_PATH.exists():
        archive = CACHE / "receipts" / f"{sha256_file(RECEIPT_PATH)}.json"
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RECEIPT_PATH, archive)
        RECEIPT_PATH.unlink()


def dotnet_archive_provenance(dotnet):
    """Record a verified local SDK archive when available; external SDKs are version-checked only."""
    if dotnet.parent != DOTNET_SDK_DIR or platform.machine() not in DOTNET_SDK_ARCHIVES:
        return None
    url, expected = DOTNET_SDK_ARCHIVES[platform.machine()]
    archive = CACHE / "downloads" / url.rsplit("/", 1)[1]
    if not archive.is_file():
        return None
    if hashlib.sha512(archive.read_bytes()).hexdigest() != expected:
        sys.exit("The cached SDK archive no longer matches Microsoft's published SHA-512.")
    return {"url": url, "sha512": expected}


def build_launcher(checks, browser_tests):
    # --ignore-scripts: the only install script in the lockfile is fsevents, used by the dev watcher.
    run(["npm", "ci", "--ignore-scripts"])
    run(["npm", "run", "build"])
    github_files = sorted(
        path.relative_to(WORK / "dist/launcher").as_posix()
        for path in (WORK / "dist/launcher").rglob("*")
        if path.is_file() and b"api.github.com" in path.read_bytes()
    )
    if github_files:
        sys.exit(f"GitHub release API references remain in the launcher: {github_files}")
    if LAUNCHER_OUT.exists():
        shutil.rmtree(LAUNCHER_OUT)
    shutil.copytree(WORK / "dist/launcher", LAUNCHER_OUT, symlinks=False)
    shutil.copyfile(WORK / "LICENSE", DIST / "AeroTizen-LICENSE.txt")
    if WGT_OUT.exists():
        shutil.rmtree(WGT_OUT)
    # Upstream release packager: fixed timestamps and order, unsigned. `install` signs it later.
    run([sys.executable, "tools/build_release.py", "launcher", "--output", WGT_OUT])
    release = json.loads((WGT_OUT / "launcher-release.json").read_text())
    wgt = WGT_OUT / release["asset"]
    if sha256_file(wgt) != release["sha256"]:
        sys.exit(f"{wgt.name}: SHA-256 does not match launcher-release.json.")
    if checks:
        for script in NPM_CHECKS:
            run(["npm", "run", script])
    if browser_tests:
        run(["npx", "playwright", "install", "chromium"])
        # The upstream HTTP test server resets connections with concurrent workers.
        run(["npx", "playwright", "test", "--workers=1", "--retries=1", *BROWSER_TESTS])
    build_info = (LAUNCHER_OUT / "js/build-info.js").read_text()
    config = (LAUNCHER_OUT / "config.xml").read_text()
    return {
        "path": str(LAUNCHER_OUT.relative_to(ROOT)),
        "widget_id": re.search(r'<widget [^>]*\bid="([^"]+)"', config)[1],
        "application_id": re.search(r'<tizen:application id="([^"]+)"', config)[1],
        "version": re.search(r'<widget [^>]*\bversion="([^"]+)"', config)[1],
        "upstream_build_info": json.loads(re.search(r"var value=(\{.*?\});", build_info)[1]),
        "files_mentioning_api_github_com": github_files,
        "wgt": {
            "path": str(wgt.relative_to(ROOT)),
            "sha256": release["sha256"],
            "app_id": release["app_id"],
            "package_id": release["package_id"],
            "signed": False,
        },
        **tree_hashes(LAUNCHER_OUT),
    }


def verify_helper(manifest_path, names, sources):
    """Mirror the CLI's own checks, prove the sources, and record what was built."""
    manifest = json.loads(manifest_path.read_text())
    native = WORK / "cli/native"
    source_sha256 = hashlib.sha256(b"\0".join((native / name).read_bytes() for name in sources)).hexdigest()
    if manifest.get("source_sha256") != source_sha256:
        sys.exit(f"{manifest_path.name}: source_sha256 does not match the pinned sources.")
    if manifest.get("schema_version") != 1 or manifest.get("target_framework") != HELPER_TARGET_FRAMEWORK:
        sys.exit(f"{manifest_path.name}: unexpected schema or target framework.")
    if set(manifest["files"]) != set(names):
        sys.exit(f"{manifest_path.name}: expected exactly {names}.")
    files = {}
    for name in names:
        data = base64.b64decode(manifest["files"][name]["base64"], validate=True)
        if hashlib.sha256(data).hexdigest() != manifest["files"][name]["sha256"]:
            sys.exit(f"{manifest_path.name}: SHA-256 mismatch for {name}.")
        files[name] = {"sha256": manifest["files"][name]["sha256"], "bytes": len(data)}
    return {
        "manifest_sha256": sha256_file(manifest_path),
        "source_sha256": manifest["source_sha256"],
        "target_framework": manifest["target_framework"],
        "files": files,
    }


def build_helpers(dotnet):
    helpers = {}
    helper_dir = WORK / "cli/src/aerotizen/helpers"
    for output, (script, names, sources) in HELPERS.items():
        (helper_dir / output).unlink(missing_ok=True)
        run([sys.executable, script, "--dotnet", dotnet], env=environment(dotnet))
        helpers[output] = verify_helper(helper_dir / output, names, sources)
    unexpected = sorted({path.name for path in helper_dir.glob("*.json")} - set(HELPERS))
    if unexpected:
        sys.exit(f"Unexpected helper payloads in the working copy: {unexpected}")
    policy = run([dotnet, "run", "--project", POLICY_PROJECT, "-c", "Release", "-p:UseSharedCompilation=false"],
                 env=environment(dotnet), capture=True)
    if POLICY_PASSED not in policy.splitlines():
        sys.exit(f"Policy harness did not print {POLICY_PASSED}:\n{policy}")
    print(POLICY_PASSED)
    return helpers


def install_cli(checks, dotnet):
    """Create the non-editable CLI once; never replace an existing recovery environment."""
    if CLI_VENV.exists():
        print(f"Preserving existing CLI environment: {CLI_VENV}")
    else:
        try:
            run([sys.executable, "-m", "venv", CLI_VENV])
            run([CLI_VENV / "bin/python", "-m", "pip", "install", "--quiet", "."])
        except BaseException:
            # This environment did not exist before this invocation. An interrupted first
            # install must not leave a partial CLI that blocks the next build.
            if CLI_VENV.exists():
                shutil.rmtree(CLI_VENV)
            raise
    python = CLI_VENV / "bin/python"
    executable = CLI_VENV / "bin/aerotizen"
    package = next((CLI_VENV / "lib").glob("python3.*/site-packages/aerotizen"), None)
    if package is None:
        sys.exit(f"No installed CLI package found in {CLI_VENV}. The existing environment was preserved.")
    expected_package = tree_hashes(WORK / "cli/src/aerotizen")
    if tree_hashes(package)["files"] != expected_package["files"]:
        sys.exit(
            f"{CLI_VENV} differs from the current source build and was preserved. "
            "Use the matching pinned source or prepare a separate recovery environment; "
            "do not remove the CLI while Native Home is active."
        )
    installed = sorted(path.name for path in (package / "helpers").glob("*.json"))
    if installed != sorted(HELPERS):
        sys.exit(f"Installed CLI has helper payloads {installed}; expected {sorted(HELPERS)}.")
    for name in installed:
        built = WORK / "cli/src/aerotizen/helpers" / name
        if sha256_file(package / "helpers" / name) != sha256_file(built):
            sys.exit(f"Installed {name} differs from the built manifest.")
    # The CLI's own loader must accept both payloads. Reads package data only; no TV access.
    run([python, "-I", "-c",
         "from aerotizen import home, home_control; home.load_helper(); home_control.load_helper(); "
         "print('helper payloads accepted by the installed CLI')"])
    version = run([executable, "--version"], capture=True)
    run([executable, "--help"], capture=True)
    if checks:
        if DEV_VENV.exists():
            shutil.rmtree(DEV_VENV)
        run([sys.executable, "-m", "venv", DEV_VENV])
        run([DEV_VENV / "bin/python", "-m", "pip", "install", "--quiet", "-e", ".[dev]"], env=environment(dotnet))
        run([DEV_VENV / "bin/python", "-m", "pytest", *CLI_TESTS], env=environment(dotnet))
    freeze = run([python, "-m", "pip", "freeze", "--all"], capture=True).splitlines()
    return {
        "executable": str(executable.relative_to(ROOT)),
        "version_output": version,
        "installed_packages": freeze,
        "installed_helpers_match_built": True,
        "aerotizen_package_tree_sha256": tree_hashes(package)["tree_sha256"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--preflight", action="store_true", help="check requirements and exit")
    parser.add_argument("--fetch-dotnet", action="store_true",
                        help=f"download .NET SDK {DOTNET_SDK_VERSION} into .cache/ after SHA-512 checks, then exit")
    parser.add_argument("--dotnet", type=Path, help=f"path to a .NET SDK {DOTNET_SDK_VERSION} dotnet executable")
    parser.add_argument("--skip-checks", action="store_true", help="skip lint, format and test runs")
    parser.add_argument("--browser-tests", action="store_true",
                        help="also run the patched Playwright spec (downloads Chromium into .cache/)")
    args = parser.parse_args()

    lock = read_lock()
    if args.fetch_dotnet:
        fetch_dotnet()
        return
    dotnet = resolve_dotnet(args.dotnet)
    ready = preflight(lock, dotnet)
    if args.preflight:
        sys.exit(0 if ready else 1)
    if not ready:
        sys.exit("Preflight failed; nothing was built.")

    DIST.mkdir(exist_ok=True)
    started = datetime.now(timezone.utc)
    archive_receipt()
    sdk_archive = dotnet_archive_provenance(dotnet)
    source = prepare_source(lock)
    launcher = build_launcher(not args.skip_checks, args.browser_tests)
    helpers = build_helpers(dotnet)
    cli = install_cli(not args.skip_checks, dotnet)
    receipt = {
        "schema_version": 1,
        "built_at": started.isoformat(timespec="seconds"),
        "note": NOTE,
        "source": source,
        "toolchain": {
            "python": sys.version.split()[0],
            "node": output_of(["node", "--version"]),
            "npm": output_of(["npm", "--version"]),
            "dotnet": {"path": str(dotnet), "sdk_version": output_of([str(dotnet), "--version"]),
                       "verified_archive": sdk_archive},
            "platform": f"{platform.system()} {platform.release()} {platform.machine()}",
        },
        "checks": {
            "ran": not args.skip_checks,
            "npm": ["build (typecheck + build)", *NPM_CHECKS] if not args.skip_checks else ["build"],
            "pytest": list(CLI_TESTS) if not args.skip_checks else [],
            "policy_harness": POLICY_PASSED,
            "browser": list(BROWSER_TESTS) if args.browser_tests else [],
        },
        "launcher": launcher,
        "helpers": helpers,
        "cli": cli,
        "not_built": ["root-runtime.json (root is out of scope)", "standalone CLI binary"],
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"\nLauncher: {LAUNCHER_OUT}  (tree {launcher['tree_sha256'][:16]}…)")
    print(f"WGT:      {ROOT / launcher['wgt']['path']}  (sha256 {launcher['wgt']['sha256'][:16]}…, unsigned)")
    print(f"CLI:      {CLI_VENV / 'bin/aerotizen'}  ({cli['version_output']})")
    print(f"Receipt:  {RECEIPT_PATH}")


if __name__ == "__main__":
    main()
