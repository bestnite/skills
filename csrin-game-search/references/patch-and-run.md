# Patch and Run: from clean Steam files to a running game

Tool versions move: this file was written from a maintained tutorial last revised 2026-09-03, so when a step fails, confirm the tool's current release notes and its forum thread before blaming the game files.

Scope: turning a downloaded folder of clean Steam game files into a running game on Windows. Unsteam or uc-online2 cover online play between patched copies, GBE Fork covers single-player and LAN, and the Nemirtingas Epic Emulator joins either online route when the game uses Epic Online Services (EOS). These routes cover most games, not all: some exes defeat Steamless, and online play only reaches players running the same patch.

## Choose a route

| Situation | Route |
|---|---|
| Online play with other patched players | Unsteam (Route 1) or uc-online2 (Route 3) |
| Single-player or LAN only | GBE Fork (Route 2) |
| Game ships `EOSSDK-Win64-Shipping.dll` | Add the EOS step to whichever route |
| exe is SteamDRM/SteamStub wrapped | Steamless first, then the route |
| Unreal Engine game with two exes | Steamless on the Shipping exe, loader on the launcher |

Tool sources: [Unsteam](https://cs.rin.ru/forum/viewtopic.php?f=29&t=134707), [uc-online2](https://github.com/UnionCrax-Team/uc-online2), [GBE Fork](https://github.com/Detanup01/gbe_fork), [Steamless](https://github.com/atom0s/Steamless), [Nemirtingas Epic Emulator](https://cs.rin.ru/forum/viewtopic.php?f=29&t=105551). Clean game files come from [CS.RIN.RU](https://cs.rin.ru/forum).

## Shared prerequisites

### Find the Steam AppID

Read the number after `/app/` in the store URL, because all three routes need it: `store.steampowered.com/app/3683770/` gives `3683770` (example). Searching the store's address bar or [SteamDB](https://steamdb.info) are fallbacks. It feeds Unsteam's `real_app_id`, uc-online2's `ogAppId` and GBE Fork's `steam_settings\steam_appid.txt`.

### Check 32-bit or 64-bit

Confirm the architecture before picking a DLL, because a wrong-architecture DLL fails as a crash or "Steam not running". `steam_api64.dll` means 64-bit; a bare `steam_api.dll` needs one more check. Read the exe header by hand: drag the exe into Notepad (accept "Still open" if it warns about size), find the readable line `This program cannot be run in DOS mode`, and look a short way past it for `PE` and the two characters after:

| You see | Architecture |
|---|---|
| `PE` followed by `d?` | 64-bit |
| `PE` followed by `L` | 32-bit |

Those bytes are the machine type: 64-bit (`0x8664`) renders as `d?`, 32-bit (`0x014C`) as `L`. Do not count a byte offset to find `PE`, because the signature moves between files — eyeball the DOS-stub line and read forward. The test works on DLLs too.

### Recognize an Unreal Engine game

Treat the build as Unreal Engine when the folder holds an `Engine\` directory or an exe named `-Win64-Shipping`, because UE games ship two executables and each step needs a different one:

```
<GameDir>\BobaCafeSimulator.exe                    launcher, only ~254KB
<GameDir>\BobaCafeSimulator\Binaries\Win64\
    BobaCafeSimulator-Win64-Shipping.exe           actual game, hundreds of MB
```

| Operation | Which exe | Why |
|---|---|---|
| Steamless | Shipping exe | the Steam Stub is attached to it |
| Unsteam `exe_file` | Launcher exe | the launcher starts the Shipping exe |
| Arch check | Shipping exe | the binary the DLL must match |

## Strip SteamDRM with Steamless (optional, shared)

Run this only when the exe carries a Steam Stub; Steamless skips DRM-free files safely. Open `Steamless.exe`, drag the executable in, click Unpack File.

- `This file dose not appear to be packed with steamstub!` means no Steam encryption — skip.
- Success writes `<GameName>.unpacked.exe`: rename the original to `<GameName>.exe.old`, then give the unpacked file the original name, because the game, the loader and the ini files all refer to it.
- Unreal Engine: drop in the Shipping exe, because the Stub sits on the binary the launcher starts.

A Shipping exe whose Stub survives makes the patched game exit instantly or claim Steam is not running, however correct the rest of the install is.

## Route 1: Unsteam (online)

Unsteam runs the game as Spacewar, Steam's free placeholder title (AppID 480), faking multiplayer between patched copies. The Steam client must be logged in, and you can only meet players on the same Unsteam patch, not owners of the real game.

1. Strip the Steam Stub if present, per the section above.
2. Copy `unsteam/{x64,x86}/*` (usually x64) into the game directory and run `unsteam_loader64.exe`, which writes `unsteam.ini`.
3. Fill in `unsteam.ini`:

   ```ini
   [loader]
   exe_file=Game.exe            ; required - the game's executable filename
   dll_file=unsteam64.dll

   [game]
   offline_mode=0               ; 0 = online, 1 = force offline
   player_name=YourName         ; defaults to the packager's name - change it
   real_app_id=replace_that     ; required - the game's Steam AppID
   fake_app_id=480              ; Spacewar - leave as is
   ```

   Only `exe_file` and `real_app_id` are mandatory, because nothing else supplies the target binary or the real store ID. For UE games point `exe_file` at the launcher, because it starts the game while Steamless handles the Shipping exe.
4. If `EOSSDK-Win64-Shipping.dll` exists, do the EOS section below.
5. With Steam logged in, run the game executable directly; if nothing starts, the unsteam build is likely the wrong architecture — try x64/x86, because the DLL cannot load into the opposite process. `unsteam_loader.exe` is the alternative launch path.
6. It works when Steam shows the account playing **Spacewar**, because that is the identity the patch installs.

## Route 2: GBE Fork (offline / LAN)

GBE Fork replaces the game's `steam_api(64).dll` so the game believes Steam is running. No Steam client or account is needed, but online play is impossible: only LAN or identically configured players can meet.

1. Strip the Steam Stub if present, on the Shipping exe for Unreal Engine.
2. Search the game folder for `steam_api*.dll`. One hit (generic or Unity build): replace it and put `steam_settings` beside it. Two hits (Unreal Engine game), typically:

   ```
   <GameDir>\Engine\Binaries\ThirdParty\Steamworks\Steamv157\Win64\steam_api64.dll
   <GameDir>\<GameName>\Binaries\Win64\steam_api64.dll
   ```

   Replace the **Engine directory** copy only, with `steam_settings` there, because the engine loads Steamworks from its own ThirdParty path at startup; a replaced copy under the game's binary directory is never read. Leave that one original.
3. Copy the DLL you are about to overwrite to `steam_api64.dll.old`, because the interfaces step needs the original bytes and the backup is the way back.
4. From the GBE Fork package (`emu-win-release`), copy the matching architecture over it: `regular\x64\steam_api64.dll` for 64-bit, `regular\x86\steam_api.dll` for 32-bit. The emulator DLL is roughly 7–11 MB against the original's roughly 200–400 KB (example figures), so a size gap of that order confirms the swap.
5. Create `steam_settings` next to the emulator DLL — the Engine directory for UE, the game exe's directory otherwise — and put `steam_appid.txt` inside it with nothing but the numeric AppID.
6. Run `generate_interfaces_x64.exe` (or the x86 build) against the **backed-up original** DLL, then move the `steam_interfaces.txt` it writes into `steam_settings\`. Mismatched interface versions cause crashes or missing features, which is why this step exists and why the emulator DLL is wrong input.
7. Optionally copy templates from `steam_settings.EXAMPLE\` into `steam_settings\`, dropping the `.EXAMPLE` infix: `configs.user.ini` with `local_save_path=./path/relative/to/dll` keeps saves in the game folder instead of `%appdata%`, and `account_name=Player` sets the in-game name; `configs.main.ini` takes `offline=0`; `configs.app.ini` takes `unlock_all=1`.
8. If `EOSSDK-Win64-Shipping.dll` exists, do the EOS section below.
9. Launch the game. No Steam client is involved, so a failure points at the DLL choice or the architecture.

## Route 3: uc-online2 (online)

uc-online2 spoofs the game as Spacewar (AppID 480) like Unsteam, but applies more directly: no loader, just replace the game's `steam_api(64).dll`. Steam must be running, play is limited to players on the same patch, and it adds DLC unlocking and encrypted-ticket emulation (`EmulateTicket`), which Unsteam lacks.

1. Strip the Steam Stub if present. When Steamless cannot unpack the exe (Dave the Diver is the named example), set `GetStubbedLol=true` instead: uc-online2 patches the Stub at runtime and the exe stays untouched, because nothing is rewritten on disk.
2. From [Releases](https://github.com/UnionCrax-Team/uc-online2/releases), take the latest build and copy the matching architecture DLL over the original (`steam_api64.dll` or `steam_api.dll`), renaming the original to `.old` first. UE games: replace only the DLL actually loaded, per Route 2 step 2.
3. Create `union-crax.ini` next to the game executable. Without it the AppID stays fixed at 480 and plugins never load.

   ```ini
   [Settings]
   AppId=480          ; spoofed AppID, default 480 (Spacewar) - usually leave as is
   ogAppId=3683770    ; required - the game's real AppID, for overlay and tickets
   PluginsFolder=plugins
   GetStubbedLol=false
   UnlockDLC=211,212  ; DLC AppIDs to unlock, comma-separated
   EmulateTicket=false
   ```

   `3683770` and `211,212` are examples; substitute the game's IDs. `ogAppId` is mandatory because overlay and ticket emulation derive from the real store ID.
4. If `EOSSDK-Win64-Shipping.dll` exists, do the EOS section below.
5. With Steam logged in, run the game exe directly. On an authentication failure, restart Steam and retry, because the client caches the dead session. Success looks like Route 1: Steam shows **Spacewar**.

Known issue: the Steam overlay is broken and Shift+Tab never brings it up. The author's suggestion in [issue #1](https://github.com/UnionCrax-Team/uc-online2/issues/1) — copy `steamclient.dll` and `GameOverlayRenderer.dll` from the Steam install directory into the game directory — was tested and did not work, so wait for a fix.

## EOS online play with Nemirtingas Epic Emulator

A game's original `EOSSDK-Win64-Shipping.dll` (usually a dozen-odd MB) contacts Epic's servers to verify account, ownership and DLC. Nemirtingas Epic Emulator answers those calls locally: the game gets normal return values, generated on this machine, bypassing Epic login and validation.

Apply it when the game directory contains `EOSSDK-Win64-Shipping.dll`, usually in the binary directory or a subdirectory like `binaries/win64/`. Both online routes need it, because they spoof Steam only and leave EOS talking to Epic.

1. Find **every** `EOSSDK-Win64-Shipping.dll` — some games ship several. Rename each original to a `.old` backup, then copy the Nemirtingas DLL to the original path. When unsure which copy loads, replace all, because one unreplaced copy keeps the real EOS stack alive.
2. Launch the game; the emulator writes `NemirtingasEpicEmu.json` into the game's working directory.
3. Set a username you will remember:

   ```json
   {
     "username": "MyAwesomeUsername"
   }
   ```

   That one line suffices: `epicid` and `productuserid` derive from it, so different usernames give different identities — a shared name makes two players collide as one account.
4. Optional fields:

   | Field | Default | Meaning |
   |---|---|---|
   | `username` | `DefaultName` | seeds the identity ID; some games show it as the in-game name |
   | `appid` | auto/blank | matches rooms of the same game; host and players must agree |
   | `savepath` | blank (game dir) | where saves and achievements go; `appdata` means `%appdata%` |
   | `disable_online_networking` | `false` | `true` limits connections to LAN/VPN; revert if the game crashes |
   | `unlock_dlcs` | `false` | `true` attempts to unlock all DLC |
   | `log_level` | `OFF` | `DEBUG` while troubleshooting, back to `OFF` afterwards |

5. Verify in order: the JSON was created or updated (the DLL loaded); at `log_level=DEBUG` the log shows `EOS_Connect_Login` and similar calls (the emulator took over the API); the game creates and joins rooms with no Epic login prompt.

Troubleshooting:

- **Crash or "EOS init failed"**: confirm the loaded DLL was replaced (do all copies), delete `NemirtingasEpicEmu.json` to regenerate it, set `disable_online_networking` back to `false`, read the `DEBUG` log.
- **EOS appid lookup**: the original reference site epicdata.info is dead. For matchmaking alone, host and every player can use the same value. For the real appid (DLC or achievements), use [egdata.app](https://egdata.app): open the game's page, take the ID from its `/offers/<ID>` URL, query `api.egdata.app/offers/<ID>` for the namespace, then `api.egdata.app/items?namespace=<namespace>` and read `appId` from the main entry's `releaseInfo`. Host and players must match to meet.
- **Identity collisions**: every player takes a different `username`; one person on several machines reuses one config file so the ID stays stable.
- **Conflict with another EOS patch**: keep one and delete the other, because two EOS emulators fight over the same functions. This emulator can replace FreeTP's EpicFix.

## Automation tools

- **ARMGDDN Autocracker** — built on GBE Fork; right-click a game folder and it patches the whole install. <https://github.com/KaladinDMP/ARMGDDN-Autocracker>
- **SteamAutoCracker** — wraps Steamless and Goldberg into one pass: DRM removal plus DLL replacement. <https://github.com/BigBoiCJ/SteamAutoCracker>

Check an automated result against the route's success signal, because a one-click patch still leaves the EOS step and the ini files to you.

## Rules that prevent wasted attempts

1. Patch the exe the game actually loads. For Unreal Engine that means Steamless on the Shipping exe and the launcher name in `exe_file`, because the Stub and the launch path live in different files.
2. Rename the original to a `.old` backup before overwriting anything, because every route needs it for interfaces generation or a clean revert.
3. Generate `steam_interfaces.txt` from the original DLL, never the emulator DLL, because the tool must read the real exported interface versions.
4. Confirm 32-bit versus 64-bit before copying a DLL. A wrong-architecture DLL surfaces as an instant crash or "Steam not running", because the process cannot load it — a message that points nowhere near the real cause.
5. Keep one EOS solution only. Nemirtingas, FreeTP's EpicFix and similar patches overlap, and two emulators on one DLL path produce failures that look like game bugs.
6. Expect online play only among players on the same patch, because both online routes rely on the Spacewar identity and never reach legitimate clients.
