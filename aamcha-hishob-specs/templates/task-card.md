# Task card

A task is the unit of work for one person or one Claude Code session: at most a day, one pull request.

```
Id:          SPEC-nnn/Tn
Title:       short imperative
Spec:        specs/SPEC-nnn-….md
Verifies:    ACn, ACm  (and through them Rx, Ry)
Depends on:  SPEC-nnn/Tk
Size:        S (≤ 2 h) · M (≤ 4 h) · L (≤ 1 day)

Context
  Files to read first, and the parts of the spec that matter.

Do
  1. Write or update tests test_specnnn_acn_* ; see them fail.
  2. Implement the smallest change that passes.
  3. Run the full test suite and the constitution checks.

Done when
  - The named acceptance-criteria tests pass in CI.
  - No other test regresses.
  - The spec's task table marks this task done.

Do not
  - Change behaviour outside this task.
  - Add a service, store or framework without an ADR.
```
