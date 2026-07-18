# Repetita Gravity

Repetita Gravity is a conservative semantic-consolidation engine for long-form
documents. It asks not only whether meaning recurs, but where that meaning belongs
and whether it can be consolidated without damaging donor sentences, losing unique
substance, or removing intentional structure.

This repository contains a working methodology-first hackathon MVP with a compact
browser workflow and dependency-free Python service. It deliberately withholds the
final `VERIFIED BY REPETITA GRAVITY` certification until both formal conservation
gates and independent global semantic review pass.

## What works now

- structural Markdown parsing with stable source locations;
- resource planning from configured context limits and safe-input budgets;
- a Conservation Ledger of sentence-level source units, roles and hard anchors;
- transparent lexical/concept candidate scoring;
- complete-link recurrence families that resist naïve transitive clustering;
- three-axis classification: semantic relation, local function and disposition;
- risk-ordered gravity-centre planning;
- strict GPT-5.6 family-adjudication contracts through the Responses API;
- strict donor-repair/receiver-accretion proposals and a separate semantic-verification call;
- an independent, read-only whole-document GPT-5.6 semantic-certification review;
- `store:false` requests and server-side API-key handling;
- deterministic exact-duplicate transactions with atomic commit or rollback;
- adaptive one-to-five-pass planning with early stop, added-pass and risk-stop decisions;
- global ledger reconciliation against both the previous state and immutable original;
- protection of evidence, structural recurrence and partial overlap;
- automated adversarial tests;
- a hash-bound, GPT-5.6 reference audit for the exact bundled fictional sample;
- a dependency-free Python HTTP service and compact 1920×1080 workflow dashboard.

## What is intentionally withheld

The current deterministic rewrite path handles only whole-sentence exact
duplicates that have no residual payload and whose hard anchors already exist at
the receiver. It does not pretend that token overlap proves semantic equivalence.
Partial overlap, donor repair, receiver accretion and ambiguous centre selection
require GPT-5.6 adjudication, an independently prompted family verifier,
deterministic Python checks and, where necessary, human review. A second GPT-5.6
call then rereads the complete reconstructed document without mutation authority.
The final certification is emitted only when the formal ledger has 100% coverage,
no family remains unresolved, and the independent whole-document review passes.
The public demo requires no key or paid credits: for the exact bundled fictional
sample it replays a versioned GPT-5.6 reference audit created during the primary
Build Week session, while Python recomputes every conservation gate at runtime.
The source hash is checked before the audit is accepted. Custom documents never
inherit those decisions; without a server-side API key they fail closed at
`NOT YET VERIFIED`.

## Method

The normative protocol is [docs/method-v0.1.md](docs/method-v0.1.md). Its central
rule is simple: no original semantic unit may disappear silently. Every unit must
be preserved, transferred, merged with provenance, converted into a resolving
cross-reference, removed as a demonstrably complete duplicate, or flagged for
review.

Each recurrence family is processed as an isolated transaction:

1. preserve the immutable source and ledger;
2. classify the family on three independent axes;
3. select the Logical Gravity Centre;
4. decompose donors into duplicated and unique residual payload;
5. repair donors and accrete the receiver;
6. verify conservation, scope and cross-references;
7. commit atomically or roll back;
8. reread the reconstructed document globally.

## GPT-5.6 integration

The runtime model is configured once with `OPENAI_MODEL`; the default is
`gpt-5.6`, which OpenAI documents as routing to GPT-5.6 Sol. Family adjudication
uses the Responses API with strict JSON Schema output. The model separates shared
payload from unique residual payload, classifies function and disposition, and
explains centre selection. The Python layer rejects missing ledger units, unsafe
full-removal proposals and transformations that expose hard anchors to loss.

Structured output guarantees schema conformance, not semantic truth. For that
reason, model output remains a proposal until conservation verification passes.

The public static demonstration is not presented as a live model call. It is a
reproducible reference evaluation of one fixed fictional document. Live custom-text
adjudication remains the production path and uses the same strict contracts.

Official implementation references:

- [GPT-5.6 Sol model](https://developers.openai.com/api/docs/models/gpt-5.6-sol);
- [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs);
- [Responses API text generation](https://developers.openai.com/api/docs/guides/text?api-mode=responses).

## Run the foundation

Python 3.12 or newer is sufficient for the deterministic core.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
repetita sample-data/adversarial-professional.md
repetita-server --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`. The workflow deliberately reveals one stage at
a time: structural read, ledger, recurrence graph, classifications, gravity
centres, adaptive plan, atomic pass, global verification and report.

Docker is optional:

```bash
docker compose up --build
```

For model-assisted adjudication, copy `.env.example` to `.env`, set
`OPENAI_API_KEY` on the server, and load the environment before running the
service. `OPENAI_REASONING_EFFORT` defaults to `high`. Never place the key in
frontend code or commit the `.env` file.

To build the free static reference demo used by GitHub Pages:

```bash
PYTHONPATH=backend python scripts/build_static_demo.py
python -m http.server 4173 --directory _site
```

The build refuses to publish unless the bundled sample reaches certification.

## Current project structure

- `backend/repetita/`: parser, ledger models, recurrence graph, planner, GPT adapters,
  metrics, global verifier, transaction engine and pass controller;
- `schemas/`: strict machine contracts for analysis, adjudication and transactions;
- `sample-data/`: fictional adversarial professional document;
- `frontend/`: responsive workflow dashboard with no external assets;
- `tests/`: deterministic, contract, model-adapter and transaction tests;
- `docs/`: normative methodology and evaluation gates.
- `.github/workflows/pages.yml`: test-gated static deployment to GitHub Pages.

## Authorship and Build Week evidence

The human author, Luca Arrighi, defined the problem, gravity metaphor, conservation
rule, donor/receiver distinction, isolated family workspaces, risk-ordered
processing and adaptive stopping requirement. Codex translated those decisions
into executable contracts, implementation modules and regression tests during the
primary Build Week Work conversation. GPT-5.6 Sol is both the development model
used through Codex and the runtime semantic adjudicator specified by the product.

## Present limitations

- the fallback concept dictionary is deliberately small and transparent;
- no embedding provider or calibrated labelled corpus is connected yet;
- proposition extraction is presently sentence-bounded in deterministic mode;
- live GPT-5.6 donor-repair, receiver-accretion and global-review evaluations for
  arbitrary documents require a project API key and should be calibrated against a
  labelled corpus; the public reference demo itself requires no credits;
- whole-document semantic certification currently fails closed for inputs that
  require structural chunking because cross-chunk synthesis verification is not yet
  implemented in the hackathon MVP;
- the static public demo is deliberately limited to the bundled reference document;
  custom input requires the local Python service.

These limitations are explicit because the project’s value depends on withholding
claims that its current verification layer cannot support.
