# Skills

[English](./README.md) | [简体中文](./README.zh-CN.md)

A collection of agent skills for the [open agent skills ecosystem](https://www.npmjs.com/package/skills) — portable `SKILL.md` packages that give AI coding agents new workflows.

## Included Skills

- **[quadlet-creator](./quadlet-creator/)** — Convert `docker run` commands, Docker Compose setups, or self-hosting deployment assets into reviewable Podman Quadlet output; includes rootless runtime identity (UserNS/UID) troubleshooting.
- **[video-edit-planner](./video-edit-planner/)** — Plan video edits through iterative dialogue: transcribe audio (FunASR), extract emotion/event labels and key frames, analyze visuals, and produce structured cut/transition/assembly plans.
- **[discord-user-operations](./discord-user-operations/)** — Operate Discord as a regular user account: read, search, and post.
- **[china-weather-query](./china-weather-query/)** — China weather from CMA official data: observation, forecast, warnings, AQI.
- **[chinese-humanizer](./chinese-humanizer/)** — Strip the AI flavor out of Simplified Chinese prose: stock phrases, nominalization, translationese sentence structure, template rhythm; keeps facts, terminology, and the author's voice.
- **[xianyu-operations](./xianyu-operations/)** — Xianyu (闲鱼 / Goofish) operations: keyword search, item detail, own listings, IM sessions — plus publishing, taking listings down and sending messages, each write approved by the user. mtop JSON API over plain HTTP, with a browser path only for search.
- **[napcat-onebot](./napcat-onebot/)** — Talk to QQ through a self-hosted NapCat protocol side (OneBot 11 over HTTP): send group and private messages, read chat history on demand, look up groups and friends, upload files — plus the auth, retcode, id-precision and account-risk failure modes, and how to bring the protocol side up.
- **[zitadel-administration](./zitadel-administration/)** — Operate a self-hosted ZITADEL instance through its APIs: service accounts and their three authentication methods, administrator roles at instance/org/project level, projects, OIDC/API/SAML applications, organizations, users and role assignments — plus the connectRPC v2 versus legacy v1 REST split, the error model, and the tasks only the legacy API can still do.
- **[android-adb](./android-adb/)** — Drive Android devices from a host shell with raw `adb`: wireless pairing and mDNS, transport selection and state recovery, input injection and display/state control, logcat and artifact capture, `am instrument` and CI gating — plus the UI-tree dumps, bug reports, ANR evidence, Doze testing and test-device reset that the common skill packs leave out.
- **[ui-design-iteration](./ui-design-iteration/)** — Take a UI from first draft to reviewed page: start from a reference the user picks — their own preferred sources first, a starter catalogue otherwise — carrying its design language — from its code or its live demo — over to the content the page needs, instead of generating from a brief, then make it a live page — bind style into tokens, pick and mark elements so the selection reaches the agent, turn each request into an addressed single-dimension patch, audit limits and accessibility at every width.

## Installation

```bash
# Install all skills
npx skills add https://git.nite07.com/nite/skills.git -g --all

# Install a single skill
npx skills add https://git.nite07.com/nite/skills.git -g -s quadlet-creator

# List available skills without installing
npx skills add https://git.nite07.com/nite/skills.git --list
```

Compatible with 73+ agent frameworks, including Claude Code, Codex, Cursor, and OpenCode. Each skill's own README covers manual installation and usage details.

## Authoring rules

Rules every skill in this repository follows — English-first content, no
hardcoded paths, no secrets, structure and writing conventions — are in
[AGENTS.md](./AGENTS.md).

## Repository Layout

Each top-level directory is one self-contained skill (`SKILL.md` plus optional supporting files), following the open agent skills format:

```text
china-weather-query/      # SKILL.md + references/ + scripts/ + tests/ + README
chinese-humanizer/        # SKILL.md + references/ + README
discord-user-operations/  # SKILL.md + references/ + README
xianyu-operations/        # SKILL.md + references/ + templates/ + README
quadlet-creator/          # SKILL.md + references/ + templates/ + README
video-edit-planner/       # SKILL.md + references/ + scripts/ + README
zitadel-administration/   # SKILL.md + references/ + templates/ + README
napcat-onebot/            # SKILL.md + references/ + README
android-adb/              # SKILL.md + references/ + README
ui-design-iteration/      # SKILL.md + references/ + scripts/ + templates/ + README
```

Several of these skills were previously maintained as standalone repositories (now archived and deleted) and were consolidated here.
