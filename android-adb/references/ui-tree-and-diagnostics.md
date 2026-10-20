# UI Tree, Bug Reports, and Device-State Diagnostics

Reference for the topics the main adb documentation covers only thinly. Every section names its evidence class, because some of these claims come from source rather than from the guides:

- **[AOSP]** — read from AOSP source (`frameworks/testing/uiautomator`, `frameworks/base`, `system/logging`).
- **[DOC]** — developer.android.com / source.android.com page.

Verified on 2026-10 against AOSP source at the paths listed under Sources; the device-side behaviour below was not exercised against a live device, so treat it as documented rather than measured.

## `uiautomator dump` — the UI tree

**[AOSP]** `Launcher.java` registers four subcommands: `help`, `runtest`, `dump`, `events`. `DumpCommand.java` defines the dump syntax:

```
dump [--verbose] [--compressed] [file]
  [--compressed]: dumps compressed layout information.
  [file]: the location where the dumped XML should be stored
```

The default target file is `<legacy external storage>/window_dump.xml`, i.e. `/sdcard/window_dump.xml`. On success it prints `UI hierchary dumped to: <path>` (the typo is in AOSP — grep for it literally).

Canonical loop — dump, pull, parse, tap:

```bash
adb shell uiautomator dump --compressed /sdcard/ui.xml
adb pull /sdcard/ui.xml ./ui.xml
```

Parsing to coordinates (no extra tooling; `bounds` is `[x1,y1][x2,y2]`):

```python
import re, xml.etree.ElementTree as ET
root = ET.parse("ui.xml").getroot()
for n in root.iter("node"):
    text = n.get("text")
    desc = n.get("content-desc")
    if not (text or desc):
        continue
    x1, y1, x2, y2 = map(int, re.findall(r"-?\d+", n.get("bounds")))
    print(f"{(text or desc)!r:30} {n.get('class')} center=({(x1+x2)//2},{(y1+y2)//2})")
```

Then `adb shell input tap <cx> <cy>`.

Limits worth knowing before you build on it:

- `--compressed` drops layout detail; use it when you only need text/ids/bounds, drop it when you need the resource-id tree.
- The dump reflects the accessibility tree: secure windows (password fields, some system dialogs) contribute no nodes; WebView content appears only as far as accessibility exposes it.
- Compose UIs expose semantics, not view ids — unless the app sets `testTagsAsResourceId`, `resource-id` is empty and you must match on `text` / `content-desc`.
- Bounds are in the current display coordinate space; with a live `wm size` override they follow the override, not the physical panel.
- There is no timeout flag. A dump can stall while the UI never reports idle; stabilize the screen (animations off) and retry rather than adding sleeps.
- `uiautomator events` streams accessibility events (subcommand exists; its own option list was not verified here).

In-process alternative, when you already ship a test APK — `UiDevice.dumpWindowHierarchy(File)` plus `UiSelector`/`UiObject2` targeting, which removes the coordinate math entirely. **[DOC]** `androidx.test.uiautomator` API reference.

## Bug report

**[DOC]** `developer.android.com/studio/debug/bug-report`:

```bash
adb bugreport E:\Reports\MyBugReports      # explicit destination
adb bugreport                              # current directory
adb -s <serial> bugreport                  # required when several devices are attached
```

On-device copies land in `/bugreports`:

```bash
adb shell ls /bugreports/
# bugreport-foo-bar.xxx.YYYY-MM-DD-HH-MM-SS.zip
adb pull /bugreports/bugreport-...zip
```

The zip's important member is `bugreport-BUILD_ID-DATE.txt` — dumpsys output for every system service plus logs. Treat the archive as sensitive: identifiers, accounts, app state. Prefer a bounded `logcat` + `dumpsys` capture and keep `bugreport` for system-level faults; a full report on a busy device is slow and large.

## ANR

**[DOC]** An ANR fires on: input dispatch not handled within 5 s; `Service.onCreate`/`onStartCommand`/`onBind` overrunning; `startForeground()` missing within 5 s of `startForegroundService()`; a broadcast receiver overrunning (5 s with a foreground activity); `JobService` callbacks overrunning.

Evidence routes, cheapest first:

1. `adb logcat -b events -v descriptive` — `am_anr` records name the process and reason.
2. `adb logcat -b crash` — the process death and stack.
3. `adb bugreport` — the archive carries the ANR traces (the `dumpsys` text inside `bugreport-*.txt`).
4. `/data/anr/` directly only on rootable builds (`adb root` on userdebug/eng); on a user build there is no supported adb path to those files without a bug report.

Apps targeting Android 13 and below report ANRs silently; 14+ reports them to the app.

## Doze and App Standby

**[DOC]** `developer.android.com/training/monitoring-state/doze-standby` (device or emulator image API 23+):

```bash
adb shell dumpsys deviceidle force-idle        # enter Doze
adb shell dumpsys deviceidle unforce           # leave Doze
adb shell dumpsys battery reset                # reactivate

adb shell dumpsys battery unplug               # App Standby setup
adb shell am set-inactive <packageName> true   # force standby
adb shell am set-inactive <packageName> false  # simulate wake
adb shell am get-inactive <packageName>        # read back
```

Under Doze the app gets no network, wake locks are ignored, `AlarmManager` alarms (except `setAlarmClock`) are deferred, Wi-Fi scans stop, sync adapters and `JobScheduler` (hence `WorkManager`) do not run. A suite that "hangs for 20 minutes then passes" is usually sitting in a maintenance window, not flaking.

## Reset a test device (the sanctioned answer to a locked/locked-down device)

**[DOC]** `developer.android.com/tools/adb` → "Reset test devices":

```bash
adb shell cmd testharness enable
```

Android 10 (API 29)+. It factory-resets the device **and** leaves it debuggable: the RSA key that authorizes the current workstation is backed up in a persistent location, so adb keeps working after the reset without re-authorizing. It also disables the lock screen, emergency alerts, account auto-sync and automatic system updates, and pre-sets the settings that would otherwise show setup wizards.

This is the only supported way to get a device that cannot present a keyguard. It is destructive by design — scope it to disposable test devices.

## Text input beyond ASCII

`input text` cannot carry Unicode reliably (see `input-and-state.md`). Options:

- **[AOSP]** IME shell command: `adb shell ime list -s` (or `-a`) to enumerate, `adb shell ime set <pkg>/<service>` to switch, `ime enable|disable` to toggle. `source.android.com` documents `adb shell ime tracing start|stop` for Winscope. Note that `ime set` changes the *default* IME; it does not type for you.
- **[DOC]** In-process, `UiObject2.setText(...)` is the robust path and needs no extra APK on the device.

## Locked screen

- `wm dismiss-keyguard` works only for an **insecure** keyguard.
- Wake first (`input keyevent KEYCODE_WAKEUP`), then `input keyevent 82` for the AOSP slide-up.
- There is no supported adb unlock for a PIN/pattern/ biometric device. The sanctioned paths are `cmd testharness enable` (which disables the lock screen) or test devices provisioned without a lock.
- `KEYCODE_HOME` does not guarantee a wake; treating it as one is the usual cause of "all my taps do nothing".

## Verification

- `uiautomator dump` produced a file whose root element is `<hierarchy>` and which parses to at least one node carrying `text`/`content-desc`.
- A tap derived from parsed bounds changes the foreground activity (`dumpsys window | grep mCurrentFocus`) — coordinates that "work" on one screenshot are not evidence.
- `adb bugreport` archive exists, is non-trivial in size, and contains `bugreport-*.txt`.
- Doze/standby state read back with `am get-inactive` or `dumpsys deviceidle` before asserting on behaviour.
- After `testharness enable`, `adb devices` still lists the device as `device` without a new authorization prompt.

## Sources

- **[AOSP]** `frameworks/testing/uiautomator/cmds/uiautomator/src/com/android/commands/uiautomator/{Launcher,DumpCommand,EventsCommand,RunTestCommand}.java`
- **[AOSP]** `frameworks/base/services/core/java/com/android/server/pm/PackageManagerShellCommand.java` (for the `pm install` flag set referenced elsewhere)
- **[DOC]** https://developer.android.com/studio/debug/bug-report
- **[DOC]** https://developer.android.com/topic/performance/vitals/anr
- **[DOC]** https://developer.android.com/training/monitoring-device-state/doze-standby
- **[DOC]** https://developer.android.com/tools/adb ("Reset test devices")
- **[DOC]** https://source.android.com/docs/core/graphics/winscope/capture/adb (`ime tracing`)
