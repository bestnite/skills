# Input, Display and System State

Host-side control of the device: gestures and text, display geometry, system settings, app launches, and the `cmd <service>` surface that replaces UI clicking and dead `svc` commands.

## `input`

```
input [<source>] <command> [<arg>...]
```

`input` wraps `InputManager.injectInputEvent()`. Default source depends on the verb: `touchscreen` for `tap`/`swipe`, `keyboard` for `text`/`keyevent`. The wrong source means the event enters the wrong pipeline — "command succeeded, nothing happened".

```bash
adb shell input tap <x> <y>
adb shell input swipe <x1> <y1> <x2> <y2> [<duration_ms>]
adb shell input draganddrop <x1> <y1> <x2> <y2> [<duration_ms>]
adb shell input roll <dx> <dy>                        # rotary/trackball axes
adb shell input motionevent <DOWN|UP|MOVE|CANCEL> <x> <y>
```

- Omitted `duration_ms` is ~300 ms for `swipe` — shorter than the long-press timeout, so it can never trigger a long-press.
- `motionevent` is the only entry that emits a one-sided event (DOWN only, MOVE only). "Hold and assert" needs it.
- `draganddrop` emits DOWN → MOVE → UP, which `View.OnDragListener` consumes. A `swipe` is a different stream and never triggers drag listeners.

Long-press, verbatim recipe ("swipe in place for the long-press timeout"):

```bash
input swipe <x> <y> <x> <y> 1000
```

`tap` has no controllable duration, and `keyevent --longpress` only applies to hardware keys.

Text:

```bash
adb shell input text "<string>"     # spaces MUST be %s
adb shell input text 'hello%sworld'
```

Non-ASCII is unreliable through `input text`; the documented alternative is UiAutomator's `UiObject2.setText(...)`. This skill has no IME/ADBKeyboard path.

Key events:

```bash
adb shell input keyevent [--longpress|--doubletap] <KEYCODE> [<KEYCODE>...]
adb shell input keyevent <NUMERIC_CODE>
```

| Mnemonic | Code | Note |
|---|---|---|
| `KEYCODE_HOME` | 3 | Presses Home; does not always wake the screen |
| `KEYCODE_BACK` | 4 | Back |
| `KEYCODE_DPAD_UP/DOWN/LEFT/RIGHT/CENTER` | 19-23 | TV / focus traversal |
| `KEYCODE_VOLUME_UP/DOWN/MUTE` | 24/25/164 | |
| `KEYCODE_POWER` | 26 | Toggles screen off/on |
| `KEYCODE_TAB` | 61 | |
| `KEYCODE_ENTER` | 66 | |
| `KEYCODE_DEL` | 67 | Backspace |
| `KEYCODE_MENU` | 82 | Also dismisses the AOSP slide-up keyguard |
| `KEYCODE_APP_SWITCH` | 187 | Recents |
| `KEYCODE_WAKEUP` | 224 | Wake without unlocking |
| `KEYCODE_SLEEP` | 223 | Force sleep |

A wrong numeric code does not error — it does something else.

Sources for multi-listener or non-touch hardware:

| Source | Use |
|---|---|
| `touchscreen` | default for tap/swipe/draganddrop |
| `touchpad` | external touchpads (Chromebook, tablet keyboards) |
| `dpad` | TV/focus: `input dpad keyevent KEYCODE_DPAD_DOWN` |
| `keyboard` | default for text/keyevent |
| `mouse` | mouse buttons + scroll |
| `trackball` | trackball roll |
| `gamepad` / `joystick` | gamepad buttons / axes |
| `stylus` | pressure-aware touch (S-Pen) |

## Display: `wm`

```bash
adb shell wm size                               # current logical size
adb shell wm size 1080x1920                     # override
adb shell wm size reset                         # restore default
adb shell wm density                            # current dpi
adb shell wm density 320
adb shell wm density reset
adb shell wm dismiss-keyguard                   # insecure keyguard only
adb shell wm user-rotation [free|lock [<rotation>]]   # 0,1,2,3 = 0/90/180/270
```

No-argument form is the read-back: it is how you prove an override did not leak between runs. `wm size 411x731` + `wm density 240` runs one device across a resolution matrix without rebuilding an emulator; every override needs a paired `reset`, because the override is device-level and survives process exit. Changing size/density fires a configuration change and rebuilds the foreground activity, so only mutate it between tests.

## `settings`

```bash
adb shell settings [--user <id>] get    <namespace> <key>
adb shell settings [--user <id>] put    <namespace> <key> <value> [<tag>] [default]
adb shell settings [--user <id>] delete <namespace> <key>
adb shell settings [--user <id>] reset  <namespace> [<package>] [untrusted_defaults|untrusted_clear|trusted_defaults]
adb shell settings [--user <id>] list   <namespace>
```

`<namespace>` is `global`, `system` or `secure` only. On multi-user devices (work profile, TV profile) omitting `--user` writes to the wrong user and the foreground app sees nothing change.

Hermetic preamble:

```bash
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
```

All three live in `global`; missing one leaves UI assertions flaking on frame jitter. Gradle equivalent: `testOptions.animationsDisabled = true`.

| Namespace | Key | Purpose |
|---|---|---|
| `system` | `font_scale` | Float (`1.0`, `1.3`) for type-scale tests |
| `secure` | `accessibility_enabled` | `1` to enable; pair with `enabled_accessibility_services` |
| `secure` | `enabled_accessibility_services` | CSV `pkg/.Service` |
| `secure` | `default_input_method` | Force a known IME |
| `secure` | `show_ime_with_hard_keyboard` | `1` keeps the IME visible on emulators |
| `secure` | `long_press_timeout` | Stabilise long-press tests |
| `global` | `airplane_mode_on` | Must be paired with `am broadcast android.intent.action.AIRPLANE_MODE` |
| `global` | `policy_control` | e.g. `immersive.full=*` hides system bars |

`airplane_mode_on` alone does not take effect — the framework only re-reads it after the broadcast. `long_press_timeout` is `secure`, not `system`.

## App state reset matrix

| Command | Kills process? | Clears data/cache/prefs? | Resets runtime permissions? |
|---|---|---|---|
| `am force-stop <pkg>` | yes | **no** | no |
| `pm clear <pkg>` | yes (implicitly) | yes | yes |
| `cmd activity stop-app <pkg>` (API 28+) | yes | no | no |

"Next round starts from zero" requires `pm clear`. "Next launch is cold" only needs `force-stop`. Clear both the app and its `.test` package, or static state in the instrumentation process survives into the next case.

## Launching

```bash
# Explicit component — the reliable form for tests
adb shell am start -n com.example.app/.MainActivity

# Force-stop first, then launch, block until started
adb shell am start -S -W -n com.example.app/.MainActivity

# Deep link
adb shell am start -a android.intent.action.VIEW -d 'https://example.com'

# Typed extras
adb shell am start -n com.example.app/.MainActivity \
  --es screen "settings" --ez debug true --ei count 42

# Back to launcher (more deterministic than KEYCODE_HOME)
adb shell am start -a android.intent.action.MAIN -c android.intent.category.HOME
```

`-n pkg/.Activity` bypasses intent resolution, immune to default-handler changes. `-S` force-stops first; `-W` blocks until launch completes — the host-side replacement for `sleep`. `-d` URIs must be quoted or `&`/`?` are eaten by the local shell.

| Token | Effect |
|---|---|
| `-a action` | Intent action |
| `-d data_uri` | Data URI |
| `-t mime_type` | MIME type |
| `-c category` | Category |
| `-n component` | Explicit component `pkg/.Activity` |
| `-f flags` | Hex `setFlags()` value |
| `--es` / `-e` | String extra |
| `--ez` / `--ei` / `--el` / `--ef` / `--eu` / `--ecn` | Boolean / int / long / float / URI / ComponentName extras |
| `--eia` / `--ela` / `--efa` | Array extras |
| `--activity-clear-top` etc. | Map to `FLAG_ACTIVITY_*` |
| `-S` | Force-stop target before starting |
| `-W` | Wait for launch to complete |

Type mismatches (`--es debug true`, read as `getBooleanExtra`) do not error — the app reads the default. Prefer the named `FLAG_ACTIVITY_*` aliases over hand-computed hex.

## `cmd <service>`

```
adb shell cmd -l
adb shell dumpsys -l
```

`cmd` calls a binder service's `onShellCommand` (API 24+). Enumerate first: a wrong service name only prints usage, with exit code 0.

| Invocation | Effect |
|---|---|
| `cmd activity stop-app <pkg>` | Modern `am force-stop` |
| `cmd activity broadcast …` | Same as `am broadcast` |
| `cmd package install -r -t -g <path>` | `pm install` equivalent |
| `cmd package compile -m speed -f <pkg>` | Force AOT compilation |
| `cmd appops set <pkg> <op> allow\|deny\|ignore\|default` | Toggle an AppOp (e.g. `RUN_IN_BACKGROUND`) |
| `cmd jobscheduler run -f <pkg> <jobId>` | Run a JobService now |
| `cmd uimode night yes\|no\|auto` | Dark mode for the current user |
| `cmd locale set-app-locales <pkg> --locales en-US` | Per-app locales (Android 13+) |
| `cmd statusbar expand-notifications` / `collapse` | Shade control |
| `cmd wifi set-wifi-enabled enabled\|disabled` | Wi-Fi toggle (preferred to `svc wifi` on API 30+) |
| `cmd connectivity airplane-mode enable\|disable` | Airplane mode on modern releases |
| `cmd testharness enable` | Reset to a hermetic test-harness state (Android 10+) |

This table is the state-control core: `cmd wifi`, `cmd connectivity`, `cmd uimode`, `cmd appops`, `cmd jobscheduler` replace `svc`, UI taps and waiting for background work. `cmd testharness enable` is the shortest path back to a clean device at suite start.

`svc data`, `svc wifi`, `svc bluetooth` silently no-op on API 30+ (the CLI was demoted from a privileged helper) — verbatim: "silently no-ops on API 30+ since the svc CLI was demoted from a privileged helper to an ordinary shell command. Exit code 0, Wi-Fi still on." Use `cmd` and read back.

## Full hermetic preamble

```bash
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
adb shell pm clear com.example.app
adb shell am start -S -W -n com.example.app/.MainActivity
```

Order is fixed: `pm clear` kills processes, so putting it last would kill the instance you just launched.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `svc wifi disable` exits 0, Wi-Fi still on | `svc` demoted on API 30+ | `cmd wifi set-wifi-enabled disabled` + `cmd wifi status` |
| Second run inherits first run's state | `am force-stop` as reset | `pm clear` on app and `.test` |
| `input text "hello world"` types only `hello` | space not encoded | `%s` |
| `a&b` becomes `a`, `$(...)` expands locally | dual-shell quoting | quote twice (Platform Tools 23+); non-ASCII needs UiAutomator |
| Chinese/emoji typed as blanks | `input text` unreliable for non-ASCII | `UiObject2.setText(...)` |
| Later jobs have wrong layout, taps offset | `wm size`/`density` override leaked | `wm size reset`, `wm density reset` in teardown |
| Activity rebuilt mid-case after a size change | configuration change | only resize between tests |
| Taps ignored, screenshots black | screen asleep; `KEYCODE_HOME` does not wake | `KEYCODE_WAKEUP`, then `82` / `wm dismiss-keyguard` |
| Extras present in the intent but the app reads defaults | type specifier mismatch, `am` does not validate | use `--ez`/`--ei`/`--el`/`--ef`/`--eu`/`--ecn`/array variants |
| Flaky assertions after a tap | fixed `Thread.sleep` used as sync | block on `am start -W`, `wait-for-device`, Compose idling |
| Focus never moves on TV/ChromeOS | missing `dpad` source prefix | `input dpad keyevent KEYCODE_DPAD_DOWN` |
