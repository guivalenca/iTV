# Pinned AeroTizen build: source and build review for the stock Native Home proof

Date: 2026-11-15. Scope: an independent read of the pinned upstream source to answer build questions for phase 1 (the stock Native Home proof on the user's U8600F, Tizen 9). This is **not** a review of the separate worker's `scripts/build.py`, `docs/build.md` or `patches/`, and it does not repeat the earlier security audit. No TV, network discovery, installs, commits or GitHub writes were made. The only network access was read-only GitHub issue lookups.

**Source:** `helalaou/AeroTizen` at `8ec95131a9339df90d4dd0c2435e794ae192c19d` (tag `launcher-v3.2.0`), checked out read-only at `.cache/aerotizen-source`. `git diff cli-v3.0.1 8ec9513 -- cli` is empty, so this commit ships CLI 3.0.1 and launcher 3.2.0, as recorded in `upstream.lock.json`.

Citation shorthand: **[S]** = `https://github.com/helalaou/AeroTizen/blob/8ec95131a9339df90d4dd0c2435e794ae192c19d/`. The same paths exist under `.cache/aerotizen-source/`.

Labels used below:
- **Verified (source):** read in the pinned code or git history.
- **Reported (upstream):** from an upstream issue or PR, not tested here.
- **Untested (TV):** depends on this TV and is still unknown.

---

## Bottom line

1. **Pin `8ec9513` (launcher 3.2.0 + CLI 3.0.1), not the `cli-v3.0.1` tree.** Both include PR #184. Between them, the Native Home code (HomeWatcher service and native navigation) is the same. The 3.2.0 changes are UI work, one store-launch change and the more frequent GitHub check (which we remove anyway). Handoff step 1 says "push upstream at tag `cli-v3.0.1`", but the lock file says `8ec9513`. Follow the lock file.
2. **The smallest reliable path:**
   - Build the two Home helpers (`home-query`, `home-control`) with .NET SDK 6.0.428.
   - Install the CLI as a normal (not editable) package in a Python 3.12 venv.
   - Build the launcher with `npm ci && npm run build`, then package a `.wgt` with `python tools/build_release.py launcher`.
   - Do **not** build the root runtime or the PyInstaller binary.
3. **Only one build blocker:** there is no `dotnet` on this Mac. Node 22.22.0 and Python 3.12 are present.
4. **The biggest unknown on the TV is upstream issue #213.** On a `25_KSUE_UB` set (this TV's platform family), `home backup` fails after Developer Mode because the TV's REST metadata returns a blank `modelName`. It fails safely (no write). Find out early, before installing anything.
5. **Order change:** run `home status` and `home backup` **before `certs` and `install`**. The backup needs neither, and doing it first removes the "don't open AeroTizen before the backup" timing risk.

---

## 1. Is PR #184 (`ddfc9c5`) in the pin? Yes.

- **Verified (source):** `ddfc9c5` ("fix(launcher): skip /leave in Native Home (#184)") is an ancestor of both `cli-v3.0.1` and `8ec9513`. `git tag --contains ddfc9c5` lists `cli-v3.0.1`, `launcher-v3.0.0`, `launcher-v3.1.0` and `launcher-v3.2.0`. The launcher changelog lists it under 3.0.0 ([S]launcher/CHANGELOG.md).
- **Verified (source):** the fix survived the TypeScript migration (#216). `leaveBeforeLaunch` skips `/leave` only when the routing file `wgt-private/aerotizen-home-routing-v1.json` holds `mode: "native"` with a valid transaction and baseline hash. Otherwise it keeps the old `/leave` handshake, with a 500 ms read timeout ([S]launcher/src/platform/tizen/createNativeNavigation.ts#L12-L14, #L87-L97, #L191-L215, #L279-L290). YouTube, Samsung Home and Live TV all go through it (#L372, #L460; [S]launcher/src/platform/tizen/createAppsPlatform.ts#L209-L219).
- **Reported (upstream):** #184 was validated on a 65" Frame (Tizen 9). Its PR text says "The original cold-boot window on the reporter's UN75U8600F still needs device verification." Issue #183 was closed with no follow-up from the U8600F reporter ([#183](https://github.com/helalaou/AeroTizen/issues/183)). That reporter ran **CLI 3.0.0 + launcher 2.7.0**, before the fix.
- **Untested (TV):** whether YouTube opens within the first ~90 s after a cold boot on a U8600F. Add it to the Q18 run: cold boot, then open YouTube as soon as the launcher appears.

### Later changes that bear on the handoff

**Verified (source):** CLI changes before `cli-v3.0.1` that matter here:

| Change | What it does |
| --- | --- |
| #203 `c789c96` | `home apply --yes` now **opens the launcher itself** and waits up to 15 s for its control service before writing ([S]cli/src/aerotizen/home_control.py#L290-L321, #L346-L351). |
| #193 `fc773a8` | Watcher startup recovery for Tizen 10. Harmless on Tizen 9. |
| #181 | Recovery for Native Home automatic startup. |

Launcher changes from `cli-v3.0.1` to `8ec9513`:
- **Verified (source):** `launcher/src/service/**` and `createNativeNavigation.ts` are unchanged.
- `createAppsPlatform.ts` changes only the Samsung store launch (#251).
- Remote-key scoping in the UI was refactored (`bindLauncherKeys.ts`, `createLauncherInputScopes.ts`), which touches Back handling inside the launcher.
- Other changes: the Chromium 63 target (#269), CEC wake for HDMI devices in standby (#267, relevant to the PS4 later), and the 6-hour GitHub check plus its button (#240).

**Reported (upstream):** the closest Native Home reports on newer builds both use CLI 3.0.1 + launcher 3.1.0:
- [#263](https://github.com/helalaou/AeroTizen/issues/263): Q70D, Tizen 9. Startup, YouTube, Home and restore work.
- [#259](https://github.com/helalaou/AeroTizen/issues/259): Q60B, Tizen 6.5.

There is no 3.2.0 Native Home report yet. In #263:
- At first, apps closed after about 3 s. That cleared after restore, reinstall, re-apply and a 60 s power cut.
- Home from HDMI only worked after setting **HDMI playback → Samsung viewer**.

## 2. Does the venv CLI avoid the root-runtime requirement? Yes.

**Verified (source):**
- **The standalone builder needs root-runtime.json.** `cli/tools/build_release.py` refuses to build without `helpers/root-runtime.json` ([S]cli/tools/build_release.py#L102-L114). CI builds it with `build_root_runtime.py` ([S].github/workflows/build-release.yml#L98-L109). That script compiles four root projects ([S]cli/tools/build_root_runtime.py#L16-L21), and `RootHelper.csproj` pulls the `Tizen.NET` NuGet package ([S]cli/native/root-helper/RootHelper.csproj#L19).
- **The Python package does not need it.** Package data is a glob (`helpers/*.json`, [S]cli/pyproject.toml), so a wheel or venv install simply ships whichever helper JSONs exist.
- **Home commands never load root code.** Root code is imported only inside `cmd_root` (`from aerotizen import root_control` at [S]cli/src/aerotizen/cli.py#L634). Home commands load only `home-query.json` and `home-control.json` ([S]cli/src/aerotizen/cli.py#L521-L547). `home.py` imports just the `SUPPORTED_VERSION` constant from `root.py`, which has no payload dependency.
- **No startup network calls.** `main()` makes none ([S]cli/src/aerotizen/cli.py#L706-L829). GitHub is contacted only by `install launcher` (no path), `update launcher` and `update cli`.
- **Tests that will fail without the root runtime:** `tests/test_packaging.py`, `tests/test_release_build.py` and `tests/test_root_{control,bridge,package}.py` expect `root-runtime.json` or the release binary. **Expected noise, not a blocker.** Run a targeted subset instead (see §6).

**Practical gotcha (verified on this Mac):**
- `/usr/local/bin/python3` is python.org 3.10.11, and its OpenSSL CA file (`…/Versions/3.10/etc/openssl/cert.pem`) is **missing**. HTTPS from a 3.10 venv (the `certs` sign-in, [S]cli/src/aerotizen/certs.py#L25-L32, #L101) should fail certificate checks.
- The 3.12 framework has the file linked to certifi.
- **Use `python3.12 -m venv`.** This is also why the release binary sets `SSL_CERT_FILE` from certifi ([S]cli/tools/build_release.py#L120-L126).

## 3. Which Home helpers to build, and how to verify them

**Build exactly two:**

```sh
python cli/tools/build_home_query.py     # -> cli/src/aerotizen/helpers/home-query.json
python cli/tools/build_home_control.py   # -> cli/src/aerotizen/helpers/home-control.json
```

Do not run `build_root_runtime.py`.

**Verified (source):**
- Both target `netcoreapp3.1` with `Deterministic`, `PathMap` and `DebugType none`. Neither has a `PackageReference` ([S]cli/native/home-control/HomeControl.csproj, [S]cli/native/home-query/HomeQuery.csproj).
- CI uses SDK **6.0.428** ([S].github/workflows/ci.yml#L175-L185; [S]CONTRIBUTING.md#L17-L31).
- The scripts already set `DOTNET_CLI_TELEMETRY_OPTOUT=1` ([S]cli/tools/build_home_control.py#L18-L36).
- **Expectation, not verified here:** restoring a `netcoreapp3.1` project with the .NET 6 SDK downloads the `Microsoft.NETCore.App.Ref` 3.1 targeting pack from nuget.org once. That is the only NuGet download for these two helpers.

**What the integrity checks actually guarantee (verified, source):**
- The manifest stores base64 bytes plus a SHA-256 computed **from those same bytes at build time** ([S]cli/tools/build_home_control.py#L37-L61). The loader re-checks that hash and a 1 MiB cap ([S]cli/src/aerotizen/home.py#L39-L60). On the TV, the staged files are checked with `sha256sum -c` before `dotnet` runs ([S]cli/src/aerotizen/sdk.py#L24-L46).
- **So it detects corruption or tampering in transit, not where the bytes came from.**
- `source_sha256` is written to the manifest but **never checked at runtime** (grep: no reader in `cli/src`).
- **Provenance comes only from building it ourselves.**

**Recommended verification after building.** These are cheap and offline.

| # | Check | Type |
| --- | --- | --- |
| a | Run the host policy harness: `dotnet run --project tests/native-home/PolicyTests.csproj -c Release -p:UseSharedCompilation=false` must print `POLICY_TESTS_PASSED=114` ([S]tests/test_home_control.py#L343-L362). It compiles the same `HomeQuery.cs`, `ControlPolicy.cs`, `HomeControl.cs`, `Compatibility.cs` and `Installation.cs` against `net6.0` ([S]tests/native-home/PolicyTests.csproj). | Required |
| b | Recompute `source_sha256` yourself (same NUL-joined file order as the build scripts) and compare it with the manifest. This proves the JSON came from the pinned sources. | Required |
| c | Check each manifest has exactly its two files. `home.load_helper()` enforces this for each manifest. | Required |
| d | Record the DLL and JSON SHA-256 values in the build record. After installing the CLI, check that the **installed** package's `helpers/*.json` match them byte for byte. | Required |
| e | Cross-check against upstream's 3.0.1 release helpers, if anyone extracts them. A matching hash would prove the build is reproducible. | Optional |

With SDK 6.0.428 and deterministic settings, byte-identical output is expected, though not verified.

**Install the CLI as a normal package (`pip install .` from the working copy), not with `-e`.**
- `PAYLOAD_PATH` is `Path(__file__).parent / "helpers/…"` ([S]cli/src/aerotizen/home.py#L29; [S]cli/src/aerotizen/home_control.py#L19).
- An editable install would run whatever helper JSON and Python sit in the working copy later, including phase-2 edits. That would also change the code that `home restore` depends on.
- Keep this venv frozen for the life of the Native Home install.
- Optional: pin `websocket-client` and `cryptography` to exact hashed versions. The project only sets lower bounds ([S]cli/requirements.txt).

## 4. The assumptions under review

### 4a. "A local install doesn't open the launcher, so backup can come after install"

**Verified (source):**
- `install PATH` signs, pushes the device profile, runs `0 vd_appinstall` and reads back the app list. It never launches anything ([S]cli/src/aerotizen/cli.py#L262-L302; [S]cli/src/aerotizen/sdb.py#L412-L415).
- The launcher never writes Home or startup vconf keys. No `vconf`, `home_appid`, `startup_appid` or `auto_start` write exists in `launcher/src` outside a diagnostics privacy schema. Only the .NET `HomeControl` helper writes them.
- `validate_backup` refuses any baseline that already contains `DclHome001.Home` ([S]cli/src/aerotizen/home.py#L328-L334).

**Reported (upstream):** on some TVs, *opening* AeroTizen makes the firmware set `db/appfw/booting_appid_backup` to `DclHome001.Home`. Apply tolerates that one difference, but a fresh backup becomes impossible ([S]docs/home-pc-flow.md#L27-L39; [S]docs/home-read-only.md#L71-L76; issue #76).

**Untested (TV):** the package also registers `DclHome001.Watcher` with `on-boot="true" auto-restart="true"` ([S]launcher/config.xml#L12-L16). It is unknown whether starting the service (after any reboot) touches that key on this firmware.

**Recommendation: move the backup ahead of `certs` and `install`.**
- **Verified (source):** `home backup` needs only an SDB session and the read-only helper. It needs no certificates and no installed launcher.
- The baseline does not record install state. Apply's preflight compares only identity, model, firmware, CPU and OS ([S]cli/src/aerotizen/home_control.py#L256-L269).
- After installing, run `home backup` again. It keeps the original and reports `matches current=True`, which is a free check that nothing drifted.
- Opening the launcher for the first time then happens inside `home apply --yes` (#203), after the backup has been validated.

### 4b. Helper integrity

Covered in §3.
- **Actual requirement:** build both helpers, pass the policy harness, and match `source_sha256` and the hashes of the installed copy.
- **Optional:** the upstream cross-check.

### 4c. Preserving the `DclHome001.Home` identity

**Verified (source):** these are hard-coded on both sides and must not change, now or in phase 2:

| Where | What is hard-coded |
| --- | --- |
| CLI | `APP_ID = "DclHome001.Home"`, `PACKAGE_ID = "DclHome001"` ([S]cli/src/aerotizen/releases.py#L24-L25) |
| HomeControl helper | `Target = "DclHome001.Home"` ([S]cli/native/home-control/ControlPolicy.cs#L84) |
| Installation check | Requires **both** `DclHome001.Home` and `DclHome001.Watcher` ([S]cli/native/home-common/Installation.cs#L36-L37) |
| Eligibility | `/opt/usr/apps/DclHome001` must exist and the firmware must accept it as a boot web app ([S]cli/native/home-control/HomeControl.cs#L47) |
| Apply and the final check | Need the service's control protocol 1, `app_id`, `persistent: true` and mode `native`/`watcher`/`hold` ([S]cli/src/aerotizen/home_control.py#L272-L287, #L446-L456; [S]launcher/src/service/createHomeMode.ts) |

`npm run build:dev` changes only the name and icon ([S]tools/dev-build-badge.mjs), but use the production build for the proof.

Rules for phase 2:
- Keep `config.xml`'s `<tizen:application>` and `<tizen:service>` IDs.
- Keep the `service/` bundle and its protocol.
- Replace only the UI.

**Untested (TV) and platform behaviour:**
- **Signing key:** Tizen normally rejects an in-place update signed by a different author certificate, so keep the same `certs` profile. Do not run `certs --force` once installed.
- **Routing state:** the Native Home routing state lives in the app's private storage, and upstream says uninstalling removes it ([S]cli/src/aerotizen/cli.py#L403-L405). Always update in place. Never uninstall while Native Home is active (already in the handoff).

### 4d. Disabling the GitHub version request

**Verified (source):**
- The only request is in `createLauncherUpdates.ts`: `RELEASES = "https://api.github.com/repos/helalaou/AeroTizen/releases?per_page=100"` and the `XMLHttpRequest` in `createReleaseRequest` ([S]launcher/src/services/createLauncherUpdates.ts#L4, #L74-L99).
- It fires on startup and on every `visibilitychange` back to visible, at most once every 6 h ([S]launcher/src/app/createLauncherApp.ts#L80-L86, #L117-L120), and from the About button (`checkNow`, 1-minute throttle).

**The smallest safe patch:**
- Make `createReleaseRequest().readPage` reject immediately, and delete `RELEASES`.
- Leave the exported `LauncherUpdates` interface alone so the Home and Settings views compile.
- Background checks then stay silent, and the About button shows "failed".

What the patch must also handle:
- `tsconfig.json` has `noUnusedLocals`/`noUnusedParameters` ([S]tsconfig.json#L11-L12), and `npm run build` runs `typecheck` first. Leftover unused symbols will break the build.
- `tests/browser/launcher_updates.spec.cjs` will fail by design. Playwright isn't needed for the proof.

**Verification:**
- `grep -r api.github.com dist/launcher` must return nothing.
- The text `github.com/helalaou/AeroTizen` in About is static and makes no request.

**Not a functional blocker:** the stock proof would work without this patch. Keep it as the only patch for phase 1.

Remaining outbound hosts from the launcher source, for awareness:
- `ipapi.co` (until a manual city is set),
- `api.open-meteo.com` and `geocoding-api.open-meteo.com`,
- `*.metahub.space` (Stremio provider only).

`config.xml` allows `<access origin="*">`. Tightening that is phase-2 material.

### 4e. Avoiding a root or runtime build for the non-root proof

**Confirmed.** Nothing in `status`, `certs`, `install PATH`, `home status|backup|apply|restore` needs `root-runtime.json`, `Tizen.NET` or PyInstaller (§2). Skip all of the following:
- `build_root_runtime.py`
- `cli/tools/build_release.py` and `tools/build_release.py cli`
- `prepare_untethered_probe.py`
- every `root …` command and the `--root` flag

## 5. Launcher packaging: install a `.wgt`, not the `dist/launcher` folder

**Verified (source):**
- `npm run build` copies the **whole** `launcher/` folder except `src/` into `dist/launcher`. That includes `AGENTS.md`, `CHANGELOG.md`, `release.json` and every asset ([S]vite.config.mts, `widgetAssets`).
- `install ./dist/launcher` signs every non-dot file it walks ([S]cli/src/aerotizen/signer.py#L109-L130).
- `python tools/build_release.py launcher --output OUT` builds the upstream release file set instead: fixed timestamps and ordering, plus a SHA-256 manifest. It checks that:
  - `dist` `config.xml` equals the source `config.xml`,
  - the required `service/index.js`, `home-mode.js`, `home-store.js` and `artmode.js` files are present,
  - no files are symlinks,
  - the Preact mounts exist.

  It needs no .NET or root runtime ([S]tools/build_release.py#L41-L137).
- That is the shape upstream users actually install. `install OUT/aerotizen-launcher-3.2.0.wgt` re-signs it with the user's certificates ([S]cli/src/aerotizen/signer.py#L126-L130).

**Recommended (optional but cheap):**
- Before packaging, confirm `dist/launcher/config.xml` contains `DclHome001.Home`, `DclHome001.Watcher` and `version="3.2.0"`.
- Checks to run: `npm ci`, `npm run build` (includes typecheck), `npm test`, `npm run test:service`.
- Skip `test:browser`.
- Node 22.22.0 here meets `engines` (`^20.19.0 || >=22.12.0`, [S]package.json#L53-L55). CI uses Node 20.

## 6. Recommended order

### Build on the Mac (no TV)

1. Copy `8ec9513` into the ignored working copy. Confirm `git status` is clean, then apply the single GitHub-check patch. Record the patch hash.
2. Install .NET SDK 6.0.428 locally, user-scoped.
3. Run `build_home_query.py` and `build_home_control.py`, then checks 3a–3c from §3.
4. In a `python3.12` venv, run `pip install .` (not editable). Then:
   - `aerotizen --version` must print `3.0.1`.
   - Run `python -c "from aerotizen import home, home_control; home.load_helper(); home_control.load_helper()"`.
   - Check the installed helper hashes (3d).
   - Optional, in a separate dev venv: `pytest tests/test_home.py tests/test_home_control.py tests/test_sdk.py tests/test_sdb.py tests/test_install.py tests/test_signer.py`.
5. Run `npm ci && npm run build && npm test && npm run test:service`. Check `grep api.github.com` returns nothing. Then run `python tools/build_release.py launcher --output <out>` and record the `.wgt` SHA-256.
6. Write one build record: commit, patch hash, tool versions, helper and `.wgt` hashes.

### On the TV (needs the user's separate authorization)

Always pass `--tv IP`. Disconnect NordVPN first.

**Untested (TV):**
- `sdk.run` makes the TV open a TCP connection *back* to the Mac on a random port ([S]cli/src/aerotizen/sdk.py#L115-L154). The macOS firewall or a VPN can block this.
- Allow the venv's Python if macOS asks.

Steps:

7. Run `status`.
8. Run `home status --json`.
   - **Check `device.model` is not empty (#213).**
   - Check `home.mode` is `stock`.
9. Run `home backup`, then copy `~/.config/aerotizen/backups/` somewhere safe.
10. Run `certs`, then `chmod -R go-rwx ~/.config/aerotizen`.
11. Run `install <out>/aerotizen-launcher-3.2.0.wgt`. Do not open the launcher.
12. Run `home backup` again. Expect `matches current=True`.
13. Run `home apply` (preview), then `home apply --yes`. This opens the launcher.
14. Unplug the TV for 60 s.
15. Run the Q18 checks, plus:
    - YouTube within the first 90 s after a cold boot (#184),
    - Settings → HDMI playback = **Samsung viewer** for the PS4 (#263).
16. Run `home restore --yes`, unplug, check that stock Home is back, then run `home apply --yes` again and unplug.

## 7. Blockers and optional improvements

### Actual blockers

| Blocker | Kind | Notes |
| --- | --- | --- |
| No `dotnet` on the Mac | Build | Needs SDK 6.0.428. Node and Python are fine. |
| Default `python3` (3.10) has no CA bundle | Practical | `certs` would fail TLS. Use 3.12. |
| **Possible:** #213 blank `modelName` | TV | `validate_backup` rejects an empty `device.model` ([S]cli/src/aerotizen/home.py#L311), and `device_info` uses the SDB banner only when REST is unreachable, not when it returns blanks ([S]cli/src/aerotizen/home.py#L184-L208; [S]cli/src/aerotizen/remote.py#L22-L28). See below. |

About the #213 risk:
- **Reported (upstream):** a UK `UE43U8000FKXXU` (`25_KSUE_UB`, the same `T-KSU2EF…-0090-1300.9` firmware line) returned a blank `modelName` after the Developer Mode power cycle ([#213](https://github.com/helalaou/AeroTizen/issues/213)). The issue is open, with no fix and no comments.
- The Brazilian 75" U8600F in #183 got past backup, so this may not hit.
- It fails safely, before any write.
- If it does hit, the fix is a small CLI patch (fall back to the SDB banner model). That patch needs its own review, because `model` is part of the backup binding.

### Not blockers

- The root runtime, PyInstaller or the standalone CLI binary.
- Playwright browser tests.
- Upstream tests that expect `root-runtime.json`.
- The GitHub-check patch: a privacy fix, not a functional one.
- `ipapi.co`: set a manual city after the first open.

### Optional improvements

- Hash-pin the Python dependencies.
- Use `npm ci --ignore-scripts` (untested whether the build still works).
- Cross-check the helper hashes against upstream 3.0.1.
- Tighten `<access origin>` in phase 2.

### Other unknowns on the TV

- Native Home on launcher **3.2.0** (no upstream report yet; 3.1.0 is reported working on Tizen 9 in #263).
- The first-run "apps close after ~3 s" symptom from #263.
- Spotify, Disney+, HBO Max and Prime Video Home/Back on this model.
- Wake from standby.
- `home restore` on this firmware.
