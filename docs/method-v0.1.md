# Repetita Gravity — conservative semantic consolidation protocol v0.1

## Objective

Repetita Gravity reduces accidental semantic redundancy without disrupting local
reasoning or silently losing substance. It is not a similarity detector followed
by deletion. It is a sequence of isolated, reversible document transactions.

The system may certify only what it can demonstrate. `VERIFIED BY REPETITA
GRAVITY` means that every original semantic unit has a recorded disposition,
all hard anchors were preserved, all formal invariants passed, and semantic
adjudication detected no critical discrepancy. It does not mean mathematical
proof that two natural-language documents are universally equivalent.

## Frozen principles

1. The sentence is a source container, not the conservation atom.
2. Every atomic proposition, fact, reason, qualification, limitation, exception,
   consequence, recommendation and reference receives a stable identifier.
3. Semantic relationship, local communicative function and editorial disposition
   are three independent axes. None may be inferred mechanically from another.
4. Similarity proposes candidates; it never authorises deletion.
5. Every recurrence family is processed in an isolated transaction against an
   immutable base-document hash.
6. A donor containing unique residual payload may never be removed wholesale.
7. Donor repair and receiver accretion are complementary and provenance-traced.
8. Protected evidence, quotations, citations, numbers, qualifications and
   intentional structural recurrences fail closed.
9. A family transaction either passes all critical checks and commits atomically,
   or it rolls back without modifying the working document.
10. The global document is reread after each committed family and after each pass.
11. Passes are adaptive and capped at five; the cap is a safety boundary, not a
    target. Unresolved semantic risk produces `NOT VERIFIED` or human review.
12. Python proves formal invariants. GPT-5.6 adjudicates semantic questions under
    strict schemas. Neither layer may claim the competence of the other.

## The protocol

### 01 — Immutable intake and resource plan

Hash the source document; identify headings, sections, paragraphs, lists,
quotations, citations and sentence boundaries. Estimate input tokens against a
configured model context limit and a conservative safe-input ratio. Select one of:

- whole-document analysis;
- section chunks with a global synthesis;
- overlapping structural chunks governed by one global ledger.

The declared `safe_input_budget` reserves space for instructions, schemas,
retrieved ledger state, reasoning and output. No component may advertise a model's
generic “memory”; it reports the configured limit and measured pressure.

### 02 — Conservation Ledger

Extract atomic semantic units and attach source location, exact wording,
discourse role and hard anchors. The original ledger is append-only. Later states
record dispositions; they do not overwrite provenance.

### 03 — Candidate recurrence graph

Use lexical overlap, transparent concept matching, embeddings and model-assisted
mutual implication as independent evidence channels. Candidate edges retain each
component score. Do not use naïve transitive closure: if A resembles B and B
resembles C, A and C are not thereby equivalent. Weak bridge nodes are split or
sent to review.

### 04 — Three-axis adjudication

For each occurrence determine separately:

- semantic relation: exact equivalent, paraphrase equivalent, partial overlap,
  related but non-duplicate, or uncertain;
- local function: structural, summary, context, evidence, analysis,
  recommendation, conclusion, definition or transition;
- proposed disposition: preserve, transfer, merge, cross-reference, remove as
  fully redundant, or human review.

### 05 — Dependency and risk scheduler

Build dependencies among families when they share units, anchors, antecedents or
gravity-centre passages. Process the lowest-risk independent family first. The
default family-risk model combines unique-residual density, section dispersion,
ambiguity, thesis centrality and dependency degree. Its weights are configuration
defaults requiring calibration, not scientific constants.

### 06 — Logical Gravity Centre

Score candidate sections for functional fit, treatment completeness, evidence
proximity, contextual coherence and minimal disruption. Protected evidence can
orbit an analytical centre; it need not be physically moved into it. Ties or low
margins require adjudication rather than arbitrary selection.

### 07 — Family Transaction Workspace

Create an isolated transaction containing all original occurrences, relevant
context windows, classifications, the selected centre, donor plans, receiver plan,
base hash, changed-unit allowlist and verification record. Only one family is
edited in the transaction.

### 08 — Donor subtraction plan

Before rewriting, decompose every donor into duplicated payload, unique residual
payload, local function, grammatical dependencies, antecedents and hard anchors.
No edit occurs at this stage. Any unassigned semantic atom blocks the transaction.

### 09 — Donor repair and receiver accretion

Repair the donor locally after subtracting only the duplicated payload. Accrete
the receiver by integrating unique transferable content in the section's logical
order; never concatenate donor sentences. Every target span carries source-unit
provenance. Unaffected units are outside the mutation allowlist.

### 10 — Transaction verification and atomic commit

Verify ledger reconciliation, anchor conservation, mutation-scope isolation,
grammar/antecedent integrity, cross-reference resolution, absence of new
duplication and bidirectional semantic coverage. Critical failure rolls back the
entire family transaction. Ambiguity sends it to human review.

### 11 — Global reread and adaptive continuation

After each commit, compare the new document with both the immediately preceding
state and the immutable original. Continue only if unresolved accidental burden
is material, expected benefit exceeds conservation risk and the document has not
stabilised. Stop early when checks pass and marginal improvement is negligible.

## Certification invariants

- I01: stable unit IDs are unique;
- I02: every original unit has exactly one final disposition;
- I03: all hard anchors are preserved or explicitly authorised for transformation;
- I04: partial-overlap donors retain all unique residual payload;
- I05: structural, evidentiary and functionally necessary occurrences are preserved;
- I06: each receiver integration has source-unit provenance;
- I07: every generated cross-reference resolves;
- I08: no mutation occurred outside the transaction allowlist;
- I09: no new accidental semantic family was introduced;
- I10: every family transaction committed or rolled back atomically;
- I11: one canonical treatment exists for each safely consolidated family;
- I12: unresolved critical risk withholds certification.

## Calibration boundary

Thresholds, similarity weights, gravity weights, risk weights and stability
margins remain configurable until evaluated against a labelled corpus. The
methodology freezes the evidence channels, state transitions and invariants—not
unvalidated numerical constants.

