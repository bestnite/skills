# Denuvo titles and hypervisor cracks

Verified against the live board on 2026-11-25, from the staff's pinned topics on the subject (`t=156407`, `t=156419`, `t=156435`, `t=159989`) and from live Denuvo game threads.

Some games cannot be run by swapping `steam_api64.dll`. Denuvo validates a token against the machine, and the working answer is a different kind of release: a hypervisor-based crack, published by a named group for one exact game build.

This is the one case where the clean files are not the answer. Report it and route the user, but never present a Denuvo download as a portable build that will start.

## How to recognise it

| Signal | Where |
|---|---|
| The game has no `SCS - …` thread, or has one that nobody runs | title search returns only the Main Forum thread |
| The game thread's newest release says `EXPERIMENTAL hypervisor-based release` | the crack post itself |
| A group name in the file: `-ARTIFACT`, `DenuvOwO` | the release name |
| SteamDB lists Denuvo for the AppID | external check, useful when the thread is ambiguous |

Do not infer Denuvo from the publisher or the genre. If the thread's newest posts are a DLL swap or a Steam emulator, the game is not Denuvo-locked, whatever the store page implies.

## What the release is

A hypervisor crack runs the game under a controlled hypervisor so that Denuvo's checks observe a machine that passes them. It is not a patch to a DLL and not something you can hand-edit: the release carries game-specific hypervisor drivers, a Denuvo token, and a setup script.

A release post reads roughly like this:

```
<Game>.Update.v<version>.Crack.Only-<GROUP>
Attachment: <Game>.Update.v<version>.Crack.Only-<GROUP>.7z
The release is for the Steam build <build>
This post includes a EXPERIMENTAL hypervisor-based release. You might encounter a BSOD.
```

Every approved release must link the three pinned topics — the introduction, the requirements, and the support thread — and must send all questions to the support thread rather than the game topic.

## Hardware requirements

From the support FAQ (`t=156435`):

- CPU with SLAT and either Intel VT-x or AMD-V.
- **AVX2**, because of how the Denuvo token is generated: Intel Haswell (4th gen, 2013) or later, Tiger Lake for Celeron/Pentium (2020+); AMD Excavator or Zen and newer (AM4/AM5, June 2015+).
- Other groups' releases may state different minimums — read the release post, not this table.

## What must be true of the files

- **Exact build only.** A crack made for build 26123051 does not work on the previous or next build, because the Denuvo token is version-bound.
- **No cross-game reuse.** Hypervisor drivers contain game-specific code. Waiting for the right release is the only correct answer.
- **No editing.** Modified game or crack files break the token.
- `VBS.cmd` is the single piece that is universal across releases.

## Running it on Windows, in outline

The full procedure lives in the release post and in `t=156435`; the shape is:

1. Use the staff-approved `VBS.cmd` for your group (DenuvOwO or ARTIFACT) — the support thread keeps the current one. Never a script from anywhere else.
2. The script turns the Windows security stack off and stops the Windows hypervisor from loading (`hypervisorlaunchtype off`), rather than uninstalling Hyper-V.
3. Disable driver signature enforcement through the advanced boot menu — the approved method, not a runtime patcher.
4. Reboot, play, then revert every change and reboot again.

Two details that catch people:

- **Shutdown is not reboot.** With Fast Startup enabled, a shutdown keeps DSE disabled; only a reboot restores it.
- **Everything needs the reboot.** The board does not support permanently disabling these features, only toggling them around a session.

## The cost of turning that security off

The introduction (`t=156407`) exists so the user can decide with open eyes: VBS is what runs Memory Integrity (HVCI), Credential Guard, and the Windows Hello sign-in protections. While the crack is active, those are not protecting the machine, and kernel-level anti-cheat software may refuse to run or may ban on indicators of kernel modification.

Therefore:

- Have the BitLocker recovery key at hand and know the normal Windows Hello password before touching anything, as the release rules require.
- Disconnect from networks while the game runs where possible.
- Scan the package with a reputable scanner, prefer releases whose hypervisor includes source, and treat any closed-source binary that wants administrator rights as a reason to walk away.
- Expect BSODs on releases marked experimental; that is what the label means.

If the game exits with `Denuvo tried to delete found token`, the hypervisor driver is not running, files were quarantined by antivirus, or the CPU lacks AVX2.

## It is not "running the game inside Hyper-V"

A common misreading, worth correcting before anyone starts: the crack runs on the **host**, and it needs Windows' own hypervisor and VBS **off** — the two uses compete for the same hardware virtualization and cannot easily coexist. Booting a VM and running the game inside it is a different, advanced path: the best-practices post mentions Hyper-V or KVM with nested virtualization and GPU passthrough for people who want isolation anyway, and notes the performance penalty. It is not the supported route and not what the release instructions describe.

## Linux

`t=159989` covers running DenuvOwO and ARTIFACT releases on Linux: a patched Proton plus a minimal hypervisor for CPUID faulting emulation. Minimums there: Intel 4th gen or AMD Ryzen 1st gen or later, Linux kernel 6.0+, with extra caveats for Zen 4 and newer. Only those two groups' releases are covered; anything else follows its own instructions.

## What this skill does with all of it

- **Detects and routes.** If the game is Denuvo-locked, say so, name the build the crack targets, and point at `references/patch-and-run.md` for everything except the Denuvo layer.
- **Reports honestly.** An experimental hypervisor release is not a normal portable build: quote the build, the group, and the experimental flag, and list the requirements (AVX2, VT-x/AMD-V, security features off).
- **Never downloads or runs it.** Hand the user the link and the tradeoff; the decision to disable security features on their machine is theirs, not a side effect of a search.
- **Never mixes releases.** No file from another game or another build, no "close enough" build numbers.
