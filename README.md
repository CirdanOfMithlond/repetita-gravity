# Repetita Gravity

Repetita Gravity is a conservative semantic-consolidation engine for long-form
documents. It asks not only whether meaning recurs, but where that meaning belongs
and whether it can be consolidated without damaging donor sentences, losing unique
substance, or removing intentional structure.

This repository currently contains the methodology-first foundation. It is not yet
the finished hackathon interface and deliberately does not display the final
`VERIFIED BY REPETITA GRAVITY` certification.

## What works now

- structural Markdown parsing with stable source locations;
- resource planning from configured context limits and safe-input budgets;
- a Conservation Ledger of sentence-level source units, roles and hard anchors;
- transparent lexical/concept candidate scoring;
- complete-link recurrence families that resist naïve transitive clustering;
- three-axis classification: semantic relation, local function and disposition;
- risk-ordered gravity-centre planning;
- strict GPT-5.6 family-adjudication contracts through the Responses API;
- `store:false` requests and server-side API-key handling;
- deterministic exact-duplicate transactions with atomic commit or rollback;
- protection of evidence, structural recurrence and partial overlap;
- automated adversarial tests.

## What is intentionally withheld

The current deterministic rewrite path handles only whole-sentence exact
duplicates that have no residual payload and whose hard anchors already exist at
the receiver. It does not pretend that token overlap proves semantic equivalence.
Partial overlap, donor repair, receiver accretion and ambiguous centre selection
require GPT-5.6 adjudication, independent verification and, where necessary, human
review. Final certification remains disabled until those gates are complete.

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
```

For model-assisted adjudication, copy `.env.example` to `.env`, set
`OPENAI_API_KEY` on the server, and load the environment before running the future
API service. Never place the key in frontend code.

## Current project structure

- `backend/repetita/`: parser, ledger models, recurrence graph, planner, GPT adapter,
  verifier, transaction engine and pass controller;
- `schemas/`: strict machine contracts for analysis, adjudication and transactions;
- `sample-data/`: fictional adversarial professional document;
- `tests/`: deterministic, contract, model-adapter and transaction tests;
- `docs/`: normative methodology and evaluation gates.

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
- model-assisted donor repair and receiver accretion are not yet committed;
- the global post-rewrite semantic verifier and final certification gate remain to
  be implemented;
- no public UI or deployment exists yet.

These limitations are explicit because the project’s value depends on withholding
claims that its current verification layer cannot support.

