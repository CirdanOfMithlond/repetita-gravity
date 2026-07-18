# Repetita Gravity engineering contract

The methodology in `docs/method-v0.1.md` governs implementation.

- Preserve frozen invariants monotonically; do not weaken a passing conservation check to make a test pass.
- Keep semantic relation, local function and editorial disposition separate in schemas, prompts and UI.
- Similarity creates candidates only. It never authorises deletion.
- Every family edit is an isolated transaction against an immutable base hash.
- Any unique residual payload, hard-anchor risk or unresolved ambiguity must fail closed.
- Python verifies formal invariants; model adjudication handles semantic judgments. Do not claim either layer proves what it cannot.
- `VERIFIED BY REPETITA GRAVITY` is forbidden until all certification gates exist and pass.
- Add an adversarial regression test with every methodological change.

Verification command:

```bash
PYTHONPATH=backend python -m unittest discover -s tests -v
```

