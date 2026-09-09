# Helix-ARPA Bounded Coding Agent

A locally governed coding-agent research project built around a simple question:

> **Can I make a local model genuinely useful for software work without giving it permission to quietly become the operator?**

`ws-code-agent` is the working answer to that question. It combines local models, explicit authority, source grounding, isolated candidate edits, deterministic validation, durable evidence, escalation rules, and mandatory human review.

The project is intentionally not “give an LLM a shell and see what happens.” It is a proving and training surface for **agentic behavior under boundaries**.

That distinction turned out to matter more than model size.

## Portfolio view

### What I built

- a bounded local coding-agent executor and experiment harness;
- explicit modes for observation, clarification, and narrowly supervised repository work;
- machine-readable request protocols that separate model intent from actual effects;
- source-grounding requirements so a model must read the file it intends to change;
- isolated candidate generation so the real source tree is not the model's scratchpad;
- visible and hidden validators that evaluate candidates independently of model self-report;
- fixed repair and turn limits;
- durable escalation states instead of infinite retries;
- model/runtime qualification records tied to exact artifacts and profiles;
- real-repository pilots with both successful and failed outcomes preserved; and
- a hard terminal boundary of **`AWAITING_OPERATOR_REVIEW`**, never automatic promotion.

The important artifact is not one model that happened to write a correct line of Python. It is the machinery that can tell the difference between:

- a good idea expressed in a broken patch;
- a syntactically valid request based on source the model never actually read;
- an authorized edit that fails validation;
- a genuine model failure;
- an infrastructure failure; and
- a candidate that is technically valid but still requires a human decision.

That was the curriculum.

## Architecture in one screen

```text
operator-authorized task
        |
        v
bounded supervisor / authority policy
        |
        +---- requirements and writable scope
        +---- frozen source snapshot
        +---- model/runtime profile
        +---- fixed repair/turn limits
        +---- validators
        |
        v
local coding model
        |
        | structured request
        v
source-grounding gate
        |
        v
isolated candidate executor
        |
        +---- no direct source promotion
        +---- no fuzzy semantic repair
        +---- observed effect/path set
        |
        v
independent validation
        |
        +---- fail -> durable escalation
        |
        v
AWAITING_OPERATOR_REVIEW
```

The model proposes. The machinery constrains and checks. The human decides whether anything becomes real.

## What the experiments taught me

One of the most useful findings was that **semantic understanding and operational reliability are different problems**.

A model can understand exactly what a change should accomplish and still fail because it serialized a bad unified diff. It can produce parser-valid output while selecting source text that does not exist. It can make a plausible code change that fails the actual validator. It can reason correctly and still loop procedurally.

Those are not all the same failure, and treating them as “the AI got it wrong” throws away useful information.

The project evolved specifically because the evidence kept separating those failure classes.

### Patch syntax was hiding useful reasoning

The practical Qwen2.5-Coder 14B worker repeatedly demonstrated the correct semantic edit while producing malformed patch envelopes. Preserved rejected patches could often become `git apply` compatible through mechanical corrections without changing the intended code.

That was an important clue: **the interface itself was measuring diff-serialization skill along with coding skill.**

So the project did not silently repair the historical outputs and declare victory. It preserved the failures, characterized them, and built a new candidate transport.

### Structured edits removed one class of failure

The V3 `PROPOSE_TEXT_REPLACEMENT` interface stopped asking the model to manufacture unified-diff grammar. Instead, the model owns:

- the authorized path;
- the exact old text; and
- the exact replacement text.

The executor owns exact-match counting, candidate construction, effect observation, and review-diff generation.

That deliberately narrows the model's job instead of teaching the evaluator to forgive bad output.

### Then source alignment became visible

Once diff serialization was removed, another problem surfaced: a model could request replacement of text that was not actually present in the current source.

That produced the next rule: **an existing-file edit must be grounded by a successful same-session read of that exact path before execution.**

An ungrounded write gets `SOURCE_READ_REQUIRED`, not a helpful leak of the source and not a guess from the executor.

That rule changed the behavior materially. In a fresh run, the 14B worker was first denied, then read the exact file, then selected the actual existing text and produced a candidate that passed both validators.

That combination became the frozen source-grounded V3 production envelope.

## Real repository work: passes and failures both count

The project eventually moved beyond synthetic fixtures into real local repositories.

The results were deliberately mixed:

- one preserved pilot was infrastructure-blocked because the validation apparatus selected the wrong descriptor;
- after the apparatus was repaired, the preserved candidate failed validation;
- a fresh independent pilot also produced a candidate that failed its visible validator;
- a separate real mid-file task in `gpu-compute/CURRENT_STATE.md` produced a bounded 52-byte edit candidate that passed both validators and ended at `AWAITING_OPERATOR_REVIEW`;
- a real Python-code task in `ws-doc-writer` produced a plausible but semantically incomplete solution and correctly failed validation.

That mix is one of the strongest parts of the project.

I did not want a demo where every test was designed to make the model look good. I wanted a system that could say **no** accurately enough that a pass would mean something.

## Model roles, not a magic winner

Several exact model/runtime combinations were characterized under the harness.

### Qwen2.5-Coder 14B — practical interactive baseline

The 14B Q4 model became the practical `INTERACTIVE_PRACTICAL_CODER` baseline on Katra. The accepted runtime profile fit entirely on the RTX 5070 Ti at the frozen comparison context.

Its strengths were useful coding intent, bounded source work, and eventually successful source-grounded structured edits. Its weaknesses included representation/patch-construction problems and real cases where technically plausible code still failed validation.

That is why its accepted role remains bounded rather than magically becoming “autonomous developer.”

### Qwen2.5-Coder 32B — deliberative scale control

The 32B Q4 model was retained as a `DELIBERATIVE_OVERNIGHT_CODER` / scale-control role. On the same Katra appliance it required partial CPU offload but produced cleaner protocol behavior in the frozen comparison and eventually a preserved candidate that passed later-added independent validators.

It was not automatically promoted over the 14B worker simply because it was bigger.

### Qwen3-Coder 30B, Devstral, and gpt-oss

Other candidates exposed different failure modes:

- Qwen3-Coder 30B demonstrated useful bounded capabilities but failed the required production-admission behaviors;
- Devstral passed some earlier gates but hit a terminal model repeat limit during write work;
- `gpt-oss-20b-mxfp4` resolved runtime compatibility but could not participate in the exact frozen 4096-context comparison because its minimum context requirement was larger.

Those distinctions are preserved on purpose. **“Did not qualify for this lane” is not the same claim as “bad model.”**

## Current state in plain English

Alpha v1 is frozen as historical evidence and the executor/harness is qualified for model evaluation.

The most useful current practical result is the source-grounded V3 path:

```text
bounded task
    -> source must be read in-session
    -> exact text replacement only
    -> isolated candidate
    -> independent visible/hidden validation
    -> AWAITING_OPERATOR_REVIEW
```

The frozen V3 production envelope does **not** grant general autonomous production use. Real-repository pilot evidence includes both a successful bounded mid-file edit and failures on other tasks. The correct conclusion is therefore narrow: the mechanism can produce valid supervised candidates under demonstrated conditions, and it can also stop or escalate when those conditions are not met.

That is enough to be useful without pretending the research is finished.

For the exact historical task sequence, protocol versions, frozen dispositions, model artifacts, and forward-only supplemental findings, see [ORIGINAL-README.md](ORIGINAL-README.md). I preserved it because the long chronology is the evidence trail, not clutter to erase once a cleaner summary exists.

## This is an agentic training surface

`ws-code-agent` is one of the clearest places where the Helix-ARPA self-taught curriculum becomes explicitly agentic.

I use the control-plane repositories as structured working areas where agents can learn the shape of a domain: ownership, current intent, evidence, allowed effects, validation, and stop conditions. This repository turns that idea inward and asks the same questions about the coding agent itself.

```text
model can answer questions
      -> model can use tools
      -> model can inspect source
      -> model can recognize missing information
      -> model can propose a bounded effect
      -> effect can be represented safely
      -> source can be proven current
      -> candidate can be isolated
      -> machine validators can judge the result
      -> failure can escalate without looping
      -> human review remains the promotion boundary
```

I call this a training surface because the work is meant to teach both sides of the system:

- **the models**, through deliberately constrained interfaces and repeatable tasks; and
- **me**, by forcing vague ideas like “safe agent” or “good coding model” into observable behavior I can actually test.

This is not necessarily “training” in the narrow sense of changing model weights. Much of the value comes from designing the protocol, tools, context, validators, authority model, and workload so that useful behavior can be distinguished from merely convincing output.

That lesson carries directly into the broader Helix-ARPA path toward governed automation. Agents can inspect, reason, draft, compare, and produce bounded candidates; mature deterministic procedures move toward `ansible-cp` and Semaphore rather than giving the model increasingly broad shell authority.

## Why I built it this way

The temptation with local models is to celebrate the first impressive result and expand authority from there.

I wanted to do the opposite.

Every time the model surprised me positively, I tried to ask what **smallest claim** the evidence actually supported. Every time it failed, I tried to determine whether the failure belonged to reasoning, representation, source state, the executor, the validator, or the experiment itself.

That process is slower than “it wrote code, ship it,” but it produces something I can reason about.

The project also taught me that a safety boundary can improve the experiment rather than merely restricting it. When a model cannot silently patch the source, repair its own malformed output, or grade itself, its strengths and weaknesses become much easier to see.

## Relationship to the rest of Helix-ARPA

`ws-code-agent` has deliberately narrow application authority.

- `ws-doc-writer` is a separate document-writing application and lineage source, not something this agent silently absorbed;
- `ws-cp` owns workstation and local Ollama service mechanics;
- GPU/runtime ownership belongs to the relevant GPU/compute control planes;
- source repositories retain their own authority;
- reading, testing, or proposing a candidate grants no right to promote it.

If peer authorities disagree, the work stops and returns to the operator.

That is the same `*-cp` philosophy used across hypervisors, networking, storage, compute, identity, and automation: **make ownership explicit before making action easy.**

## Where to go next

- [foundation contract](docs/contracts/CODING_AGENT_FOUNDATION_CONTRACT.md) — the governing architecture;
- [supervised single-repository work](docs/work/supervised-single-repo.md) — the operator-gated lane;
- `docs/qualification/` — artifact-bound model qualification statements;
- `benchmarks/` — repeatable calibration and test cases;
- `src/` — bounded executor, harness, protocol, and experiment controller;
- `tests/` — deterministic and containment-oriented regression coverage;
- `validation-assets/` — independent validation material;
- `lineage/` — preserved Doc Writer lineage without inherited authority;
- [ORIGINAL-README.md](ORIGINAL-README.md) — the detailed Task 10/11 research chronology.

## Engineering focus

**Local LLMs · agentic systems · bounded authority · source grounding · structured tool protocols · isolated code mutation · deterministic validation · model evaluation · Ollama · GPU inference · Python · Git · escalation policy · human-in-the-loop systems**

In plain language: I am not trying to teach a model to be trusted. I am trying to build a system where **trust is never the only thing standing between a model and the source tree**.