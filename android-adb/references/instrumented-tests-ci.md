# Instrumented Tests and CI Scripting

Running `am instrument` without Gradle, sharding across devices, orchestrator isolation, and the bash idioms that keep a CI job from reporting green on failure.

## Invocation shape

```bash
adb shell am instrument -w -r \
  [-e <key> <value>] ... \
  <pkg>/<runner>
```

- `-w` — "Wait for instrumentation to finish before returning. **Required for test runners.**" Without it the shell returns immediately and `$?` means nothing.
- `-r` — "Print raw results (otherwise decode `report_key_streamresult`)." Only parseable together with `-w`.
- `androidx.test.runner.AndroidJUnitRunner` — the AGP default for `androidTest`.
- `androidx.test.orchestrator.AndroidTestOrchestrator` — wrapper that runs each test in its own instrumentation invocation.

```bash
adb shell am instrument -w -r \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner
```

## `-e` arguments

| Key | Value | Meaning |
|---|---|---|
| `package` | `<java_package>` | "Any test class using this package executes." Takes precedence over `class`; CSV allowed |
| `class` | `<fqcn>` | only that class |
| `class` | `<fqcn>#<method>` | only that method — separator is `#`, not `:` or `.` |
| `class` | `<fqcn1>,<fqcn2>#m,…` | CSV combination |
| `size` | `small` / `medium` / `large` | by `@SmallTest` / `@MediumTest` / `@LargeTest` |
| `annotation` / `notAnnotation` | `<fqcn>` | include / exclude by annotation |
| `numShards` | `<N>` | total shards |
| `shardIndex` | `<i>` | this shard, 0-based, `0 ≤ i < N` |
| `debug` | `true` | waits for a debugger before each test |
| `log` | `true` | "Loads and logs all specified tests but doesn't run them." The only dry-run for filter combinations |
| `listener` | `<fqcn>` | register a `RunListener` (CSV) |
| `filter` / `runnerBuilder` | `<fqcn>` | custom JUnit `Filter` / `RunnerBuilder` |
| `disableAnalytics` | `true` | opt out of runner analytics |
| `clearPackageData` | `true` | **orchestrator only** — `pm clear` between tests |
| `targetInstrumentation` | `<pkg>/<runner>` | **orchestrator only** — the wrapped runner |
| `coverage` / `coverageFile` | `true` / `<path>` | JaCoCo collection and device-side output path |

```bash
# one class
adb shell am instrument -w -r -e class com.example.app.LoginTests \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner

# one method
adb shell am instrument -w -r -e class com.example.app.LoginTests#login_succeeds \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner

# @LargeTest only
adb shell am instrument -w -r -e size large \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner
```

## Sharding

```bash
# shard 0 of 4 — one device per shard
adb shell am instrument -w -r -e numShards 4 -e shardIndex 0 \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner
```

```bash
adb -s emulator-5554 shell am instrument -w -r -e numShards 2 -e shardIndex 0 \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner &
adb -s emulator-5556 shell am instrument -w -r -e numShards 2 -e shardIndex 1 \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner &
wait
```

Shards must run on **different** devices — two shards on one `-s` serialize behind each other. Bucketing is by test-name hash, so adding or removing tests reshuffles shards; "that shard used to be slow" is not a stable fact.

## Orchestrator

```bash
adb shell am instrument -w -r \
  -e clearPackageData true \
  -e targetInstrumentation com.example.app.test/androidx.test.runner.AndroidJUnitRunner \
  androidx.test.orchestrator/.AndroidTestOrchestrator
```

The orchestrator occupies the runner position; the wrapped runner goes in `-e targetInstrumentation`. Swapping them produces an error message that explains neither.

Installing without Gradle. The package-visibility flag belongs to `pm install`, **not** `adb install`: AOSP `PackageManagerShellCommand` parses `--force-queryable`, while adb's own command line (`client/commandline.cpp`) has no such option (both verified 2026-10). Push first, then install on-device:

```bash
adb push path/to/orchestrator-1.6.1.apk /data/local/tmp/
adb shell pm install --force-queryable -r /data/local/tmp/orchestrator-1.6.1.apk
adb push path/to/test-services-1.6.0.apk /data/local/tmp/
adb shell pm install --force-queryable -r /data/local/tmp/test-services-1.6.0.apk

adb shell 'CLASSPATH=$(pm path androidx.test.services) app_process / \
 androidx.test.services.shellexecutor.ShellMain am instrument -w -e \
 targetInstrumentation com.example.test/androidx.test.runner.AndroidJUnitRunner \
 androidx.test.orchestrator/.AndroidTestOrchestrator'
```

Gradle wiring — `androidTestUtil`, **not** `androidTestImplementation`:

```gradle
android {
  defaultConfig {
    testInstrumentationRunner "androidx.test.runner.AndroidJUnitRunner"
    testInstrumentationRunnerArguments clearPackageData: 'true'
  }
  testOptions {
    execution 'ANDROIDX_TEST_ORCHESTRATOR'
  }
}

dependencies {
  androidTestImplementation 'androidx.test:runner:1.7.0'
  androidTestUtil           'androidx.test:orchestrator:1.6.1'   // NOT androidTestImplementation
}
```

Cost/benefit: each test starts from a fresh `Application`, a crash cannot take the suite down, and `pm clear` between tests is real. Price: 1-2 s per test of process startup — a 500-test suite goes from ~5 min to 15+ min. Use it only where state leakage actually bites.

## Output framing and status codes

```
INSTRUMENTATION_STATUS: <key>=<value>      # repeated per Bundle entry per status frame
INSTRUMENTATION_STATUS_CODE: <int>          # one per status frame
...
INSTRUMENTATION_RESULT: <key>=<value>      # final result bundle
INSTRUMENTATION_CODE: <int>                 # final, exactly once
```

| Code | Meaning |
|---|---|
| `1` | test started (`REPORT_VALUE_RESULT_START`) |
| `0` | passed (`REPORT_VALUE_RESULT_OK`) |
| `-1` | process error / unexpected throw (`REPORT_VALUE_RESULT_ERROR`) |
| `-2` | assertion failure (`REPORT_VALUE_RESULT_FAILURE`) |
| `-3` | ignored (`@Ignore`) — added by AndroidJUnitRunner |
| `-4` | assumption failure — added by AndroidJUnitRunner |

Framework only defines `1/0/-1/-2`; `-3`/`-4` are runner extensions. Treating them as failures manufactures red builds.

The trailing `INSTRUMENTATION_CODE` is a different thing: it carries `Activity.RESULT_*` values — `-1` (`RESULT_OK`) when the run finished without a runner-level error, `0` (`RESULT_CANCELED`) when the runner itself broke. "Neither this line nor the shell `$?` reliably reports test pass/fail": AndroidJUnitRunner calls `finish(Activity.RESULT_OK, results)` regardless, and AOSP `Instrument.java` ends with an unconditional `System.exit(0)`.

Gating, therefore, is stdout parsing:

```bash
output=$(adb shell am instrument -w -r \
  com.example.app.test/androidx.test.runner.AndroidJUnitRunner)
if echo "$output" | grep -qE 'INSTRUMENTATION_STATUS_CODE: -[12]$'; then
  echo "FAILED"; exit 1
fi
```

Both anchors matter: `^`/leading match avoids substring hits, `-[12]$` avoids matching `-20`-style numbers. Keep the raw stream as an artifact (`| tee instrument.log`) and export JUnit XML only when a dashboard needs it (`connectedDebugAndroidTest` writes `app/build/outputs/androidTest-results/connected/<variant>/TEST-*.xml`); many pipelines run sharded `am instrument` and post-process the status stream themselves.

## Exit-code matrix (what CI may trust)

| Operation | Behaviour |
|---|---|
| `adb push` / `adb pull` | 0 on success; non-zero on transport/filesystem failure — must be checked |
| `adb install` / `adb uninstall` | 0 on success; modern adb returns non-zero on `INSTALL_FAILED_*`, older versions exit 0 even when package manager failed |
| `adb wait-for-device` (and variants) | blocks until the state, then 0 — usable as a boot gate together with `boot_completed` |
| `adb shell <cmd>` | propagates the device exit code only on platform-tools ≥ 24 **and** device API ≥ 24; older devices always return 0 |
| `adb -t <id>` | transport id, **not** a timeout |
| `am instrument` | always 0 — see above |

Escape hatch for pre-API-24 devices: print a sentinel on the device (`adb shell 'cmd; echo __ADB_RC=$?'`) and grep it host-side.

## `adb shell` invocation details

```bash
adb -s SERIAL shell -T COMMAND...
```

`-T` disables the PTY while keeping remote exit code and stdout/stderr separation — the right form for scripts. `shell -x` **disables** remote exit codes and stream separation; text-mode automation almost never wants it. A PTY also injects CR and escape sequences, the number-one cause of parse failures.

Everything after `shell` crosses two parsers (local shell, then device shell); Platform Tools 23+ follows `ssh(1)` semantics, so quote twice. Pass arguments as vectors where possible instead of building one string from untrusted data.

## Port forwarding

```
adb forward [--no-rebind] LOCAL  REMOTE        # host → device
adb reverse [--no-rebind] REMOTE LOCAL         # device → host  (arguments reversed!)
```

| Direction | Use | Recipe |
|---|---|---|
| `forward` | host drives a device-side service | `adb forward tcp:9222 localabstract:chrome_devtools_remote` |
| `reverse` | device reaches a host-only service (CI runner, Metro, local backend) | `adb reverse tcp:8080 tcp:8080` |

`reverse` with both sides equal works even when the order is wrong, which hides the bug until the ports differ. Example: `adb reverse tcp:9000 tcp:8080` exposes host `:8080` as device `localhost:9000`.

| Token | Position |
|---|---|
| `tcp:<port>` | either side; `tcp:0` on LOCAL picks a free port and prints it |
| `localabstract:<name>` | abstract Unix socket (Chrome DevTools, Stetho, Flipper) |
| `localreserved:<name>` / `localfilesystem:<name>` | reserved / filesystem Unix sockets |
| `jdwp:<pid>` | REMOTE only |
| `vsock:<CID>:<port>` | REMOTE only (emulator) |
| `dev:<char-device>` | character device passthrough |
| `acceptfd:<fd>` | LOCAL only, listen on a pre-opened fd |

Cleanup: `--list`, `--remove`, `--remove-all`. Remove your own mappings in a `trap`, or the next run dies with `cannot bind: address already in use`.

## Bash idioms that survive CI

Timeouts (there is no per-command timeout flag):

```bash
timeout 60s adb -s emulator-5554 shell am instrument -w -r ...
echo $?
# 124 = killed at the deadline; 137 = escalated to SIGKILL
# 0 only means am instrument exited — parse the output for pass/fail
```

```bash
( timeout 600s adb logcat -v threadtime > artifacts/logcat.txt ) &
LOGCAT_PID=$!
trap 'kill $LOGCAT_PID 2>/dev/null' EXIT
```

On macOS `timeout` is `gtimeout` (`brew install coreutils`).

Bounded retry for transient transport errors (`error: device 'X' not found`, `error: closed`, `error: protocol fault`, `error: device offline`):

```bash
retry() {
  local n=0 max=3 delay=2
  until "$@"; do
    n=$((n+1))
    [ "$n" -ge "$max" ] && return 1
    echo "[retry] $* failed (attempt $n); restarting adb"
    adb kill-server; adb start-server
    sleep "$delay"
  done
}

retry adb install -r app.apk
```

Three constraints: it must only cover transport failures (a real test failure exits 0 from `am instrument` and is never retried); `pm clear` the test package between attempts or transient state leaks; unbounded retries turn flakiness into a hang.

Parallel fan-out:

```bash
adb devices \
  | tail -n +2 \
  | awk '$2=="device"{print $1}' \
  | xargs -I {} -P 4 adb -s {} <command>
```

`tail -n +2` drops the header, `awk '$2=="device"'` filters `unauthorized`/`offline`/`recovery`, `-P 4` matches physical hubs, `-P 0` means "as many as there are inputs". Serialize setup, parallelize tests:

```bash
SERIALS=$(adb devices | awk '$2=="device"{print $1}')
echo "$SERIALS" | xargs -I {} -P 0 adb -s {} install -r app-debug.apk
echo "$SERIALS" | xargs -I {} -P 0 adb -s {} install -r app-debug-androidTest.apk

i=0
for S in $SERIALS; do
  adb -s "$S" logcat -c
  adb -s "$S" shell am instrument -w -r \
       -e numShards $(echo "$SERIALS" | wc -l) -e shardIndex "$i" \
       com.example.test/androidx.test.runner.AndroidJUnitRunner \
       > "results-$S.txt" &
  i=$((i+1))
done
wait

if grep -qE '^INSTRUMENTATION_STATUS_CODE: -[12]$' results-*.txt; then
  echo "test failures detected"; exit 1
fi
```

Concurrent `adb install` against one device fights itself, so installs are serial; `wait` hides every exit code, so the gate has to be the parsed output.

Artifact namespacing for TCP serials:

```bash
artifact_dir() { echo "artifacts/${1//[:_]/-}"; }
for S in $(adb devices | awk '$2=="device"{print $1}'); do
  D=$(artifact_dir "$S"); mkdir -p "$D"
  adb -s "$S" logcat -d -v threadtime > "$D/logcat.txt"
  adb -s "$S" shell screencap -p /sdcard/last.png
  adb -s "$S" pull /sdcard/last.png "$D/last.png"
done
```

A serial like `192.168.1.5:5555` otherwise splits into nested directories and the artifact layout drifts.

Idempotent preamble:

```bash
adb wait-for-device
adb shell input keyevent 82                         # wake; no-op if already on
adb shell pm clear com.example.app                  # data + cache
adb shell pm clear com.example.app.test             # test-process state
adb shell am force-stop com.example.app
adb shell settings put global window_animation_scale 0
adb shell settings put global transition_animation_scale 0
adb shell settings put global animator_duration_scale 0
```

Cleanup that cannot mask the real failure:

```bash
cleanup() {
  adb shell am force-stop com.example.app                       || true
  adb shell pm clear     com.example.app                        || true
  adb uninstall          com.example.app                        || true
  adb forward --remove tcp:6100                                 || true
  adb reverse --remove-all                                      || true
  adb shell settings put global window_animation_scale 1        || true
  adb shell settings put global transition_animation_scale 1    || true
  adb shell settings put global animator_duration_scale 1       || true
}
trap cleanup EXIT
```

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `$?` is 0, log shows `-2` | `am instrument` always exits 0 | parse `INSTRUMENTATION_STATUS_CODE` |
| `am instrument` returns instantly, tests still running | missing `-w` | add `-w` (with `-r`) |
| Output is decoded `report_key_streamresult` | missing `-r` | add `-r` |
| `-e class X:method` runs nothing | separator is `#` | `-e class X#method`; cross-check `INSTRUMENTATION_STATUS: numtests=1` |
| Orchestrator errors, `clearPackageData` ignored | target and runner positions swapped | runner position = `androidx.test.orchestrator/.AndroidTestOrchestrator`, target via `-e targetInstrumentation` |
| `clearPackageData` passed without orchestrator | runner-only argument | install orchestrator and call it in the right shape |
| Two shards, no speedup | same `-s` for both | one device per shard |
| `-e class` and `-e package` together, class ignored | `package` takes precedence | pass one, or CSV in `class` |
| CI flaky, green locally | animations | three scales to 0 / `testOptions.animationsDisabled = true` |
| State bleeds between tests | no per-test reset | orchestrator + `-e clearPackageData true` |
| `androidTestImplementation 'androidx.test:orchestrator:…'` installs nothing | it is a separate APK, not a library | `androidTestUtil` |
| Cannot bind port on a re-run | leaked forward/reverse mapping | `trap` + `--remove` / `--remove-all` |
| Cleanup overwrote the failure code | cleanup commands not `|| true` | suffix every one |
| `device not found` on a cold runner | one attempt, no retry | bounded `retry` with `kill-server`/`start-server` between |
| `adb -t 60` did not time out | `-t` is a transport id | `timeout 60s adb …` |
