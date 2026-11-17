# Custom UI integration

The approved implementation was integrated on 2026-11-16 from the
[implementation handoff](design/home-ui-handoff.md). The unchanged delivered patch
is `patches/0002-itv-home-ui.patch`, applied after 0001 to pinned upstream `8ec9513`.

Current status: the round 8 slower Home-return fade is installed in place and
launched successfully. The TV accepted the `tv.audio` privilege without removing
it. The user accepted round 8 on the TV on 2026-11-17 ("Ficou bom"). The TV confirmed installation of `DclHome001.Home` version
3.2.0, then reported the launcher running and visible. Independent readback confirms
the device, firmware, every Home/startup value and Native Home control mode are
unchanged. The immutable original backup still has its original SHA-256.

## Verified package

- WGT: `dist/wgt/aerotizen-launcher-3.2.0.wgt`.
- SHA-256: `14b059b6ed74e86b305cc1462855863f7c2a081d79c9fb4285e413fec07ee096`.
- Patch SHA-256: `805dd360fa3caa1d99300905585d343e8556a3e04d343a24c0a301c955bc6579`.
- Formatting, lint, types and build pass; 567 Node, 195 component, 13 packaged-service,
  317 Python, 114 native-policy and 21 local safety/CLI-routing checks pass.
- The six custom Home browser flows and three offline-update checks pass with one
  worker: all nine passed on the first attempt for this revision. The full legacy browser suite has incompatible specs;
  see the handoff for the partial diagnostic run and its limitations.
- Every WGT file matches `dist/launcher`. All packaged `service/` files match the
  tested stock package byte for byte. The only manifest addition is `tv.audio`;
  all app identities and other manifest fields match the tested stock package.
- The frozen CLI tree is unchanged (`7f4f15b900d91c69b68f57bee264b0c293ee34af7beb16ec66d2d87862c1e8d0`)
  and its files match the portable recovery wheel.

## Update and recovery

Update the existing package in place with the saved Samsung signing profile. Do
not uninstall, regenerate certificates, update firmware or reassign Native Home.
The guarded model fallback remains available for Home status and recovery.

The prior stock WGT and receipt are kept in `.cache/releases/stock-aerotizen-3.2.0/`.
The prior build tree, including unexpected duplicate-named files, was moved intact
to `.cache/build-snapshots/before-ui-20261117T002153Z/` before the clean build.
The first custom UI WGT, receipt, patch and handoff are archived in
`.cache/releases/itv-home-ui-381d8236bd00c106/`. The earlier Feltro build is archived
in `.cache/releases/itv-home-ui-d74bdce240f99b3a/` with its receipt, patch and handoff.

The refreshed private Desktop recovery ZIP includes both patches, the new receipt,
the known-working stock UI package and receipt, the unchanged CLI wheel, certificates
and complete original Home/transaction backups. Replace the private Drive copy.

## Physical acceptance still required

The user reported through the implementation thread that Settings did not open,
app opening felt frozen, returning showed an unwanted zoom, and audio had delay.
The latest delivered revision addresses those reports with Settings discovery
and an operation fallback, a 220 ms opening transition and 300 ms return fade,
stable returning focus, pre-rendered Feltro audio and visible-Home-only keepalive.
Those fixes are installed but still need confirmation on the TV.

For the requested sound A/B, hold Back on the Home for 1.5 seconds to switch
between `Sounds: iTV` and `Sounds: Samsung`. The gesture is temporary. The updated
[design](design/home-ui.md) records the Feltro choice and this exception to short
Back doing nothing on the Home. Accepting the privilege at install time does not
by itself prove that the native beep API works; verify it during the A/B.

### Latest user feedback and read-only follow-up

The user approved Feltro sounds. Settings still shows black and returns to the
Home. Key-to-movement delay and skipped movement during rapid presses remain
under investigation in the implementation thread. No new package was installed
for this follow-up.

`aerotizen --tv <TV-IP> apps --raw` returned 16 parsed apps, with zero matches
for `setting|config|menu|quick|panel` in appid or app name. Occurrences of `panel`
were only the field name `app_panel_icon_path`, not Settings candidates. The local
inspector port 9222 refused connections. Given the previous inspect timeout,
the optional console report and performance trace were skipped without restarting
the app in this read-only round. Results were sent directly to the implementation
thread at the user’s request.

### System app inventory discovered through SDK queries

The stock SDK `apps --raw` inventory was insufficient. A follow-up used the existing
`sdk.run_shell` transport as UID 901, with temporary staging cleanup confirmed.
The TV’s own help documented `app_launcher --list` and `pkgcmd --list` as read-only
list operations. These returned the system application/package inventories.
Filtering app IDs and names found 24 candidates. The main candidate is app/package
`com.samsung.tv.coba.setting`, named `Setting`; other entry-point candidates include
`org.tizen.menu` and `com.samsung.tv.quickpanel`. None was launched in this query.
This identifies real installed IDs but does not yet prove which opens the desired
Samsung Settings UI. The filtered structured report was sent to the implementation
thread and saved in `.cache/home-ui-dev/diagnostics/system-app-candidates.json`.

### Audio diagnostics attempt

The requested `aerotizen inspect launcher --port 9222` attempt timed out before
publishing a DevTools port. The local console connection was therefore refused;
`itvAudio.report()` could not be collected. No latency measurement is available
from this attempt. The inspector process exited, and the Home was relaunched
normally. A future capture needs the inspector connected **before** the user
generates key presses, because inspect restarts the page and clears its samples.

Confirm the six app tiles, wallpaper and sounds; app launch and Home return; cold
boot and standby; persistence of focus and ordering; and the Settings and Apps tiles.
The Settings app IDs and PS4 detection need device confirmation. Last-used tracking
for remote shortcut launches remains best effort, as explicitly accepted during
implementation. Sound latency, visual scale and smoothness require the actual TV.
General performance investigation remains deferred until the basic UI is working.

### Subsequent inspector collection

The final authorized inspect retry succeeded. `JSON.stringify(itvAudio.report().slice(-15))`
returned 15 samples: keyAgeMs 2–11, etaMs 48–96, baseLatencyMs 50 and outputLatencyMs 50,
all in the running state. These measure page dispatch and engine estimates, not
physical-button-to-sound latency or focus rendering. The raw report and system app
candidates were sent directly to the implementation thread and saved in
`.cache/home-ui-dev/diagnostics/`. A five-second trace was armed after a real arrow
key, but no arrow event arrived in the 30-second observation window, so no trace
was recorded. The inspector was then stopped. No package installation, removal,
Settings launch or Native Home assignment occurred in this diagnostic round.

### Latest responsiveness and reflection feedback

The user reports severe key-to-focus delay and apparent skipped tiles during rapid
presses. Responsiveness is now an acceptance requirement for finishing this UI.
The reflection is liked but should run only as an occasional first-focus accent
after roughly 2–3 minutes idle; the exact interval is still open. The user also
perceived a sound change after the diagnostic restart, which is unconfirmed. This
feedback was sent directly to the implementation thread. The later trace attempt
coincided with a failed inspector reconnection; no valid trace was collected, and
the read-only tunnel was closed. No update was installed during these diagnostics.

## Performance / Settings revision installed (rounds 4–5)

Patch SHA-256: `cb7290c4f7c58df1c7375826a1001b07c9878af5ed0bc4b283c425234870c81f`.
WGT SHA-256: `8282ff91ac64bc10fd00f6573a6cf2161c971ef6a0ef5698dbd656e872aa7f77`.
The TV confirmed in-place installation of version 3.2.0 and normal launch as
running and visible. Manifest and service files match the already accepted
audio-enabled version; the frozen CLI is unchanged. The package, receipt, patch
and handoff are archived in `.cache/releases/itv-home-ui-8282ff91ac64bc10/`.

Checks passed: formatting, lint, types, build, 567 Node, 195 component, 13 service,
317 Python and 114 native-policy tests. Browser results were 7 first-attempt passes
and 2 retry passes. Both failing first attempts had ERR_CONNECTION_RESET for local
CSS/JS in the saved Playwright network traces, so no further test rerun was used.

Settings now prioritizes the discovered `com.samsung.tv.coba.setting`, then
`org.tizen.menu`, without a black curtain. Focus uses stable DOM/composition layers
and a bitmap shadow; sheen appears only after 150 seconds idle, and rapid arrows
under 160 ms disable focus animation until 260 ms after the last arrow. Feltro is
the startup default; the Samsung A/B mode is session-only. These are installed
behaviours awaiting physical acceptance, not proof that the reported lag is fixed.
The private Desktop recovery ZIP was refreshed and its current patch/receipt, all
payload hashes and owner-only permissions were verified.

The optional inspector attempt for this revision timed out before publishing a
port. It used the unchanged CLI in-process with a one-second settling delay after
the normal stop, to avoid an immediate stop/debug-launch race; this did not resolve
the timeout. No installed CLI file was changed. No `itvPerf.report()`,
`itvPerf.presented()` or new `itvAudio.report()` measurements were collected from
this revision. The inspector process exited and normal Home launch was requested.
No user key test was requested while the inspector was unavailable.

## Bottom-anchored layout installed (round 6)

Patch SHA-256: `766e6a5e55534c30fed55460a8f29d918bad7ca73d86c5f2e9ae89f155c87c89`.
WGT SHA-256: `166d89578f7d5a59122bdd86a66e8626067b30b24d91eea18f50f1e38f968767`.
The user feedback relayed in the implementation handoff says the prior revision
removed the perceived navigation delay, synchronized Feltro and made app opening
acceptable. Its return still popped from black, and the Settings tile still failed.
The user chose to remove Settings and use the physical remote instead.

This revision anchors the grid 60 px from the bottom, uses one continuous plate,
reveals Apps below the last row with Down and hides it with Up, places the hold-OK
menu above the tile, and waits two animation frames after visibility before a
400 ms return fade and tile shrink. Native Home, service, manifest and frozen CLI
remain unchanged from the previously accepted audio-enabled package.

The TV confirmed in-place installation of version 3.2.0. Build checks passed:
567 Node, 195 components, 13 service, 317 Python and 114 native-policy tests. Browser
checks had seven first-attempt passes and two retry passes; both first failures
have ERR_CONNECTION_RESET in saved network traces. The previous package and this
package are archived locally; the refreshed Desktop recovery ZIP is verified
separately. Physical acceptance of the new layout/Apps navigation/return fade
is still pending.

The optional round 6 inspector attempt used a 15-second SDK timeout and a one-second
stop settling delay, in-process only; it timed out before returning a port. No
measurements were collected. The diagnostic exited, and normal Home launch was
requested. No retry or extra user key-capture window was started.

## Return fade timing correction installed (round 7)

Patch SHA-256: `bf52330824196100b805593e1b9fd756d223d99f6230740f85afcbe3fc6e538e`.
WGT SHA-256: `bcda9c075efd8e3b95d20c06f7d5181872c72aca8c359fa197239b2acb99c907`.
The prior UI package is preserved; this package, receipt, patch and handoff are
archived in `.cache/releases/itv-home-ui-bcda9c075efd8e3b/`.

The user reported about half a second of abrupt black followed by the ready Home,
without seeing the round 6 return animation. The timing explanation remains a
hypothesis: the TV may hide the beginning of the page animation behind its own
black transition. This revision waits 450 ms plus two animation frames before a
500 ms return fade, with the tile shrinking. A key during the wait reveals the
Home immediately. It applies to returns from apps opened through Home tiles;
remote-shortcut launches retain the existing direct-return behaviour.

Build checks passed: formatting, lint, types, 567 Node, 195 components, 13 service,
317 Python and 114 native-policy tests. All nine selected browser checks passed
on the first attempt. Manifest, service and frozen CLI are unchanged. The TV
confirmed in-place installation and normal launch; the private recovery ZIP was
refreshed and its payload hashes/current patch/current receipt/mode 0600 verified.
No inspector restart is requested for this visual-only correction. Physical
acceptance must determine whether the fade is now visible and whether black lasts
too long; no success is inferred from the Mac tests.

## Slower return fade installed (round 8)

The user confirmed that round 7 made the return fade visible, but found it too
quick. Round 8 changes only CSS: reveal duration 500→800 ms for curtain and tile
shrink, with curtain easing `cubic-bezier(0.25, 0.1, 0.25, 1)`. The 450 ms wait and
all JavaScript remain unchanged. Manifest, service and frozen CLI match round 7.

Patch SHA-256: `805dd360fa3caa1d99300905585d343e8556a3e04d343a24c0a301c955bc6579`.
WGT SHA-256: `14b059b6ed74e86b305cc1462855863f7c2a081d79c9fb4285e413fec07ee096`.
The package/receipt/patch/handoff are archived in
`.cache/releases/itv-home-ui-14b059b6ed74e86b/`, with the prior round retained.
Build checks passed: 567 Node, 195 components, 13 service, 317 Python, 114 policies;
all nine browser flows passed on the first attempt. The TV confirmed in-place
installation. The Desktop recovery ZIP has the current patch/receipt and passed
full payload hash and 0600 permission verification. No inspector was used for this
CSS-only adjustment. User judgement of the new fade speed is still pending.

### Round 8 physical acceptance

The user confirmed **“Ficou bom”** after the requested YouTube-tile launch and Home
return test. The 800 ms fade speed is approved on the TV. Keep the 450 ms wait and
current easing; no further return-timing adjustment was requested. This approval
applies to the fade test, not to unrelated functionality. No rebuild or TV change
was made when recording this feedback.
