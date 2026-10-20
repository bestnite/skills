---
name: android-adb
description: "Use when driving Android devices over adb: pairing, UI, logs, tests."
---

# Android ADB

One operator's manual for driving an Android device from a host shell: attach (USB / emulator / wireless), inject input, flip app and system state, read logs, capture artifacts, run instrumented tests and gate CI. Everything is raw `adb` / `am` / `pm` / `cmd` / `logcat` — no wrapper CLI, no MCP layer, no shipped scripts: every command is meant to be adapted to your host and your device.

Sources: Android's official documentation and AOSP source. Every reference names the specific page or source path its claims rest on; where the documentation is silent or stale, the reference says so and points at the command that settles it.

## When to Use

- Wireless debugging: `adb pair`, `adb connect`, mDNS discovery, "paired successfully but the device never appears".
- A device won't attach: `unauthorized`, `offline`, `no permissions`, `more than one device/emulator`, stuck transport.
- Driving UI from the host: tap / swipe / long-press / text / keyevent, wake + keyguard, screen size and density, system settings, app launches.
- Seeing what happened: logcat filters, crash buffer, per-PID streams, failure-time dumps.
- Moving bytes: screenshots, screen recording, pull/push, `/data/data` extraction via `run-as`, TestStorage artifacts.
- Running instrumentation without Gradle, sharding across devices, building a CI gate that cannot go green on failure.

Don't use for: fastboot / bootloader / flashing (adb has no transport there), or for on-device test frameworks (Espresso, Compose, the UiAutomator *library*). Host-side evidence trails for those — UI tree dumps, bug reports, ANR traces, Doze/standby state — are in `references/ui-tree-and-diagnostics.md`.

## Prerequisites

- `platform-tools` on `PATH`, and **exactly one** canonical `adb`: `adb --version` must print one path, `which -a adb` must not reveal a shadowed Homebrew copy fighting Android Studio's auto-updated one.
- Device reaches state `device` in `adb devices -l`. `-l` is mandatory in scripts — it carries `transport_id` and `model`, which the bare listing does not.
- Android 11 (API 30)+ for phones/tablets and Android 13 (API 33)+ for TV/Wear if you want wireless pairing; API 17+ shows the RSA authorization dialog.

## Quick Reference

| Intent | Command | Detail |
|---|---|---|
| List transports | `adb devices -l` | `connection.md` |
| Only ready serials | `adb devices \| awk '$2=="device"{print $1}'` | `connection.md` |
| Bind one device | `adb -s SERIAL …` / `adb -t TRANSPORT_ID …` | `connection.md` |
| Wait for transport | `adb wait-for-device` | `connection.md` |
| Wait for OS ready | `until [[ "$(adb shell getprop sys.boot_completed \| tr -d '\r')" == "1" ]]; do sleep 1; done` | `connection.md` |
| Pair (Android 11+) | `adb pair HOST:PAIRING_PORT` | `connection.md` |
| Connect after pairing | `adb connect HOST:CONNECT_PORT` | `connection.md` |
| What is discoverable | `adb mdns check` / `adb mdns services` | `connection.md` |
| Recover stuck transport | `adb reconnect offline` | `server-and-architecture.md` |
| Trace transport internals | `ADB_TRACE=adb,transport,auth adb devices -l` | `server-and-architecture.md` |
| Install / reset | `adb install -r -t -g X.apk` / `adb shell pm clear PKG` | `apps.md` |
| Tap / swipe / long-press | `adb shell input tap X Y` / `input swipe X Y X Y 1000` | `input-and-state.md` |
| Type text | `adb shell input text 'hello%sworld'` | `input-and-state.md` |
| Resize display | `adb shell wm size 411x731` … `wm size reset` | `input-and-state.md` |
| Kill animations | `settings put global window_animation_scale 0` (+2 more) | `input-and-state.md` |
| Launch and wait | `adb shell am start -S -W -n PKG/.Activity` | `input-and-state.md` |
| Stream logcat | `adb logcat TAG:D *:S` | `observability.md` |
| Dump logcat once | `adb logcat -d -b all -v threadtime,year,UTC` | `observability.md` |
| Screenshot (binary-clean) | `adb exec-out screencap -p > out.png` | `capture-and-transfer.md` |
| Record (max 180 s) | `adb shell screenrecord --time-limit 180 /sdcard/run.mp4` | `capture-and-transfer.md` |
| Pull / push | `adb pull REMOTE [LOCAL]` / `adb push --sync -z brotli LOCAL REMOTE` | `capture-and-transfer.md` |
| Read app-private files | `adb exec-out run-as PKG tar cf - dir/ \| tar xf - -C ./out` | `capture-and-transfer.md` |
| Run tests directly | `adb shell am instrument -w -r -e class PKG.Class PKG.test/androidx.test.runner.AndroidJUnitRunner` | `instrumented-tests-ci.md` |
| Gate CI on results | `grep -qE '^INSTRUMENTATION_STATUS_CODE: -[12]$' out.txt` | `instrumented-tests-ci.md` |
| Dump the UI tree | `adb shell uiautomator dump --compressed /sdcard/ui.xml` | `ui-tree-and-diagnostics.md` |
| Full bug report | `adb bugreport` | `ui-tree-and-diagnostics.md` |
| Enter Doze / App Standby | `adb shell dumpsys deviceidle force-idle` / `am set-inactive PKG true` | `ui-tree-and-diagnostics.md` |
| Reset a disposable test device | `adb shell cmd testharness enable` | `ui-tree-and-diagnostics.md` |

## Hard Rules

These nine hold across every reference file; breaking one is the usual cause of a "flaky" suite.

1. **Bind every command to one verified target.** `-s SERIAL` or `-t TRANSPORT_ID`; `-d`/`-e` are safe only when exactly one USB/TCP device exists; `ANDROID_SERIAL` is overridden by an explicit `-s`. Re-check identity after reboot, reconnect, emulator restart, Wi-Fi change or server restart.
2. **`adb -t` is a transport id, never a timeout.** Use `timeout 60 adb …` (macOS: `gtimeout`, from coreutils). Exit `124` = killed at the deadline, `137` = escalated to SIGKILL.
3. **`wait-for-*` proves a transport, not a booted OS.** Always pair it with `getprop sys.boot_completed == 1` (and, for UI tests, wake + keyguard work). `adb wait-for-device-online` does not exist.
4. **`device` in `adb devices` means adbd answers — not that the system is usable.** Package manager readiness, unlock state and app-process state are three different checks.
5. **Reset between tests with `pm clear`, never `am force-stop`.** `force-stop` kills the process and leaves shared prefs, databases, caches and granted runtime permissions intact. Clear the app **and** its `.test` package.
6. **Every write gets a read-back assertion.** `cmd wifi status`, `settings get`, bare `wm size`, `adb logcat -g`, `pm path`. `svc wifi|data|bluetooth` silently no-op on API 30+, so the read-back is the only proof.
7. **Binary bytes only through `exec-out`** (or device-side file + `pull`). `adb shell … > file` allocates a PTY that rewrites `\n` as `\r\n` and corrupts PNG/MP4/tar — reliably on Windows hosts.
8. **`am instrument` always exits 0.** Neither `$?` nor the final `INSTRUMENTATION_CODE` reports pass/fail. Parse stdout: `INSTRUMENTATION_STATUS_CODE: -1` (error) and `-2` (assertion failure) are failures; `-3`/`-4` are skips.
9. **Restore what you changed.** `wm size reset`, `wm density reset`, animation scales back to `1`, `adb forward --remove`/`adb reverse --remove-all`, `adb usb` off legacy TCP mode, delete wireless pairings you no longer trust. Every cleanup line ends with `|| true` so it cannot mask the real exit code.

## Wireless Debugging

Modern flow (Android 11+, TV/Wear 13+): enable **Settings → System → Developer options → Wireless debugging**, tap **Pair device with pairing code**, then on the host:

```bash
adb pair 192.168.1.42:42999     # prompts for the 6-digit code; keeps it out of shell history
adb connect 192.168.1.42:39555  # DIFFERENT port
adb devices
# 192.168.1.42:39555  device
```

**The single biggest failure mode: the pairing port and the connect port are different objects.** The pairing port is one-shot and dies on success; the debug port is what `adb connect` needs. Both are ephemeral — turning wireless debugging off or rebooting the device changes them, so any script with a hard-coded port survives exactly zero reconnects.

`adb mdns services` is how you find the live port instead of hard-coding it:

```bash
adb mdns check
# mdns daemon version [openscreen discovery 0.0.0]   <- 35.0.2–36.x literal
# 37.x prints: mdns daemon version [adb discovery 0.0.0]
adb mdns services
# adb-XXXXXXXX-RQAZWM   _adb-tls-pairing._tcp  192.168.1.42:42999
# adb-XXXXXXXX-RQAZWM   _adb-tls-connect._tcp  192.168.1.42:39555
```

`_adb-tls-connect._tcp` entries are auto-connected by default (`ADB_MDNS_AUTO_CONNECT=adb-tls-connect`); `_adb._tcp` is the legacy `tcpip` broadcast. If auto-connect does not happen, mDNS is blocked — connect manually with the port from the device's Wireless debugging screen.

Diagnose in this order, never skipping the first two: (1) same SSID/VLAN/subnet; (2) secure/corporate Wi-Fi — verbatim from the docs: "Secure Wi-Fi networks, such as corporate Wi-Fi networks, may block p2p connections and not let you connect over Wi-Fi"; (3) `adb mdns check`; (4) port freshness (`connection refused` after a reboot or a wireless-debugging toggle); (5) link flakiness — switching networks turns wireless adb off by itself.

Do **not** pin the mDNS backend by assumption, and do not believe any single document. Verified timeline from the platform-tools release notes: **35.0.2** made Openscreen the default on all platforms; **37.0.0** made `libadbmdns` the default; **37.0.1** deleted the Openscreen backend, so `ADB_MDNS_OPENSCREEN` has no effect at all. The developer guide still describes the variable as choosing between two backends, and the AOSP man page still calls Bonjour the default — both lag the release notes. Read `adb server-status` instead: it prints `mdns_backend:` (`LIBADBMDNS` on 37.x) and `mdns_backend_forced:`, which is the only ground truth. Gate CI on "a daemon responded", never on the word `openscreen` or `bonjour`.

Legacy `adb tcpip 5555` needs a USB bootstrap, exposes an unauthenticated well-known port until reboot, and has no mDNS discovery. The docs title it "only option available on Android 10 and lower" but add a note that it "is applicable also to Android 11 (and higher), the caveat being that it also involves an initial connection over physical USB" — so it is a fallback everywhere and the only path on API 29 and below. Keep it to isolated trusted networks and prefer `adb pair` whenever the device supports it.

Security posture: anyone with network reach plus the pairing code can pair; a flat office LAN means the whole Wi-Fi is the attack surface. Turn wireless debugging off when done — the toggle kills the listening socket immediately. Never enable it on café/hotel/public Wi-Fi.

## Procedure: Attach a Device

1. `adb --version` — one path, one version; kill a shadowing copy before debugging anything else. **Done when** `which -a adb` shows no second platform-tools install.
2. `adb devices -l` — read the state word, not just presence. **Done when** every target shows `device`, no `offline` / `unauthorized` / `no permissions` / `connecting`.
3. If `unauthorized`: unlock the device and accept the RSA dialog (optionally "Always allow"). If no dialog appears, suspect a charge-only cable or port. Do not delete `~/.android/adbkey*` — that revokes every device you ever authorized.
4. If `offline`: `adb reconnect offline` first, re-plug second, `adb kill-server && adb start-server` last (it drops every other client's session too).
5. If `no permissions` on Linux: install udev rules (see `connection.md`), then `udevadm control --reload-rules && udevadm trigger` and re-plug.
6. Gate readiness: `wait-for-device` then `sys.boot_completed == 1`. **Done when** both succeed and `adb -s SERIAL shell echo ok` returns `ok`.

## Procedure: Drive the UI Deterministically

1. Wake and clear the keyguard: `input keyevent KEYCODE_WAKEUP`, then `input keyevent 82` (AOSP) or `wm dismiss-keyguard` (insecure keyguard only). **Done when** a screenshot is not black.
2. Read the geometry before tapping: `wm size`, `wm density`. Coordinates are physical-pixel based; a leftover `wm size` override from a previous run shifts every tap.
3. Make the environment hermetic: three animation scales to `0`, `pm clear` app and `.test`, `am start -S -W -n PKG/.Activity` in that order (`pm clear` kills processes, so it cannot come last). **Done when** `settings get global window_animation_scale` returns `0`.
4. Inject input with the right source: plain taps/swipes for touchscreens, `input dpad keyevent …` for TV/focus traversal, `input motionevent DOWN|UP|MOVE` when you need a half gesture. Long-press = `input swipe X Y X Y 1000` (same point, past the long-press timeout).
5. Never `sleep` to sync. Block on something real: `am start -W`, `wait-for-device`, Compose idling inside instrumentation.
6. Restore on teardown: `wm size reset`, `wm density reset`, scales back to `1`. **Done when** bare `wm size` prints `Physical size:` with no `Override size:` line.

## Procedure: Capture Evidence

1. Clear, reproduce, dump — in that order: `adb logcat -c` → run the scenario → `adb logcat -d > log.txt`. **Done when** the dump starts at the reproduction, not at device boot.
2. On failure capture three surfaces, not one: `-b main` (app), `-b crash` (tombstone/uncaught), `-b events -v descriptive` (am/wm/focus/notification actions). Add `screencap -p` and, if the failure is visual, a 180 s `screenrecord`.
3. Save the failing exit code **before** capturing evidence (`RC=$?` under `set +e`), then `exit $RC`. **Done when** the CI job's status equals the scenario's status, not the log command's.
4. Keep artifacts per device: directory name derived from the serial with `:` and `_` flattened (`artifacts/${1//[:_]/-}`), because a TCP serial otherwise explodes into nested paths.
5. Verify each artifact: `file out.png` must say `PNG image data`, `file main.db` must say `SQLite 3.x database`. **Done when** every file type-checks; a CRLF-mangled PNG still downloads fine and opens as garbage.

## Procedure: Run Tests and Gate CI

1. Install three APKs: app, test (`-t` required — every Gradle test APK is `testOnly`), and the orchestrator when used (`pm install --force-queryable` on API 30+, see `instrumented-tests-ci.md` — the flag is a `pm` flag, not an `adb install` flag). **Done when** `pm path PKG` resolves for each.
2. Prepare: animations off, `pm clear` app + `.test`, device bound with `-s`. **Done when** the preambles in `instrumented-tests-ci.md` replay idempotently.
3. Invoke `am instrument -w -r` (or Gradle `connectedDebugAndroidTest`), one shard per device with `-e numShards N -e shardIndex i`. Wrap in `timeout`. **Done when** each device produced its own log file.
4. Gate on parsed output, never on `$?`: `grep -qE '^INSTRUMENTATION_STATUS_CODE: -[12]$' out.txt`. **Done when** deliberately breaking one test turns the job red.
5. Shard-aware fan-out: install and prep serially, run tests in parallel (`xargs -P`), then parse every result file. **Done when** a partially failing shard fails the job instead of disappearing behind `wait`.

## Pitfalls

| Symptom | Root cause | Fix |
|---|---|---|
| `Successfully paired` but `adb devices` stays empty | mDNS auto-connect blocked, or the pairing port was used as the connect port | `adb mdns services` → connect with the `_adb-tls-connect._tcp` port; check p2p blocking |
| `error: more than one device/emulator` | No selector, two transports attached | `-s` / `-t`; or `adb --one-device SERIAL start-server` for a single-tenant runner |
| Command hangs forever, `-t 60` "did nothing" | `-t` is a transport id | `timeout 60 adb …` |
| Second test run fails on state from the first | `am force-stop` used as reset | `pm clear PKG` **and** `pm clear PKG.test` |
| `svc wifi disable` exits 0 but Wi-Fi is still on | `svc` silently no-ops on API 30+ | `cmd wifi set-wifi-enabled disabled`, read back with `cmd wifi status` |
| `input text "hello world"` types only `hello` | Spaces must be `%s` | `input text 'hello%sworld'`; non-ASCII needs UiAutomator `setText`, not `input text` |
| Taps land on nothing, screenshots black | Screen asleep; `KEYCODE_HOME` does not always wake | `KEYCODE_WAKEUP`, then `82` / `wm dismiss-keyguard` |
| Next CI job has wrong layout and shifted taps | `wm size` / `wm density` override leaked | pair every override with `reset` in teardown |
| `file out.png` says `data` | `screencap` without `-p` wrote raw RGBA | `screencap -p`; stream with `exec-out` |
| Recording is 3 minutes, expected 10 | `--time-limit` maxes at 180 s and truncates silently | chain 180 s segments, or use scrcpy for live mirroring |
| MP4 exists but is unplayable | host-side `kill -9` left it unfinalized | `adb shell pkill -INT screenrecord`, then `wait $REC` |
| `adb pull /data/data/PKG/...` → `Permission denied` | `0700`, owned by the app UID | `exec-out run-as PKG …` (debuggable) or `adb root` (userdebug/eng) |
| logcat piped to grep lags and misses lines | device pushes every line, host discards 99% | filter device-side: `adb logcat TAG:D *:S` |
| `adb logcat -T 100` never returns | `-T <count>` streams after the tail | `-t 100` (dump and exit) |
| CI green while tests failed | gated on `am instrument`'s exit code | grep `INSTRUMENTATION_STATUS_CODE: -[12]` from `-w -r` output |
| `clearPackageData` does nothing | passed without the orchestrator | install orchestrator, put it in the runner position, target via `-e targetInstrumentation` |

## Verification

- `adb devices -l` lists exactly the intended targets, all `device`, all bound by `-s` in later commands.
- `getprop sys.boot_completed` returns `1` on every device the script touches.
- Every state mutation has a read-back line next to it, and every teardown resets it.
- CI: 50 consecutive runs with no "leaked port forward", "previous animation scale" or "leftover wm size" flake.
- CI: a deliberately broken test fails the job (prove the gate opens, do not trust a green run).
- Artifacts type-check (`file`), and per-device directories exist for every device in the matrix.

## References

| File | Covers |
|---|---|
| `references/connection.md` | `adb devices -l`, selectors `-s/-d/-e/-t`, `wait-for-*`, state machine, RSA authorization, Linux udev, emulator races, `adb pair` / `adb connect` / mDNS / `tcpip` in depth |
| `references/server-and-architecture.md` | client/server/daemon topology, `start-server`/`kill-server`/`reconnect`, full env-var table, server log paths, `~/.android/adbkey`, dual-binary skew |
| `references/apps.md` | `adb install` flags, split APKs, `pm list/path/grant/revoke/disable/uninstall`, `pm clear` semantics, baseline profiles |
| `references/input-and-state.md` | `input` verbs and sources, keycodes, `wm size/density/keyguard/rotation`, `settings` syntax, `am start` intents and extras, `cmd <service>` table, hermetic preambles |
| `references/observability.md` | logcat buffers, priority ladder, `*:S`, formats, `-T` vs `-t`, `--pid` re-resolution, rotation/`-G`, R8 log stripping |
| `references/capture-and-transfer.md` | `screencap` / `screenrecord`, `pull`/`push` flags, path permission table, `run-as`, tar over `exec-out`, TestStorage, capture-on-failure in three layers |
| `references/instrumented-tests-ci.md` | `am instrument -w -r`, `-e` argument table, sharding, orchestrator wiring, status codes, CI bash idioms, exit-code matrix |
| `references/ui-tree-and-diagnostics.md` | `uiautomator dump` + XML parsing, bug reports, ANR evidence routes, Doze/App Standby commands, `cmd testharness enable`, IME switching, locked-screen limits |

## Coverage and Evidence

Everything above is host-side adb work. Topics that the adb documentation covers only thinly get their own reference: `references/ui-tree-and-diagnostics.md` — `uiautomator dump` and element targeting (AOSP `DumpCommand`), `adb bugreport`, ANR evidence routes, Doze/App Standby commands, `cmd testharness enable` for disposable test devices, IME switching, and the limits of locked-screen handling (no supported PIN/pattern unlock).

Evidence class is marked per claim: **[AOSP]** source, **[DOC]** developer/source.android.com. Three widely-copied claims did not survive that check:

| Claim | Verdict |
|---|---|
| `adb logcat -v json` (Android 11+) for machine-readable output | **Dropped.** AOSP logcat's format list has eight verbs plus adverbs and no `json`; the recipe circulates widely but has no basis in the implementation. Parse `-v threadtime,year,UTC` on the host instead |
| `adb install --force-queryable …` | **Corrected.** It is a `pm install` flag (AOSP `PackageManagerShellCommand`); `adb`'s own command line has no such option. Use `adb shell pm install --force-queryable -r <path>` |
| `ADB_MDNS_OPENSCREEN` as the mDNS backend knob | **Version-scoped.** Openscreen was default 35.0.2–36.x, `libadbmdns` from 37.0.0, Openscreen deleted in 37.0.1. Docs disagree with each other and with the binary; `adb server-status` is the arbiter |

Single-source claims kept but flagged: `svc wifi|data|bluetooth` silently no-op on API 30+ (always read back with `cmd wifi status`), and `uiautomator events`' own option list.

Refresh policy: the authoritative sources are developer.android.com, source.android.com, the SDK Platform Tools release notes, and AOSP source. After a platform-tools major release, the binary outranks every document: `adb help` (which variables and flags it actually implements), `adb server-status` (active USB and mDNS backends), `adb host-features`. When the docs and the binary disagree, trust the binary and record the version boundary in a table instead of asserting one side.

## Evidence Limits

Host-side facts here are documented behaviour: selectors, `wait-for` semantics, PTY corruption on binary streams, dual-shell quoting, the exit-code matrix, `pm clear` versus `force-stop`. **Device-side thresholds are sourced rather than measured across devices** — the `svc` demotion on API 30+, `screenrecord`'s 180 s cap, `uiautomator`'s output shape, wireless connection state transitions — and come from AOSP source and developer docs. Treat them as strong defaults, and re-verify on the devices and platform-tools build you actually depend on. The self-checks are all in the sections above: `adb server-status`, `settings get`, bare `wm size`, `adb logcat -g`, and `file` on every artifact.

Scope: this skill drives devices from a host shell. On-device test code (Espresso, Compose test, the UiAutomator library), app implementation, fastboot/flashing and device provisioning are out of scope.
