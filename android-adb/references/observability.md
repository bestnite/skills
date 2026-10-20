# Observability: logcat

Reading device logs for failures, smoke runs and CI repros. The rule that governs the file: **filter on the device, not with grep on the host.**

## Three primitives

| Command | Behavior |
|---|---|
| `adb logcat` | Streams until interrupted |
| `adb logcat -d` | "Dumps the log and exits." CI-friendly |
| `adb logcat -c` | "Clears the log buffer." Run before reproducing |

The CI sequence is fixed:

```bash
adb logcat -c                           # clear before the scenario
./run-scenario.sh                       # reproduce
adb logcat -d > artifacts/log.txt       # dump after
```

Dumping before clearing drags in history; not clearing at all expands the attribution window to everything the device ever logged.

## Buffers

| Buffer | Contents |
|---|---|
| `main` | default app-side buffer; does NOT include system or crash |
| `system` | framework / system_server |
| `crash` | tombstones + unhandled exceptions |
| `events` | structured/binary system events; decode with `-v descriptive` |
| `radio` | telephony |
| `kernel` | kernel |
| `all` | everything |
| `default` | implicit set: `main`, `system`, `crash` |

Looking for a crash stack in `main` alone never finds one. The implicit default omits `events`, `radio` and `kernel`.

```bash
adb logcat -b radio
adb logcat -b main -b radio -b events
adb logcat -b main,radio,events      # repeated -b and CSV are equivalent
```

`events` is the behavioural evidence: `am_*`, `wm_*`, `input_focus`, `notification_*`. Nothing human-readable without `-v descriptive`:

```bash
adb logcat -b events -v descriptive
```

That buffer answers "who started/killed this app" and "where did focus go", which `main` cannot.

## Priority ladder and filters

| Letter | Meaning |
|---|---|
| `V` | Verbose |
| `D` | Debug |
| `I` | Info |
| `W` | Warning |
| `E` | Error |
| `F` | Fatal |
| `S` | "Silent (highest priority, nothing is printed)" |

`S` is the counter-intuitive one: silent, highest priority, prints nothing. It is the pivot of the whole filter language.

```bash
adb logcat ActivityManager:I MyApp:D *:S     # only these two tags
adb logcat *:W                               # warnings and above, all tags
adb logcat *:E                               # errors and above (CI default)
```

`*:S` mutes everything, and preceding `tag:P` entries reopen that tag at level P or above — so `*:S` must come last. Quote the whole expression in scripts:

```bash
adb logcat "ActivityManager:I MyApp:D *:S"
```

Unquoted, a cwd containing a file named `S` makes the shell glob `*:S` into `S`, silently changing the filter. Host-level default filter:

```bash
ANDROID_LOG_TAGS="ActivityManager:I MyApp:D *:S"
```

Set it and bare `adb logcat` inherits it — also the first thing to remember when "nothing prints".

## Formats

| `-v` | Output |
|---|---|
| `brief` | priority, tag, PID |
| `long` | all metadata, blank-line separated |
| `process` | PID only |
| `raw` | message only |
| `tag` | priority and tag |
| `thread` | legacy: priority, PID, TID |
| `threadtime` | **default**: date, time, priority, tag, PID, TID |
| `time` | date, time, priority, tag, PID |

Use `threadtime` when thread ordering matters (it is the only one carrying TID). Modifiers stack, comma-separated or repeated: `color`, `descriptive`, `epoch`, `monotonic`, `printable`, `uid`, `usec`, `UTC`, `year`, `zone`.

Default lines carry neither year nor zone, so cross-year or cross-timezone artifacts cannot be ordered. Fix it at capture time:

```bash
adb logcat -v threadtime,year,UTC -d -b all > run.log
adb logcat -b all -v color -d
```

Do not reach for `-v json`: AOSP logcat's format list (`logcat --help` on `main`, verified 2026-10) has eight single verbs — `brief`, `long`, `process`, `raw`, `tag`, `thread`, `threadtime`, `time` — plus the adverbs, and no JSON format. The `-v json` recipe that circulates widely has no basis in that list and should not gate anything. For machine-readable output, parse `threadtime,year,UTC` against the stable schema below.

Line schema for parsers: `<priority>/<tag>(<PID>): <message>`; `threadtime` prefixes date/time/TID.

## Time and PID selection

| Flag | Behaviour |
|---|---|
| `-T '<date> <time>'` | start at a timestamp (same format as `threadtime`), e.g. `'01-01 12:00:00.000'` |
| `-T <count>` | prints the last N lines **then keeps streaming** |
| `-t <count>` | prints the last N lines **and exits** (`-t` = `-T` + auto-quit) |

Confusing the last two is how a CI job hangs forever: verbatim, "Hangs forever — -T <count> prints the last 100 lines THEN CONTINUES STREAMING."

```bash
adb logcat --pid=$(adb shell pidof -s com.example.app)
```

`pidof -s` returns a single pid (API 24+); without `-s` it returns a space-separated list that `--pid` rejects. Older devices: `adb shell ps -A | grep <pkg>`.

PIDs change when the process dies and restarts, which silently ends a `--pid` stream. Re-resolve in a loop:

```bash
while true; do
  PID=$(adb shell pidof -s com.example.app 2>/dev/null)
  [ -n "$PID" ] && adb logcat --pid="$PID"
  sleep 1
done
```

## Persistence, rotation, capacity

| Flag | Meaning |
|---|---|
| `-f <file>` | write to file instead of stdout. **`adb logcat -f` writes on the host; `adb shell logcat -f` writes on the device** |
| `-r <kbytes>` | rotate every N KB (requires `-f`) |
| `-n <count>` | keep at most N rotated files (`logfile`, `logfile.1`, …) |
| `-G <size>` | resize the selected `-b` ring (e.g. `1M`, `16M`); persists for the life of `logd` |
| `-g` | print buffer sizes and current usage, then exit |

```bash
adb logcat -b main -f /data/local/tmp/app.log -r 1024 -n 8   # host-side path per the flag table
adb shell logcat -b main -f /data/local/tmp/app.log -r 1024 -n 8  # device-side, survives USB/TCP drops
adb pull /data/local/tmp/app.log ./app.log
```

`-G` is global for that buffer and survives `logd` restarts until reboot; on a shared CI machine give the memory back with `-G 256K` when done. `-g` is the first thing to check when logs go missing.

## Structured output

There is no supported JSON logcat format (see above). Emit a stable, parseable stream instead and convert on the host:

```bash
adb logcat -d -v threadtime,year,UTC -b all > run.log

# <date> <time> <PID> <TID> <P> <tag>: <message>
awk '$5 ~ /^E|^F/ { print }' run.log
```

Keep the original `threadtime` text as the artifact — a parser can always be rerun over it, while a lossy conversion cannot be undone.

## Capture on failure

```bash
adb logcat -c
./run-scenario.sh
RC=$?
if [ "$RC" -ne 0 ]; then
  adb logcat -d -v threadtime               > artifacts/logcat.txt
  adb logcat -d -b crash    -v threadtime   > artifacts/crash.txt
  adb logcat -d -b events   -v descriptive  > artifacts/events.txt
fi
exit "$RC"
```

Store `RC` first: otherwise the log commands' exit 0 replaces the failure. Three artifacts = app log, crash, behavioural events.

## Keeping debug logs out of release builds

```pro
-assumenosideeffects class android.util.Log {
    public static *** v(...);
    public static *** d(...);
    public static *** i(...);
    public static boolean isLoggable(java.lang.String, int);
}
```

R8 treats these as no-ops and drops the call sites (and constant string concatenations), while `w`/`e`/`wtf` remain for production diagnosis. Without the rule, `Log.d("Sensitive", …)` ships in the APK. Verify with:

```bash
apkanalyzer dex packages app-release.apk | grep 'android.util.Log'
```

Never add `kotlin.jvm.internal.Intrinsics` to `-assumenosideeffects` — it deletes null checks the compiler depends on and changes runtime behaviour (especially with Compose).

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| SSH session lags, logs arrive late | device pushes every line, host grep discards 99% — "saturates the transport" | filter device-side: `adb logcat MyApp:D *:S` |
| `adb logcat -T 100` never returns | `-T <count>` streams after the tail | `-t 100` |
| `-f` file missing after `adb pull` | path was host-side (`adb logcat -f`) | use `adb shell logcat -f` for device-side, then pull |
| Filter behaves differently per directory | `*:S` glob-expanded by the shell | quote the whole expression |
| `run.log` empty or unparseable | wrong `-b` / wrong filter / stream never flushed | verify with `-t 50`, check `adb logcat -g` for buffer state |
| Stream stops at the crash | pid changed, `--pid` bound to the old one | loop re-resolving `pidof -s` |
| Random missing log windows | ring buffer overflow or wrong `-b` | `adb logcat -g`, then `-G 16M` (restore `-G 256K`) |
| Artifacts contain a previous run | buffer not cleared before the repro | `adb logcat -c` first |
| `Log.d` visible in a release build | missing R8 rule | add `-assumenosideeffects`, verify with `apkanalyzer` |
| Null checks stop working after shrinking | `Intrinsics` stripped | never list it in `-assumenosideeffects` |

## Version notes

- `-v` formats: the eight AOSP verbs + adverbs only; no `json` (verified against AOSP logcat help, 2026-10).
- `pidof -s`: API 24+.
- `-G` lifetime: until reboot, across `logd` restarts.
- Every long-running `adb logcat` gets a wall-clock budget (`timeout 600s adb logcat …`) — an unbounded stream is the main cause of CI disks filling.
