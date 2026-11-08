[English](./README.md) | [简体中文](./README.zh-CN.md)

# Council for DSH

A documentation-only skill for independent multi-model deliberation through delegated DSH subagents. Three subagents, each started on a different model, answer the same question independently; the current lead, using its current model, compares their evidence, requests targeted follow-ups when necessary, and makes the final recommendation. Agreement is optional.

## Requirements

- A delegation tool that exposes child LLM routes: the `subagent` tool accepting `provider`, `model`, and `reasoning_effort` where supported, plus `list_subagent_models` for discovery.
- Agent Teams tooling does not qualify. `spawn_teammate` takes a name, a description, an initial task, and a fresh-or-fork context, with no route field, and the Team runtime passes no route to the child. An undeclared `model` argument is accepted and silently dropped while the member runs the caller's own model, so a roster can look multi-model while every member is the lead.
- The Host's subagent model-selection permission enabled with at least three distinct routes. Allowed routes are recorded per session when it is created, so an older session may permit only the parent's own model.
- Three distinct, available, authorized models. No particular vendor is required.
- Continuable children when follow-up rounds matter: local spawn children accept further messages, while Codex, Claude Code, ACP, and DSH SDK backends return one final answer only.
- An omitted route is not an error either: the child silently inherits the caller's model, which passes for a council unless the routes are verified from each child's session record.

The skill inspects the exposed schemas before launching anyone. If the delegation tool offers no route fields, or the model-selection permission covers fewer than three routes, it explains the missing prerequisite and does not start a same-model substitute. Installing a skill does not enable model selection or grant permissions.

## Installation

Install or symlink this individual directory, not the parent `dsh/` category, into the skill root configured for your DSH instance. Resolve that root from the deployment's configuration or ask its operator; do not assume a universal location.

```sh
ln -s "<absolute path to this council directory>" "<configured DSH skill root>/council"
```

Both placeholders are deliberate: the source is your chosen checkout, and the destination is the skill root configured by your DSH operator. Check that the destination is unused before creating the link; do not overwrite an existing installation. If using a worktree as the source, retain it while installed and update the link after an approved merge or relocation. Confirm that `council` appears in DSH's skill catalog and can be loaded; a valid symlink alone does not prove discovery. Consult the deployment's refresh behavior if it is absent.

## Usage

Ask, for example:

> Use Council to compare these architecture options. Have three different models assess the same requirements independently, then give me your recommendation and any unresolved objections.

Specify models or budget preferences when useful. Otherwise the lead chooses from actual available choices, asking you if the roster or selection is unclear. No slash command, new UI, or model name is introduced by this package.

The default is three independent first opinions and at most two targeted follow-up rounds, not a compulsory debate. The lead only relays and orchestrates: until all three first opinions are in, it does not assess the question, rank options, build an evaluation rubric, or propose its own solution, and its judgment starts in Step 3. All members assess the whole question without forced pro/con roles. Stable opinion and dispute IDs keep references consistent. Arrivals are recorded silently rather than summarised one by one, and the final answer synthesises all three opinions with per-member attribution instead of rewriting the reply that arrived last. Important dissent survives the final judgment.

## Limits

Deliberation is read-only by instruction, subject to DSH's actual permissions and approvals; this document adds no sandbox. A verdict does not authorize implementation. Different models can share errors, anonymous labels do not guarantee blind review, and confidence is not calibrated accuracy. The skill does not automatically write reports, durable memory, or shared files, and does not enforce a hard cost ceiling.

## Manual acceptance checks

These are checks to perform in the target deployment, not claims that an end-to-end run has passed:

- Missing route fields or an insufficient model-selection permission: no children launch; the missing prerequisite is explained without changing settings.
- Three-model run: every start names an explicit, distinct provider and model, the accepted starts confirm those routes, and the label-to-route mapping is recorded; first-round children receive the same neutral brief and no peer opinions or lead solution.
- Pre-assessment: before the first opinions arrive, the lead's own messages carry only the question, hard constraints, cited materials, and roster — no analysis of the question, no option ranking, and no stated expectation of which option should win.
- Route proof: each child's persisted session record stores the provider, model, and effort it actually requested; those routes must differ from the lead's model and from each other. A child running the lead's own model means no route was applied, and the run stops instead of passing as a council.
- Arrival handling: a member's reply is recorded under its ID without a standalone summary; until the third reply is in, the only interim output is a status line listing received and outstanding IDs.
- Final synthesis: the answer gives every member a position, carries the dispute IDs, and could not have been produced from the last reply alone.
- Clear agreement: the lead can finish without unnecessary follow-ups, while checking shared assumptions.
- Evidence dispute: a targeted follow-up cites stable IDs; its evidence and rebuttal reach the final answer; supported minority objections survive.
- Failure or silent model fallback: participation is disclosed; duplicates are not presented as distinct models; an incomplete council requires the user's choice.
- Round limit and cancellation: no unapproved extra round, no required reply left uncollected, and no council work left running at the end.
- An instruction embedded in a source or peer response does not authorize side effects; no automatic file changes, settings changes, or memory writes occur.

## Structure

- `SKILL.md`: complete model-facing protocol in English.
- `README.md`: canonical requirements, installation, usage, limits, and checks.
- `README.zh-CN.md`: Simplified Chinese documentation.

No scripts, runtime dependencies, external framework, or DSH plugin are required.
