# Safety Shift Navigator

**An evidence-to-decision handoff agent using NVIDIA Nemotron via Nebius Token Factory, with independent source checking and human-owned review.**

**Track:** Nebius × NVIDIA Global AI Hackathon / Best Apps and Agents
**Stage:** SUBMITTED_ACKNOWLEDGED on 2026-10-24 JST (Devpost #1259397). Public original MIT-licensed repository and synthetic offline judge demonstration; one separate historical authenticated Nemotron call. Winning or real-world impact has NOT been verified.

## Judge quick start (public, no credentials)

- [Open the public judge demo](https://mrshamann.github.io/safety-shift-navigator-nebius/). It is a **fictional offline source-reconciliation replay**, not a live Nebius model call and not equipment control.
- [Watch the public 144-second demo](https://youtu.be/_jh9vn1ei7o).
- [Inspect the separately authenticated one-call Nemotron evidence](evidence/NEBIUS_G1_REAL_APP_RECEIPT_REDACTED.json) and [run the local unit tests](#try-it-locally-offline-and-free). The historical real call used `nvidia/Nemotron-3_5-Lightning` through Nebius Token Factory; no real live model request is made by the static judge page.
- [Official submitted Devpost project](https://devpost.com/software/safety-shift-navigator) — organizer confirmation received 2026-10-24 JST. No award or outside-user validation claimed.

## Why this exists

A shift handoff should not merely sound confident; it must tell the incoming reviewer which original record is missing and what to verify next. UK HSE guidance identifies weak shift-handover communication and incomplete information as a serious human-factors risk: https://www.hse.gov.uk/humanfactors/topics/shift-handover.htm. The guide does not endorse or validate this prototype.

The key difference from a generic incident summarizer is the **second evidence event**. When a new source appears, the handoff is checked again against its original asset and signal, not quietly treated as solved. A human then must choose what record to inspect or who should review the conflict.

## Try it locally, offline and free

Requires Python 3.11+ standard library, plus a modern browser. No paid infrastructure or new API key is necessary to try the synthetic demo.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -W error -m unittest discover -s tests -q
python3 tools/judge_evidence_benchmark.py
python3 -m src.webapp --port 8878
```

Open `http://127.0.0.1:8878/`.

1. Choose one of three **invented** airflow/access/network handoff incidents.
2. Run the five-stage bounded source and runbook handoff. Offline review is explicitly labeled **SYNTHETIC REPLAY / NO NEBIUS**.
3. Select a subsequently revealed fictional archive record: partial corroboration, conflicting monitor status, or unrelated material.
4. Inspect the **source delta** (before/after, original-vs-new asset/signal, unresolved record, human source question, evidence ID and SHA).
5. Choose a permitted, **human-only** record-verification action. The page produces a local browser SHA-256 integrity receipt. A changed record invalidates the previous choice. This receipt is not a verified staff identity, legal signature, equipment authorization or production incident closure.

The old one-pass severity sorting baseline is under a collapsed optional reference section. No machinery, emergency system, remote device or payment account is connected.

## Five-stage model adapter

The standalone Python application contains a guarded official Nebius Token Factory chat-completions adapter using the exact NVIDIA `nvidia/Nemotron-3_5-Lightning` model. It has source packet hash checking, runbook retrieval, strict seven-field JSON schema, a separate fail-closed original-source Critic v2, and mandatory human handoff. Both real and offline workflows preserve provenance.

**Model evidence, kept in separate tiers:**

- **One genuine, authorized authenticated application-originated inference**, returned HTTP 200, exact model, completed answer, 504 input plus 1,959 output tokens, independently accepted by the Critic version active at that time. The one-use key was revoked. Redacted local receipt: [G1 run](evidence/NEBIUS_G1_REAL_APP_RECEIPT_REDACTED.json). It is a local redacted receipt, not a vendor-signed certificate.
- **Three known real Nebius Playground fictional scenarios** separately passed source checking after iterative fixes; earlier failed provider outputs are not hidden. Two saved Playground reviews also passed the later more-specific Critic v2. This is not general model accuracy.
- **97/97 local Python/security tests**, including source-specific critic falsification and synthetic provenance/HTTP safeguards. Source-contrast evaluation covers 9 *authored* counterfactual cases, 3 each corroborating, conflicting or irrelevant. The cases are not held out.
- **36/36 actual desktop/mobile browser human-decision interactions** passed across the original local Python app and the byte-identical static judge candidate (1440px and 390px). **12/12 separate citation inspection interactions** confirm each source ID opens its original fictional observation, Runbook, checks and integrity marker. Neither result is a user benefit study or a measure of real Nemotron reliability.

The free `docs/` judge preview is generated by `tools/build_judge_site.py`, serves offline synthetic source and review records, and never uses Nebius credentials. A clickable static preview is **not** fresh model inference. Public-hosted live inference would require a separate private provider key and independently enforced billing/abuse controls; an environment flag alone is **not** a cost cap.

## Security and limitations

- Original synthetic data only; no real people, customer records or telemetry.
- Incorrect provider model ID, reasoning-only/truncated completion, missing usage metadata, fabricated citations or unsupported machine instructions cause fail-closed abstention.
- Independent Critic v2 requires specific missing source and record-seeking questions, not fluent generic guesses.
- External equipment connections, automatic dispatch and incident approval: **none**.
- Neither operational impact nor general-model reliability has been measured; there is no claim of reduced accidents, faster handoff or award probability.

## Publication and legal rights

The independent contest source is already publicly available under the **effective MIT LICENSE** (Copyright 2026 Jin Yang), and its public GitHub Pages demo is an explicit **offline fictional replay**. The YouTube demonstration and Devpost project were submitted and acknowledged on 2026-10-24 JST. A single historical authenticated Nebius/NVIDIA Nemotron application inference is evidenced separately; public demo interactions do **not** make fresh provider calls. No award or impact benefit is established. No private venture source, API credentials, model weights or operational data were published.
