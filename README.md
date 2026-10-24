# Safety Shift Navigator

**A source-checked, human-owned operations handoff prototype powered by NVIDIA Nemotron on Nebius Token Factory.**

This independent hackathon candidate converts incomplete *fictional* shift observations into a structured handoff that cites the exact source and runbook IDs, identifies what is still unverified, and asks a qualified human which original record to inspect.

**Evidence scope:** One authenticated request from the original local application to Nebius Token Factory **passed** the independent source critic on 2026-10-24. The public-facing static replay (when hosted) is separate from this authenticated inference and never contains a provider key. No statistical accuracy, award, physical safety outcome, or final Devpost acceptance is claimed.

## The five-step agent

1. **Source validation:** rejects malformed, changed, or instruction-bearing fictional observations.
2. **Runbook retrieval:** attaches a separately written fictional runbook with a distinct ID.
3. **Nemotron model:** an optional authenticated call to `nvidia/Nemotron-3_5-Lightning` at `https://api.tokenfactory.nebius.com/v1/chat/completions`.
4. **Independent critic:** validates seven-field JSON, original signal/runbook citations, exact missing-record disclosure, a source-seeking human question, and prohibition on unsupported machine instructions.
5. **Human handoff:** presents the evidence and unanswered questions. No external equipment, dispatch, emergency system or billing action is available.

The app defaults to a deterministic **SYNTHETIC_OFFLINE_MOCK**. This replay is not real model inference.

## Requirements

- Python 3.11+ (the private evaluation used Python 3.14.3).
- Modern desktop/mobile browser.
- For optional live inference only: your own authorized project-scoped Nebius Token Factory API key and explicit no-cash-overage review. Never put credentials in source, browser JavaScript, CLI args, public demonstration videos or Devpost text.
- No Python third-party dependencies; all fixtures are fictional.

## Run offline

```bash
python3 -m src.webapp --port 8878
```

Open `http://127.0.0.1:8878/`. Select an original scenario and click **Prepare reviewed handoff**. The UI distinguishes offline replay from genuine Token Factory inference and refuses real calls unless a separate configured gate is enabled.

Run tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -W error -m unittest discover -s tests -q
```

The isolated Python suite passed 80 local checks, including 10 adversarial provider-envelope cases. Re-run on this release tree. Offline tests are not model reliability evidence; the separate single real application call and three observed Playground tests are reported under distinct evidence tiers.

## Live inference contract (optional, after approval)

The adapter expects `NEBIUS_API_KEY` and `NEBIUS_SANDBOX_ZERO_SPEND_APPROVED=YES` in a **private server process**, never in the browser. This flag is a local technical gate **not** a server-side budget cap. Verify your actual credit balance, account auto-payment behavior and cost controls independently before enabling it.

The runtime makes at most one authenticated request per handoff, with `max_tokens=4096`, `temperature=0`, a strict seven-field JSON schema and no silent fallback. An accepted real receipt must report HTTP 200, exactly the expected Nemotron model, finalized output and consistent token usage, and pass the independent original-source Critic. Any failure is an explicit abstention.

## Evidence tiers

- **Local deterministic:** validates the three synthetic scenes, five stages and fail-closed browser result display.
- **Real first-party Nebius Playground:** separate private testing yielded three source-critic-accepted outcomes on three known fictional scenarios; this is not a measured reliability rate.
- **Application-authenticated Token Factory:** VERIFIED for **one** bounded fictional `handoff-airflow` request, HTTP 200, exact Nemotron model ID, completed `stop` response, 504 input and 1,959 output tokens, followed by independent semantic Critic PASS. Redacted, non-provider-signed local receipt: [`evidence/NEBIUS_G1_REAL_APP_RECEIPT_REDACTED.json`](evidence/NEBIUS_G1_REAL_APP_RECEIPT_REDACTED.json). This is **not** a reliability rate or a provider-issued signed certificate; public judge hosting is a separate requirement.
- **Real operational impact:** not measured. No production safety claims.

## Privacy / security

- Original synthetic data only; no real personnel, customer, equipment or financial records.
- Denies prompt injection and unknown evidence IDs; human approval is compulsory.
- Local server binds to 127.0.0.1 by default. **Do not expose this local server directly to the Internet.** Any publicly hosted judge copy needs its own reviewed HTTPS, Host/Origin, rate limit and credential-budget boundary.
- Secret-safe response envelopes do not expose token contents.
- No model access, vendor relationship, sponsorship endorsement, certification or machine actuation is implied by naming Nebius and NVIDIA.

## Public release and attribution

The original source history, internal billing notes and private governance ledger are deliberately not included in this standalone contest package. **No license rights are granted by `LICENSE.PROPOSED`.** A distribution license applies only if an authorized, verified rights holder explicitly adds the matching top-level `LICENSE` and publishes the approved clean-room source tree. The prototype is not a production safety system.

For review, use the redacted G1 receipt and reproducible source/fixtures. The private governance ledger, full vendor account history and API keys are intentionally excluded. No fabricated user outcomes, awards or predicted win rate.
