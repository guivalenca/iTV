# Building the pinned AeroTizen launcher and CLI

`scripts/build.py` builds the pinned launcher, custom iTV Home and recovery tools on this Mac. It never connects to a TV.

It builds from the commit in `upstream.lock.json`: `helalaou/AeroTizen` at `8ec95131a9339df90d4dd0c2435e794ae192c19d`, which is launcher 3.2.0 and CLI 3.0.1. After applying patches, the script requires `cli/` to be unchanged since `cli-v3.0.1`; a difference, unexpected source file, or Git error stops the build.

## Run it

```sh
python3.12 scripts/build.py --preflight     # checks tools; works without dotnet
python3.12 scripts/build.py --fetch-dotnet  # once: .NET SDK 6.0.428 into .cache/
python3.12 scripts/build.py                 # full build with checks (about 2 minutes)
```

Options:

- `--dotnet PATH` uses a .NET SDK 6.0.428 you already have.
  - Without it, the script looks at `AEROTIZEN_DOTNET`, then `.cache/dotnet-sdk-6.0.428/dotnet`, then `dotnet` on `PATH`.
  - Any other SDK version is refused.
- `--skip-checks` skips lint, format and tests. The helper policy harness always runs.
- `--browser-tests` also runs the six custom Home flows and three offline-update checks in Playwright. It downloads Chromium into `.cache/ms-playwright` and uses one worker to avoid the upstream HTTP test server's concurrent-connection resets.

**Use Python 3.12.** Preflight refuses an interpreter older than 3.12 or one with no CA file. The CLI venv is created with the interpreter that runs the script. The `certs` step signs in over HTTPS, and this Mac's python.org 3.10 has no working CA file of its own.

### What `--fetch-dotnet` does

1. It downloads `dotnet-sdk-6.0.428-osx-arm64.tar.gz` (or the x64 archive) from `builds.dotnet.microsoft.com`.
2. It checks the archive against a SHA-512 written into the script, then extracts it into `.cache/dotnet-sdk-6.0.428/`.
   - The hash comes from Microsoft's release metadata: `https://builds.dotnet.microsoft.com/dotnet/release-metadata/6.0/releases.json`, release 6.0.36.
   - On a mismatch, the archive is deleted and nothing is extracted.

It runs no installer scripts and changes no global tools. The script also keeps NuGet, npm, pip, Playwright and dotnet state under `.cache/`.

The receipt includes the verified SDK archive URL and SHA-512 when the local downloaded archive is available. For an externally supplied SDK, it records the path and version without claiming archive verification.

## What it does

1. Clones `.cache/aerotizen-source` into `.cache/build/aerotizen` and checks out the pinned commit. The source cache is only read. The working copy is rebuilt from scratch on every run.
2. Applies `patches/*.patch` with `git apply --check`, then `git apply`, and records each patch's SHA-256.
3. Builds the launcher with upstream tools:
   - `npm ci --ignore-scripts` with the upstream lockfile. The lockfile's only install script is `fsevents`, which the dev watcher uses.
   - `npm run build`.
   - `tools/build_release.py launcher` packages the build as an unsigned `.wgt`.
   - Then the upstream checks run: `format:check`, `lint`, `test`, `test:components` and `test:service`.
4. Builds the two Home helpers with `cli/tools/build_home_query.py` and `cli/tools/build_home_control.py`, then verifies them:
   - Each manifest holds exactly its two files, and each file's SHA-256 matches.
   - `source_sha256` is recomputed from the pinned sources, the same way the upstream scripts compute it.
   - No other helper payload is present.
   - The host policy harness, `tests/native-home/PolicyTests.csproj`, must print `POLICY_TESTS_PASSED=114`.
5. Creates the CLI in `dist/aerotizen-cli` with a normal `pip install .`, not an editable install. Rebuilds preserve an existing CLI environment and verify its package files match the current source build. A mismatch stops the build without replacing the CLI. Then:
   - It checks that the installed `helpers/*.json` files match the built ones byte for byte.
   - The CLI's own `load_helper()` must accept both payloads.
   - It runs only `aerotizen --version` and `--help`.
   - A failed or interrupted first install removes only the new partial environment so the next attempt can retry. An environment that already existed is preserved.
6. Runs these pytest files in a separate dev venv: `test_home`, `test_home_control`, `test_home_probe`, `test_sdk`, `test_sdb`, `test_install` and `test_signer`. Tests that need the root runtime or the standalone binary are left out.
7. Writes `dist/build-receipt.json` only after the whole build succeeds. Before a rebuild, the previous receipt is archived under `.cache/receipts/<sha256>.json` and removed from `dist/`. If a rebuild fails, generated packages have no current approval receipt and must not be installed.

It does **not** build the root runtime, the standalone CLI binary, or anything for `root`.

## Outputs

| Path | What |
| --- | --- |
| `dist/wgt/aerotizen-launcher-3.2.0.wgt` | Unsigned launcher package, the file to install later. Also has `launcher-release.json` and `SHA256SUMS`. |
| `dist/launcher/` | The compiled launcher directory, the same content before packaging. |
| `dist/aerotizen-cli/bin/aerotizen` | The CLI, installed from source in its own venv. |
| `dist/build-receipt.json` | Source commit, patch hashes, toolchain, helper hashes, `.wgt` hash, per-file launcher hashes and installed Python packages. |
| `dist/AeroTizen-LICENSE.txt` | AeroTizen's MIT license. |

License notices:

- The launcher carries its third-party notices in `dist/launcher/licenses/` and `fonts/googlesans/OFL.txt`.
- The CLI's license is in its `dist-info`.
- AeroTizen's own license is kept outside `dist/launcher` so the package content stays the same as upstream's.

**Keep `dist/aerotizen-cli` frozen while Native Home is installed.** `home restore` runs from it. The build script preserves it on rebuilds and refuses to replace a package that differs from the current source. Keep the directory at its existing path: virtual environments contain absolute paths and are not portable backups. Retain the pinned source and build receipt so the tools can be recreated if necessary; the complete TV baseline backups and signing certificates need their own private backup off the Mac.

## The patches

`patches/0001-launcher-no-automatic-update-check.patch` disables both automatic and manual release requests. The service keeps its public interface so Home and Settings still work, but never requests release metadata or advertises cached upstream releases:

- Automatic checks are silent. The existing **Check for updates** button reports the check as unavailable using the stock failure message.
- Previously cached upstream release notices are ignored, so they cannot display an upstream update command.
- The build fails if any compiled launcher file still mentions `api.github.com`.
- App/package IDs (`DclHome001.Home`, `DclHome001.Watcher`), the Native Home service, and the rest of the UI are unchanged.

The patch also:

- adds `createLauncherUpdates.test.ts`, covering silent automatic checks, ignored cached releases, and manual checks making no request;
- updates `tests/browser/launcher_updates.spec.cjs` to cover both offline paths and suppression of the upstream update command.

`patches/0002-itv-home-ui.patch` implements the [approved Home design](design/home-ui.md): six-column app grid, Dusk wallpaper, logos, focus and navigation sounds, Move/Hide, last-used focus and PS4/Settings/Apps tiles. The [implementation handoff](design/home-ui-handoff.md) records reviews, decisions and TV-only checks. The current revision removes the Settings tile and its launch/discovery code, anchors the grid at the bottom under one plate, hides Apps below it, and updates the return fade. It retains the responsiveness fixes, Feltro and the temporary Samsung sound comparison. It preserves the background service and all CLI sources; the only manifest change is the user-requested `tv.audio` privilege. Its SHA-256 is `805dd360fa3caa1d99300905585d343e8556a3e04d343a24c0a301c955bc6579`.

Because of the patches, `js/build-info.js` reports `"dirty": true` with the upstream commit. That is accurate: the build is upstream plus the recorded patches.

## Integrated UI build verified on 2026-11-17 (UTC)

| Check | Result |
| --- | --- |
| Lint (ESLint + Stylelint) | Passed with zero warnings |
| Typecheck and build | Passed |
| `npm test` | 567/567 passed |
| `test:components` | 195/195 passed, including the custom Home and revised layout tests |
| `test:service` | 13/13 passed |
| Python tests | 317 passed |
| Helper builds | 0 warnings |
| Policy harness | `POLICY_TESTS_PASSED=114` |
| Local safety and CLI routing | 21 tests passed; the frozen CLI still matches the portable recovery wheel and previous receipt |
| Browser flows (`itv_home.spec.cjs`, `launcher_updates.spec.cjs`) | 9/9 passed on the first attempt with one worker. |
| Final artifact verification | WGT contents, app/service identities, receipt hashes, installed CLI and helper provenance match. No compiled launcher file contains the GitHub API endpoint. |

The current custom UI unsigned `.wgt` SHA-256 is `14b059b6ed74e86b305cc1462855863f7c2a081d79c9fb4285e413fec07ee096`.

The tested stock UI WGT and its receipt are preserved in `.cache/releases/stock-aerotizen-3.2.0/` and included in the private recovery ZIP for an in-place UI rollback. The CLI environment stays at its original path. See [UI integration results](ui-integration.md) for installation and physical acceptance status.

The full legacy browser suite is not green: many specs address the removed Home, header and optional widgets. The implementation thread stopped that diagnostic run partway through and documented it in the handoff. The nine browser flows above are the relevant integration checks; this is not a claim that every upstream browser spec passes.

## Not reproducible byte for byte

The receipt records what was built. It does not claim anyone can rebuild identical bytes:

- npm follows the lockfile.
- pip resolves `websocket-client` and `cryptography` to the latest matching versions at build time.
- NuGet restores the `netcoreapp3.1` reference pack.

The helpers use upstream's deterministic settings, but nobody has compared them with upstream's own release payloads.

## Dev server exception

`launcher/AGENTS.md` asks frontend work to keep a dev server running. This is a packaging task with no interactive UI work, so no dev server is started. Playwright's own config starts temporary local servers during `--browser-tests` and stops them afterwards.

## TV installation runbook

The authorized TV proof was performed on 2026-11-16. Current hardware results and
the final confirmation state are in [stock-proof.md](stock-proof.md). The sequence
below remains the reference for a first installation.

Developer Mode must be enabled with the physical remote before these commands can
work. Open **Apps** and enter `12345` with the remote's on-screen number pad. Some
models require **Apps → App Settings** instead. Turn Developer Mode on and enter
the Mac's current local IPv4 address in **Host PC IP**. Disconnect TV power for 60
seconds, reconnect, and turn it on. These instructions follow the pinned
[upstream setup guide](https://github.com/helalaou/AeroTizen/blob/8ec95131a9339df90d4dd0c2435e794ae192c19d/README.md).

Keep automatic firmware updates off and decline any update prompt. The Mac and TV
need stable local IP addresses so Developer Mode continues to allow the Mac.

Before running anything:

- Always pass `--tv <IP>`.
- Disconnect NordVPN.
- The TV opens a connection back to the Mac, so allow the venv's Python through the macOS firewall if asked.

Never run `update cli`, `update launcher`, `install launcher` with no path, `debloat`, or any `root` command.

Steps:

1. `dist/aerotizen-cli/bin/aerotizen --tv <IP> status`
2. `... home status --json`
   - Check that `device.model` is not empty. Upstream issue #213: on a `25_KSUE_UB` set, the model came back blank after Developer Mode, and backup then refuses, safely.
   - Check that `home.mode` is `stock`.
   - If the model is blank, stop before creating a baseline. On this TV it later became blank during the restore/reapply test. The separately tested [guarded wrapper](home-metadata-fallback.md) supports an existing original backup; it cannot create the first backup from missing metadata.
3. `... home backup`, then copy `~/.config/aerotizen/backups/` somewhere off the Mac. The backup needs no certificates and no installed launcher, so it goes first.
4. `... certs`, then `chmod -R go-rwx ~/.config/aerotizen`. After installing, never run `certs --force`, because the update would need the same signer.
5. `... install dist/wgt/aerotizen-launcher-3.2.0.wgt`. Do not open the launcher.
6. `... home backup` again. Expect `matches current=True`.
7. `... home apply` to preview, then `... home apply --yes`. This step opens the launcher.
8. Unplug the TV for 60 seconds, then run the agreed pass checks. Add two:
   - YouTube within 90 seconds of a cold boot (#184);
   - HDMI playback set to Samsung viewer for the PS4 (#263).
9. Run `... home restore --yes`, cold boot, and verify Samsung's home is back. Reapply Native Home and cold boot again only after restoration has been verified.

## Cleaning up

Everything generated is under `.cache/` and `dist/`, and both are git-ignored. To start over, delete `.cache/build`. To get a new SDK, delete `.cache/dotnet-sdk-6.0.428` and `.cache/downloads`.
