# AGENTS.md

Rules for anyone — agent or human — adding or editing a skill in this repository.
They apply to every top-level skill directory.

## 1. English first — but only where it does not cost meaning

- Write skill content in English: `SKILL.md`, `README.md`, `references/*`,
  `scripts/*` (comments, help text, error messages, log lines, JSON keys),
  templates and examples.
- Assume no shared language with the reader. A skill is a portable artifact read
  by agents and users of any language, so English is the lowest common
  denominator — not a preference for English speakers.
- **Meaning outranks the language rule.** English is first-class *on the
  condition* that the content still says exactly what it means. Where translating
  would distort, flatten, or lose the subject matter, write the skill in the
  language of the subject instead. Do not apply this rule mechanically.
- **A skill whose subject is a language is written in that language.**
  `chinese-humanizer` exists to fix AI-flavoured Chinese prose: its SKILL.md,
  references and examples are Chinese, because the word lists, before/after pairs
  and judgement calls *are* the content. An English rewrite of it is less
  accurate, not more portable — and it would be unusable by the reader it is for.
  The bilingual README pair still applies to such a skill like any other.
- The test: *if I translate this, does anything become vaguer, wrong, or
  unfaithful?* If yes, it stays in the language it was written in.
- **The skill text is English; the conversation adapts.** When a skill tells the
  agent to ask the user something, write that question in English and let the
  agent render it in the user's own language. Never bake one natural language
  into the dialogue, and never add "reply in Chinese"-style directives — write
  "talk to the user in their own language" instead.
- Non-English text is allowed for:
  - literal site/page strings the skill matches on (e.g. risk-control text like
    `验证码`, `请先登录`);
  - server response strings (e.g. `SUCCESS::调用成功`);
  - a platform's or product's native name where the native form aids
    identification (e.g. `闲鱼` for Goofish);
  - a deliberate translation file or localized sample the skill ships;
  - **a skill whose subject is a language — the whole skill, prose included, not
    just the sample text** (the `chinese-humanizer` case above).
- Outside those cases everything is English: explanatory prose, headings,
  comments, and example values picked for convenience. In an English skill prefer
  `router` over `路由器` as an example keyword.
- **Every skill directory ships a bilingual README pair**: `README.md`
  (English, canonical) and `README.zh-CN.md` (Simplified Chinese). A missing
  half is a gap to fill, not a matter of taste — a reader who does not read
  English has no other entry point.
- Both files open with the same switcher line, so either one leads to the other:

  ```
  [English](./README.md) | [简体中文](./README.zh-CN.md)
  ```

- Outside the language-subject case, `SKILL.md` and `references/` are
  **English-only** — `SKILL.md` is what a host agent loads, so it must not fork
  per language. The README is the only paired file, and the English one stays
  canonical.
- The root README pair follows the same rule.

## 2. Never hardcode paths

- No absolute paths, and no assumptions about where something is installed or
  written: `/home/<user>/…`, `/Users/…`, `C:\…`, `~/.cache/<tool>/…`,
  `~/.config/<app>/…` as *the* location.
- Where a tool lives, where state is written, where a config file goes — those
  are the environment's and the user's decisions. Resolve them at runtime, in
  this order of preference:
  1. an environment variable the user sets (document its name; never pick its
     value);
  2. the tool's own "where am I" output (`tool info`, `--print-path`, …);
  3. an API that resolves it (e.g. Playwright's
     `pw.chromium.executable_path`);
  4. a direct answer from the user.
- Config examples must use visible placeholders that state their provenance —
  `<path reported by cloakbrowser info>`, `<your client's config path>`,
  `<any writable directory>` — plus one line saying the placeholder is
  deliberate and whose decision the value is.
- Do not discover installs by globbing guessed directories. Report capability
  ("no browser available") and let the environment declare the path: a wrong
  guessed path is worse than an explicit "not configured", because it fails
  later and looks like a bug in the skill.
- Relative paths *inside* a skill are correct and preferred: `scripts/foo.py`,
  `references/bar.md`.
- **One exception for runtime state: a saved login session.** A browser tool's
  own persistent profile comes first. When there is none, the session (and any
  per-account state such as a device id) goes in `.state/` inside the skill's own
  directory, resolved at runtime, and nowhere else. Because every credential a
  skill wrote is then in one place the user can inspect and delete. The skill
  asks once before the first write, creates files `0600`, ships a `.gitignore`
  that ignores `.state/`, and carries `references/session-persistence.md`, which
  holds the full rules.
- The same applies to service endpoints: don't bake in `127.0.0.1:3000` as
  universal truth; name the setting and let the user supply it.
- Machine-specific facts (a container name, this host's IP, an account id) never
  belong in a published skill. Keep them in a local, unpublished note — and say
  in the skill where that note lives.

## 3. No secrets, no personal data, no build artifacts

- Never commit cookies, tokens, API keys, session strings, personal URLs, or a
  specific user's identifiers.
- A skill that needs credentials takes them from the user's environment and
  states how to revoke them afterwards.
- Do not commit generated files: `__pycache__/`, `*.pyc`, `node_modules/`,
  build output, `.env`. These belong in `.gitignore`.
- Publish only what is portable. Local paths, probe results, and this machine's
  quirks stay out.

## 4. Structure and naming

- One top-level directory per skill; the directory name is the skill name
  (lowercase, hyphens).
- Required: `SKILL.md` (YAML frontmatter with `name` and `description`),
  `README.md`, and `README.zh-CN.md`. Optional: `references/`, `templates/`,
  `scripts/`, `tests/`, `assets/` — and see §6 before adding anything to
  `scripts/`. Whatever you ship, say so in `SKILL.md` and in the README's
  structure section: an undocumented directory is invisible to the agent.
- `description` is one line, trigger first ("Use when …"), no marketing. Host
  agents may truncate long descriptions (Hermes cuts at 57 characters), so
  front-load the trigger.
- Keep `SKILL.md` the entry point and push detail into
  `references/<topic>.md`, named by topic. Support files load on demand.
- **Skills are self-contained.** Installs are per-skill (`npx skills add … -s
  <name>`), so a skill cannot rely on a sibling directory. When two skills need
  the same text — the browser-tool setup guide is the current example — each
  carries its own copy; edit both when you change one. The same goes for
  `references/session-persistence.md` in every skill that drives a logged-in
  browser.
- Adding or removing a skill: update **both** root READMEs.

## 5. Writing rules

- Imperative rules with the reason attached: "Do X, because Y". One rule per
  lesson, no incident narration, no PR numbers, no dates inside rules.
- Time-sensitive findings go to `references/` with an explicit
  "verified on <date>" line.
- Separate what was verified from what was assumed; label unverified claims.
- Prefer a fact over an adjective. If a number came from a measurement, keep the
  number.

## 6. Scripts stay narrow (narrow script, wide docs)

A skill is not an MCP server. An MCP server owns a capability; a skill hands the
agent knowledge plus, at most, the code that must be exact. The default is *no
code* — reach for it only where prose would be unreliable. When code is warranted,
the question is not "script or snippet" but **"can the user's environment make
this fail?"**

- **Scripts compute; documents decide.** Legitimate script territory is
  byte-exact arithmetic (signatures, hashes, encodings), protocol frame
  construction, format conversion, and reduction of data too large to read whole.
  Everything else is prose.
- **Never put environment or capability checks in a script.** Whether the agent
  has a browser tool, which binary is installed, whether a session is logged in —
  the agent can see its own toolset and can open a page. A script that answers
  those is usurping a decision the agent makes better, and it will be wrong on
  setups nobody anticipated.
- **Prefer dependencies to be empty.** A signer that needs `requests` and
  `playwright` installed to tell you "not ready" is a design smell; stdlib-only
  is the target for anything shipped here.
- **Where the action depends on the environment, write the decision, not a
  branch.** "If you have a browser tool, do A; otherwise ask the user for one,
  setup guide here" beats a subcommand that probes for browsers.
- **Judge by environment sensitivity, not by "script vs snippet".** A finished
  script is fine — preferable, even — when nothing about the user's machine can
  make it fail: pure computation over declared inputs (signing, hashing,
  encoding, format conversion, index arithmetic) behaves identically everywhere.
  Ship those as complete scripts with a real interface.
- **When the environment can break it, ship a template instead.** If the script
  has to locate tools or files, pick a transport, find where state lives, cope
  with OS differences, or assume something about the agent runtime, then it is
  not a script — it is a snippet the agent copies, adapts at the marked spots,
  and runs. A fixed interface there has to guess, and it will guess wrong
  somewhere. Either way, say *why* each marked spot differs per machine.
- **One script (or snippet) that does one thing beats a toolkit of subcommands.**
  Every subcommand is a promise the skill has to keep across platforms forever,
  and a wider surface for the next breaking platform change.
- The test to apply before adding code: *would a competent agent, given only the
  docs, get this wrong or do it inconsistently?* If not, it belongs in prose.

## Checklist before committing

- [ ] No non-English text, except verbatim external strings, native platform
      names, and a skill whose subject is a language (written in that language
      throughout, not just in its samples).
- [ ] No absolute or assumed paths — placeholders instead, with provenance.
- [ ] No secrets, no personal identifiers, no machine-specific facts.
- [ ] Session material is written only to the skill's `.state/`, and `.state/` is
      ignored by git.
- [ ] `SKILL.md` + `README.md` + `README.zh-CN.md` present, the pair sharing a
      switcher line; root READMEs updated if the skill list changed.
- [ ] Anything dated or environment-specific lives in `references/` and is
      marked as such.
- [ ] Any shipped code computes only what must be exact: no environment probing,
      no capability checks, minimal dependencies.
- [ ] Environment-sensitivity decided: a finished script only if nothing about the
      user's machine can break it, otherwise a template with the adaptation points
      marked and explained.
