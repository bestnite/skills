[English](./README.md) | [简体中文](./README.zh-CN.md)

# DSH-specific skills

This category contains skills that depend on DeepSeek Harness capabilities, rather than portable workflows for arbitrary agent hosts. Each child skill is self-contained and declares its prerequisites.

## Skills

- **[council](./council/)**: three different models give independent opinions through Agent Teams; the current lead chairs evidence-based follow-ups and judgment. Requires lead-controlled teammate model selection.

## Installation

Install or link each leaf skill directory into the skill root configured for your DSH instance. Do not assume linking this category makes its children discoverable. See each skill's README for installation and verification; this category itself has no `SKILL.md`.

## Structure

- `README.md` and `README.zh-CN.md`: category index and installation boundary.
- `council/`: complete Council skill, with its own skill entry and bilingual README pair.
