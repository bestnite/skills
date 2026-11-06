[English](./README.md) | [简体中文](./README.zh-CN.md)

# Council for DSH

A documentation-only skill for independent multi-model deliberation using DSH Agent Teams. Three teammates answer the same question independently; the current lead, using its current model, compares their evidence, requests targeted follow-ups when necessary, and makes the final recommendation. Agreement is optional.

## Requirements

- DSH Agent Teams enabled.
- Lead-controlled teammate model selection enabled and exposed through a supported runtime mechanism.
- Three distinct, available, authorized teammate models. No particular vendor is required.

The skill checks live capabilities before launching members. If the spawn tool offers no model selection and the runtime supplies no supported alternative, it explains the missing prerequisite and does not start a same-model substitute. Installing a skill does not enable model selection or grant permissions.

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

The default is three independent first opinions and at most two targeted follow-up rounds, not a compulsory debate. The lead relays the question neutrally without first proposing its own solution. All members assess the whole question without forced pro/con roles. Stable opinion and dispute IDs keep references consistent. Important dissent survives the final judgment.

## Limits

Deliberation is read-only by instruction, subject to DSH's actual permissions and approvals; this document adds no sandbox. A verdict does not authorize implementation. Different models can share errors, anonymous labels do not guarantee blind review, and confidence is not calibrated accuracy. The skill does not automatically write reports, durable memory, or shared files, and does not enforce a hard cost ceiling.

## Manual acceptance checks

These are checks to perform in the target deployment, not claims that an end-to-end run has passed:

- Missing Teams or model-selection access: no members launch; the missing prerequisite is explained without changing settings.
- Three-model run: returned runtime metadata confirms distinct models; first-round members receive the same neutral brief and no peer opinions or lead solution.
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
