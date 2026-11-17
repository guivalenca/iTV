# Home UI design

Decisions for the iTV Home that replaces the existing AeroTizen interface after the Native Home proof. The initial decisions were settled in a design interview and two rounds of prototypes on 2026-11-16, with the layout and behaviour updated through round 8 on 2026-11-17 (UTC). The prototypes are on the `prototype/home-ui` branch.

The Home should look and feel like the Apple TV home, used with a single Samsung remote: arrows, OK, Home and Back. It does not depend on a mouse, keyboard, touch or phone. Everything runs on the TV.

## Layout

The Home is a tvOS-style grid with 6 columns over a wallpaper, anchored at the
bottom. The last visible row sits 60 px above the bottom edge and additional rows
grow upward. A single continuous glass plate covers all visible rows.

- **Initial app order:** Netflix, Spotify, YouTube, Disney+, HBO Max, Prime Video. User apps, later additions and the connected PS4 fill the grid in order. The PS4 can occupy row 1 if space is available.
- **Apps** is hidden on its own row below the grid, in column 1. Down from any column of the last app row raises the grid and focuses Apps; Up hides Apps again and returns to the originating tile. The continuous plate also covers this revealed row.
- **Settings has no tile.** The user opens Samsung's settings with the physical remote. Settings discovery and launch code were removed from the customization.
- The upper part of the screen is wallpaper only. Recommendations or a top shelf may use it later ([#1](https://github.com/guivalenca/iTV/issues/1)).
- PS4 and Apps have fixed places. The user can move or hide app tiles.

The six apps fill row 1 exactly, new apps flow into further rows, and the upper
wallpaper area stays free for later features. The bottom anchor, continuous plate
and hidden Apps row replace the original fixed-height first-row layout, as approved
in the round 6 design interview.

## Visuals

- **Tiles** use each brand's official logo on its own colour, shaped like tvOS app icons:

  | Tile | Background | Logo |
  | --- | --- | --- |
  | Netflix | white | as published |
  | YouTube | white | as published |
  | Spotify | black | green |
  | Disney+ | deep blue | white |
  | HBO Max | blue–violet gradient | white |
  | Prime Video | bright blue | white |

- **Apps installed later** show the TV's own icon on a frosted tile.
- **System tiles:**
  - Apps shows an icon with the word "Apps" inside the tile.
  - PS4 shows the PlayStation symbol with "PS4" inside the tile.
- **No labels.** No name appears under any tile, focused or not, so text appears only inside a tile's artwork.
- **Focus uses Lift:**
  - The focused tile scales to about 113% and gains a deeper shadow.
  - A light sheen is retained as an occasional accent, on the first movement after power-on or after 2.5 minutes without navigation. It does not repeat on each tile change.
  - Movement takes about 200 ms.
  - Rapid arrows less than 160 ms apart move focus without animation; normal animation returns 260 ms after the last arrow. Each press is still counted and sounded. Tiles retain stable DOM order and composition layers.
- **Wallpaper** is "Dusk": a purple-to-orange gradient generated in code, with fine grain so the panel shows no colour banding. It needs no image file. "Ocean" stays in reserve and can be switched on the Mac.
- **Language:** all UI text is English.
- **No other elements:** no clock, status bar, greeting or branding.
- **Entrance animation:** a short staggered rise of about 0.4 s. An OK pressed during it is acted on when it ends.

## Navigation and behaviour

- **Power-on** always opens the Home with focus on the last-used app, so one OK opens it.
  - The last-used app is the last thing opened by any route, including the remote's app buttons and the PS4. System menus and Apps never count.
  - Booting straight into the app would require a black screen first, so it is deferred to [#2](https://github.com/guivalenca/iTV/issues/2).
- **Home** inside an app returns to the Home. On the Home itself it moves focus back to the last-used app.
- **Back** works normally inside apps and returns to the Home when the app exits. A short press on the Home does nothing. During the temporary audio comparison, holding Back for 1.5 seconds switches between iTV and Samsung sounds and shows a toast; this never exits the Home.
- **Edges:** focus stops at the ends of a row and does not wrap. Reaching an edge gives a small bump animation and the bump sound. On the revealed Apps row, Left, Right and Down bump; Up returns to the app tile that revealed it.
- **Reopening an app** resumes it where it was, if the TV still holds it in memory.
- **Opening and returning:** OK grows the tile and fades the Home to black in 220 ms before launching. Returning from an app opened through the Home waits 450 ms and two animation frames after visibility, then fades in over 800 ms while the app tile shrinks over the same duration, with stable focus. The curtain uses `cubic-bezier(0.25, 0.1, 0.25, 1)` to settle gently. A key press during the return wait reveals the Home immediately. Apps opened through the remote's shortcut buttons return without this custom fade. Launch failure, a key press or a 6-second uncovered timeout restores the Home.
- **Holding OK** on an app tile opens a small menu with Move and Hide.
  - The menu opens above the tile in the free space.
  - Move: the tile wiggles, the arrows move it, OK places it and Back cancels.
  - Hide removes the tile. Showing hidden apps again is later work.
  - On PS4 or Apps, holding OK only says the tile has a fixed place.
- **New apps** installed from Samsung's store appear automatically after the user's apps, so adding an app never needs the Mac. Samsung's pre-installed apps stay hidden.
- **An app that fails to open** gives the bump plus a short toast ("Couldn't open Netflix"), and the Home stays.
- **An uninstalled app's tile disappears.** Reinstalling restores it to its previous position.
- **PS4 not connected:** when the PS4 was the last-used item and is no longer connected, focus falls back to the first tile.

## Sounds

The user selected **Feltro** in the follow-up sound lab. It replaces the original
Soft/Wood/Pebble mix: low, soft taps with very little click, and a cushioned edge bump.
Sounds are synthesised and pre-rendered in code, with no bundled audio files.

| Event | Family | Character |
| --- | --- | --- |
| Move focus | Feltro | low, soft tap |
| Bump at an edge | Feltro | cushioned low bump |
| Select (OK) | Feltro | soft confirmation tap, played on keydown |
| Back | Feltro | soft lower tap |
| Grab (hold-OK menu) | Feltro | soft lift cue |

- Sounds also play while music runs in the background, quieter than the music.
- Exact current values are in `launcher/src/itv/sounds/createItvSounds.ts` in patch 0002; the original prototype is historical reference.
- The audio context starts with the Home, buffers are prepared in advance, and an inaudible keepalive runs only while the Home is visible. Audio is suspended when leaving for another app.
- A temporary A/B mode, requested by the user, compares Feltro with `tizen.tvaudiocontrol.playSound`. Hold Back for 1.5 seconds on the Home to alternate **Sounds: iTV** and **Sounds: Samsung**. The Home always starts in Feltro; Samsung mode lasts only for that session and the old `itv.sounds.v1` preference is ignored. The package adds only the `tv.audio` privilege for this experiment; remove the temporary gesture after the user chooses.
- If the TV refuses that privilege, omit it and keep Feltro; Samsung mode then reports that native sounds are unavailable.
- Delay between key press and sound must be checked on the TV. If it is noticeable, report it before shipping a lagging sound.

## Implementation notes

**Keep from AeroTizen.** The `DclHome001.Home` and `DclHome001.Watcher` identities, the service and the Native Home integration stay as they are. Pinned launcher code that can be reused:

- **Reordering:** the long-press menu and move mode in `launcher/src/home/state/createHomeController.ts` and `launcher/src/home/components/ReorderControls/`.
- **Startup:** `launcher/src/app/startLauncherBoot.ts` renders the Home from saved local state before any TV API call, which keeps OK responsive at power-on.
- **Audio:** `launcher/src/fireplace/startFireAudio.ts` already uses Web Audio on the TV.
- **Continue Watching:** `launcher/src/platform/tizen/createSamsungContinueWatchingProvider.ts` reads Samsung's Continue Watching feed for apps that declare support ([#1](https://github.com/guivalenca/iTV/issues/1)).

**Check on the TV during implementation:**

- reliable PS4 connection detection;
- whether the Watcher sees apps opened by the remote's app buttons, which last-used depends on;
- the installed-app list and which stock apps to hide;
- the app-store tile and its hidden-row navigation;
- sound latency;
- how well tiles read from the sofa on the 50-inch screen.

**Later:**

- recommendations and top shelf ([#1](https://github.com/guivalenca/iTV/issues/1));
- booting straight into the app ([#2](https://github.com/guivalenca/iTV/issues/2));
- unhiding apps;
- the phone remote;
- the lag follow-up in [performance-followup.md](../performance-followup.md).

## Prototypes

The `prototype/home-ui` branch keeps the prototypes as reference. They are throwaway code; the real UI is rewritten inside the launcher. Logos come from Wikimedia Commons.

- `prototypes/home-ui/index.html` is the approved direction. Use the arrows, Enter (hold for the menu), Esc for Back and H for Home.
- `prototypes/home-ui/v1-variants.html` has the four layouts that were compared:
  - A: tvOS grid (chosen);
  - B: single row;
  - C: hero with brand tint;
  - D: big 3×3 tiles.
- `prototypes/home-ui/sound-lab.html` compares the sound families.

Round 6 layout reference: `.cache/home-ui-dev/layout-mock-inline.html`. It supersedes
the original prototype layout and Settings tile; the earlier prototype remains
historical reference for artwork and general styling.
