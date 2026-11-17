# Installing iTV on the TV

This is the sequence we followed in November 2026 on a Samsung U8600F
(UN50U8600FGXZD, Tizen 9.0). It has three parts:

1. a one-time setup: back up Samsung's home, create signing certificates, install the launcher and apply AeroTizen Native Home;
2. updating the Home in place;
3. recovery.

The results are recorded in [stock-proof.md](stock-proof.md) and
[ui-integration.md](ui-integration.md).

Run all commands on a Mac from the repository root. Replace `<TV-IP>` with the TV's
local address and `<BACKUP-DIR>` with your backup folder. Keep the quotes. Commands
we actually ran are shown as run. Where a line is only an equivalent of what we did,
the text says so.

> **Our first proof used stock AeroTizen with only patch 0001; patch 0002 did not exist
> yet.** The repository now contains both patches, so a build installs the iTV Home
> directly. The order below is still the right one for a first installation.

> **Rules that apply throughout**
> - Keep automatic firmware updates off and decline any update prompt. No root, debloat, region change or service menu.
> - Never uninstall the launcher while Native Home is active: restore Samsung's home first.
> - Never run `update cli`, `update launcher`, `install launcher` (it downloads upstream), `debloat`, any `root` command, or `certs --force`.
> - Keep the Home backups, the signing certificates and the recovery ZIP private: never in this repository, and with a second copy off the Mac.

## 1. Prepare the TV

1. Turn off automatic firmware updates.
2. On our TV the path was **Apps → App Settings** (not the TV's general Settings). With that screen open, type `12345` on the remote's number pad to open **Developer Mode**.
3. Turn Developer Mode **On** and set **Host PC IP** to the Mac's current address, not the TV's. On the Mac: `ipconfig getifaddr en0`.
4. Unplug the TV for 60 seconds, plug it back in and let it finish booting.

Keep the Mac and the TV on the same network and disconnect any VPN on the Mac. If
macOS asks, allow Python through its firewall for local network access: the TV
connects back to the Mac. You do not need to turn the firewall off.

If the Mac's address changes later (another network, a new lease), update **Host PC
IP** on the TV and power-cycle it again.

Host PC IP is only for maintenance. The Mac is not needed for everyday use: our final
test ran with the Mac's Wi-Fi off.

## 2. Build

The build reads a local clone of AeroTizen. On a fresh clone of this repository,
create it first:

```sh
git clone https://github.com/helalaou/AeroTizen.git .cache/aerotizen-source
git -C .cache/aerotizen-source checkout --detach 8ec95131a9339df90d4dd0c2435e794ae192c19d
python3.12 scripts/build.py --fetch-dotnet
python3.12 scripts/build.py --preflight
python3.12 scripts/build.py --browser-tests
```

This produces:

- `dist/wgt/aerotizen-launcher-3.2.0.wgt`: unsigned, with every patch in `patches/` applied;
- the AeroTizen CLI in `dist/aerotizen-cli/`;
- `dist/build-receipt.json`.

[build.md](build.md) explains the checks.

**Do not move or replace `dist/aerotizen-cli` once Native Home is installed.** Its
virtual environment contains absolute paths, and it is the tool that restores
Samsung's home. The recovery ZIP holds a portable copy.

The commands below use `$CLI` as shorthand for the frozen CLI (a convenience, not part
of the original logs):

```sh
CLI=dist/aerotizen-cli/bin/aerotizen
```

## 3. Back up Samsung's home before anything else

The backup needs no certificates and no installed launcher.

```sh
$CLI --tv "<TV-IP>" status
$CLI --tv "<TV-IP>" home status --json
$CLI --tv "<TV-IP>" home backup
```

Before going on, check that:

- `home.mode` is `stock`;
- `device.model` is not empty;
- the firmware matches the device.

The CLI saves the baseline as `~/.config/aerotizen/backups/<folder>/original-home.json`
and prints the path. Keep the **whole** `backups/` folder, including `transactions/`,
not just the JSON. Never overwrite the original baseline.

If you redirect `--json` output to files, keep those raw files private.

Right after a boot, Samsung's HTTP endpoint was sometimes not ready even though the
SDK connection worked. We let the TV finish starting, opened Samsung's home and
repeated the query.

## 4. Create the signing certificates

```sh
umask 077
PYTHONUNBUFFERED=1 $CLI --tv "<TV-IP>" certs
chmod -R go-rwx "$HOME/.config/aerotizen"
```

The command opens Samsung's sign-in in the Mac's browser and receives the result on a
local listener. Signing in to the Samsung account website on its own does not issue
the profile; the sign-in must be the one this command opens.

It creates `author.p12`, `distributor.p12`, `password.txt` and `device-profile.xml`
under `~/.config/aerotizen/certs/`. Every later install is signed with these same
files: never regenerate them. We did not use generic Tizen SDK certificates; see
[no-login-certificate.md](research/no-login-certificate.md).

Our first attempts timed out while the account sign-in was being resolved. The run
that completed raised the sign-in timeout to 20 minutes **in memory only**, without
editing the frozen CLI:

```sh
dist/aerotizen-cli/bin/python -I -u - <<'PY'
import functools
import os
import sys
from aerotizen import certs, cli
os.umask(0o077)
certs.samsung_login = functools.partial(certs.samsung_login, timeout=1200)
sys.argv = ['aerotizen', '--tv', '<TV-IP>', 'certs']
cli.main()
PY
chmod -R go-rwx "$HOME/.config/aerotizen"
```

Then make the recovery ZIP (section 8) and put a copy somewhere private off the Mac
**before** applying Native Home.

## 5. Install the launcher and apply Native Home

```sh
$CLI --tv "<TV-IP>" install dist/wgt/aerotizen-launcher-3.2.0.wgt
$CLI --tv "<TV-IP>" home backup
$CLI --tv "<TV-IP>" home apply
$CLI --tv "<TV-IP>" home apply --yes
```

- **`install`** signs the local WGT with the saved profile and checks the installed version. No `--force`, no uninstall.
- **The second `home backup`** must report `matches current=True`. Do not open the launcher before this check; `home apply --yes` launches it.
- **`home apply`** without `--yes` is a preview.
- **Our first `home apply --yes` timed out** after 15 seconds waiting for the launcher's control service, before changing any Home value. `home status --json` then showed the service ready and Home still stock. Repeating the same command succeeded, with no timeout change.

The readback showed:

- main, Home and startup all pointing to `DclHome001.Home`;
- autostart set to 1;
- the control service in native mode;
- the original baseline unchanged.

Prove it physically:

- unplug the TV for 60 seconds (cold boot), and wake it from standby while YouTube is open;
- open each app and press Home in each;
- check Back inside the apps.

We confirmed YouTube opens after a cold boot but did not time it.

## 6. Prove recovery, then reapply

We restored Samsung's home once on purpose, to prove it works:

```sh
$CLI --tv "<TV-IP>" home restore
$CLI --tv "<TV-IP>" home restore --yes
$CLI --tv "<TV-IP>" home backup --json
```

The readback matched every original value. After a 60-second power cycle, Samsung's
home was back.

The reapply then hit a problem: Samsung's HTTP metadata returned an empty model name,
and the CLI refused before writing anything. The SDK identity, firmware, CPU and
Tizen version were all unchanged. The reviewed wrapper
[`scripts/aerotizen-home.py`](../scripts/aerotizen-home.py) fills an exactly-empty
model from the live SDB banner. It does so only when the banner matches the original
backup and keeps every other check; details are in
[home-metadata-fallback.md](home-metadata-fallback.md).

```sh
dist/aerotizen-cli/bin/python -I -u scripts/aerotizen-home.py --tv "<TV-IP>" home status --json
dist/aerotizen-cli/bin/python -I -u scripts/aerotizen-home.py --tv "<TV-IP>" home apply --yes --json
dist/aerotizen-cli/bin/python -I -u scripts/aerotizen-home.py --tv "<TV-IP>" home status --json
```

The reapply ended `applied_verified`. The final test ran with the Mac's Wi-Fi off:
- a cold boot opened the launcher;
- YouTube opened;
- Home returned to the launcher.

## 7. Update the Home in place

We installed the iTV Home over the stock launcher in six batches: the first UI, rounds
2+3, rounds 4+5, then rounds 6, 7 and 8. Each batch did the same things.

1. **Replace the patch** with the new one. We copied it with a hash check; a plain `cp` is equivalent:

   ```sh
   cp <new-patch> patches/0002-itv-home-ui.patch
   ```

   `build.py` applies the patches to a fresh clone of AeroTizen; there is no manual `git apply`.

2. **Build, install, open and check:**

   ```sh
   PYTHONUNBUFFERED=1 python3.12 scripts/build.py --browser-tests
   umask 077
   PYTHONUNBUFFERED=1 $CLI --tv "<TV-IP>" install dist/wgt/aerotizen-launcher-3.2.0.wgt
   PYTHONUNBUFFERED=1 $CLI --tv "<TV-IP>" launch DclHome001.Home
   dist/aerotizen-cli/bin/python -I -u scripts/aerotizen-home.py --tv "<TV-IP>" home status --json
   ```

   - The app ID and the version (3.2.0) stay the same, so the TV updates the package in place.
   - `install` takes no `--yes`.
   - **Do not** uninstall, regenerate certificates, run `home apply` again, update firmware or touch the service.

3. **Verify:**
   - The build checks the WGT files against `dist/launcher`, the patch and receipt hashes, the app identity and the manifest.
   - After installing, `launch` must report `running=True visible=True`.
   - `home status` must match the previous snapshot: same identity, firmware, Home values and native control, and an unchanged `original-home.json`.

The manifest stayed identical across batches except for one line added in rounds 2+3:
the `tv.audio` privilege, used for the sound comparison. The TV accepted it.

## 8. Recovery ZIP

```sh
python3.12 scripts/backup-recovery.py --output "$HOME/Desktop/iTV-Recovery.zip"
```

`$HOME/Desktop/iTV-Recovery.zip` is also the default output. The script writes a
private file (mode `0600`). It contains:

- the baseline and transactions;
- the signing profile;
- a portable wheel of the CLI;
- the pinned source;
- the build receipt and the patches;
- the guarded wrapper;
- the stock launcher WGT, so the UI alone can be rolled back.

We refreshed it after the certificates, after every apply, restore or reapply, and
after every UI update.

**Each time, replace the private off-Mac copy** (ours is on a private Drive). Never
put the ZIP or certificates in this repository.

To rebuild the tools on another Mac, follow the README inside the ZIP: create a Python
3.12 virtual environment and install the included wheel. We did not need this.

## 9. Go back to Samsung's home

```sh
$CLI --tv "<TV-IP>" home restore
$CLI --tv "<TV-IP>" home restore --yes
```

If the model name comes back empty, or if you are restoring from the recovery ZIP, use
the wrapper with the original backup. Extract the whole folder somewhere writable: do
not copy only the JSON, and do not work inside the ZIP.

```sh
dist/aerotizen-cli/bin/python -I scripts/aerotizen-home.py --tv "<TV-IP>" home restore --backup "<BACKUP-DIR>/original-home.json"
dist/aerotizen-cli/bin/python -I scripts/aerotizen-home.py --tv "<TV-IP>" home restore --backup "<BACKUP-DIR>/original-home.json" --yes
dist/aerotizen-cli/bin/python -I scripts/aerotizen-home.py --tv "<TV-IP>" home status --json
```

Then unplug the TV for 60 seconds and confirm Samsung's home is back. Only after that is
it safe to uninstall the launcher. We never uninstalled it.

Restoring Samsung's home needs only the SDK connection and the backup. The
certificates are needed only to sign updates.
