# Verification architecture

Repetita Gravity uses three non-interchangeable gates. Passing one gate never
implies that the others passed.

## 1. Family semantic gate

GPT-5.6 adjudicates one isolated recurrence family. It must account for every
occurrence, separate semantic relation from local function and editorial
disposition, identify duplicated and unique residual payload, and select an
existing Logical Gravity Centre. An unresolved question or hard-anchor risk fails
closed.

When every occurrence performs a necessary distinct function, the family is
recorded as preserved and no rewrite call is made.

## 2. Atomic transaction gate

If a rewrite is justified, a separate GPT-5.6 call proposes donor repair and
receiver accretion. Another independently prompted call verifies every family unit.
Python then checks source hashes, mutation scope, provenance, hard anchors,
cross-reference resolution and the exact set of changed unit IDs. The family is
committed atomically or rolled back in full.

## 3. Whole-document certification gate

Python reconciles every immutable source unit against the reconstructed document
and all committed transactions. It checks hard anchors, transaction state and new
candidate recurrence families. Only after those formal gates pass and no semantic
occurrence remains unresolved does a read-only GPT-5.6 verifier receive:

- the immutable original document;
- the reconstructed document;
- every ledger unit and its formal destination;
- committed transaction audits;
- prior family adjudications and verifications.

The global verifier must return exactly one check for every original unit ID and
must separately confirm evidence, qualifications, exceptions, anchors,
cross-references, gravity-centre coherence, narrative continuity and absence of new
accidental redundancy. Python rejects a claimed pass if any check is false, any unit
is missing or duplicated, or any failure is reported.

`VERIFIED BY REPETITA GRAVITY` is returned by the server only when all three layers
pass. Missing credentials, unsupported chunking, model refusal, malformed
Structured Output, ambiguity, coverage loss or verification failure results in
`NOT YET VERIFIED`.

## Structured Outputs boundary

The OpenAI Responses API requests use strict JSON Schema, `store: false`, GPT-5.6
and configurable reasoning effort (high by default). Schema conformance makes the
audit machine-readable; it does not establish semantic truth. The independent
prompts and deterministic reconciliation are therefore part of the safety model,
not optional decoration.
