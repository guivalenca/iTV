# Stock AeroTizen proof on the TV

Physical tests on 2026-11-16 used the pinned launcher 3.2.0 and CLI 3.0.1,
Samsung UN50U8600FGXZD, Tizen 9.0.0, firmware build
`T-KSU2EFUABC-0090-REL-202607211330`. No firmware update or root operation was used.
See [build provenance](build.md) for source, package and helper checks.

## Observed results

| Check | Evidence and result |
| --- | --- |
| Installation | Exact locally built WGT installed; TV reports launcher 3.2.0. |
| Native Home | Apply succeeded; independent native readback verified main, Home and both startup targets point to `DclHome001.Home`, autostart is 1, and the persistent control service is in native mode. |
| Cold boot | User confirmed AeroTizen opens after disconnecting power for 60 seconds. |
| Standby wake | User confirmed AeroTizen opens after standby from YouTube and waking without pressing Home. |
| App launch and Home | User reported all six apps launch and Home returns to AeroTizen. |
| YouTube startup | Opened normally during the cold-boot sequence; exact latency was not measured. |
| Back/exit | User reported the checks passed; Spotify and Prime Video show exit confirmations. Netflix short Back stays inside Netflix, and long Return exits to AeroTizen. |
| Samsung comparison | After exact stock restoration, user confirmed Netflix short Back behaves the same under Samsung Home. |
| Recovery | Restore succeeded. Independent readback matched all original Home/startup values; user subsequently used the restored Samsung menu for the Netflix comparison. |
| Final reapply | Reapply succeeded after the reviewed model fallback; receipt is `applied_verified`. Independent readback confirms Native Home and the original baseline digest. User confirmed the final cold boot opens AeroTizen, YouTube opens, and Home returns to AeroTizen with the Mac disconnected from Wi-Fi. |
| PS4 / HDMI | No hardware result recorded in this session. |

The original baseline SHA-256 remains
`993877b0028216f4696980d94538b5ae5c755663ee18535b841df221ac60fbaf`.
The frozen CLI's 33 package files match the portable recovery wheel byte for byte.

## Issues encountered

The first apply attempt timed out while waiting for the control service. It failed
before changing Home. After opening AeroTizen and confirming the service was ready,
the same guarded command succeeded. No startup timeout patch was applied.

After stock restoration, Samsung HTTP metadata returned an empty model name while
the live SDK banner still returned the correct model. Original preflight rejected
reapply before writing. The [model fallback](home-metadata-fallback.md) was tested,
reviewed by Opus 5.5 High with no blocking findings, and then used successfully.
Firmware, SDK identity, architecture, OS and backup checks remain in place. There
are 21 passing local tests: 15 metadata/CLI-routing tests and 6 build guard tests.

The user reported general lag and requested investigation after customization.
The [deferred performance follow-up](performance-followup.md) records that work;
no performance cause has been established.

## Recovery and next step

The private Desktop recovery ZIP is refreshed with the complete baseline and
transaction folder, signing certificates, portable CLI wheel, pinned source,
build receipt and guarded model wrapper. Verify its manifest after refreshing and
replace the private Google Drive copy. Keep this archive private.

The final physical check passed with the Mac disconnected from Wi-Fi. This completes
the core Native Home proof and demonstrates TV-only operation. Exact YouTube launch
latency and PS4/HDMI behavior remain unmeasured, as noted above. The project can move
to the custom UI while preserving app/package IDs and the working Native Home service.
Recommendations and performance work remain later tasks.
