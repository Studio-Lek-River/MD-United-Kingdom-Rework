---
name: validate
description: 'Run the Millennium Dawn validation tools against this submod (overlaid on the pinned MD commit) and summarize errors by category as file:line. Use only when the user explicitly asks to validate, e.g. "/validate", "run the validators". Optional arg: a batch name (core, targeted-a, targeted-b).'
disable-model-invocation: true
---

Run the Millennium Dawn validation tools against this submod's files and summarize the results.

Supported arguments: a batch name (`core`, `targeted-a`, `targeted-b`; default all).
Requested arguments: $ARGUMENTS

Steps:

1. Run from the project root (needs an MD checkout containing the commit in `tools/md_base_ref.txt`,
   default `D:/secondary-md`; pass `--md <path>` otherwise):
   ```
   python tools/validate_with_md.py [--batch <batch>]
   ```
   The script overlays the owned files on a temporary sparse worktree of MD, runs MD's validator
   batches, and prints only findings in files this repo owns. It exits 1 on gating errors.
2. Present results grouped by validator category (variables/flags, scripted localisation, decisions, events, etc.)
3. For each category with errors, show each error as: `file:line — description`
4. End with a summary line: total error count, or "All validators passed" if clean
