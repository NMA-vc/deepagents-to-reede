# From an existing LangGraph agent to a verified receipt in under ten minutes

A small [Deep Agents](https://github.com/langchain-ai/deepagents) agent (LangChain `deepagents`,
built on LangGraph) wired to [Reede](https://github.com/NMA-vc/reede). It runs on a scripted
fake model, so it needs **no API key and makes no network model call**. Reede seals every span
the agent emits into a signed, hash-chained receipt that you verify offline.

What you get is a **reported** receipt: it proves what the agent reported and when this machine
sealed it. It does not prove the report is true, and it carries no trusted timestamp (signed, not
timestamped). A hosted Reede path is coming; this is the local, open-source flow.

Repository: <https://github.com/NMA-vc/deepagents-to-reede>. The one helper it uses,
[`reede-otel`](https://github.com/NMA-vc/reede-otel), is installed from GitHub (not on PyPI yet).

## Steps

Needs Python 3.10+ and a Rust toolchain (for step 1 only).

**1. Install reede** (one-off compile; the crate is not on crates.io yet):

```text
cargo install --git https://github.com/NMA-vc/reede --features ingest
```

Once published, `cargo install reede --features ingest` does the same.

**2. Get the example and its pinned dependencies:**

```text
git clone https://github.com/NMA-vc/deepagents-to-reede && cd deepagents-to-reede
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
```

**3. Start the receipt server** (own terminal; OTLP/HTTP on 127.0.0.1:4318):

```text
reede serve --out ./ingest
```

**4. Run the agent.** `agent.py` starts with `reede_otel.configure()`, which sets the env vars
below. They must be set *before* langchain/langgraph are imported, so set them yourself if you
wire your own agent without the helper:

| Variable | Value |
|---|---|
| `LANGSMITH_TRACING` | `true` |
| `LANGSMITH_TRACING_MODE` | `otel` (older SDKs: `LANGSMITH_OTEL_ENABLED=true`, `LANGSMITH_OTEL_ONLY=true`) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://127.0.0.1:4318` (base URL; `/v1/traces` is appended) |
| `OTEL_EXPORTER_OTLP_HEADERS` | any non-empty `k=v`, so LangSmith adds no `x-api-key` header |

```text
python agent.py
```

`LANGSMITH_TRACING_MODE=otel` exports over OTLP only; nothing is sent to LangSmith. The
`reede serve` terminal prints `sealed receipts seq 1..N`.

**5. Check the sealed spans against their receipts:**

```text
reede ingest check --out ./ingest --pubkey "$(cat ingest/pubkey.hex)"
```

**6. Verify the chain offline:**

```text
reede receipt verify --chain ingest/chain.json --pubkey "$(cat ingest/pubkey.hex)"
```

Expected ending:

```text
CHAIN:      VERIFIED
SIGNATURES: VERIFIED
HASH:       VERIFIED
TIMESTAMP:  ABSENT
VERDICT:    SIGNED, NOT TIMESTAMPED (authentic; not fully qualified evidence)
```

## What the verdict means

- **CHAIN / SIGNATURES / HASH verified**: no receipt was altered, removed from the middle or
  reordered, and each was signed by the key you pinned.
- **TIMESTAMP ABSENT**: nothing independent vouches for *when*. Whoever runs `reede serve` holds
  the signing key and could seal anything. Pinning `pubkey.hex` from the same directory, as here,
  only shows the form; a real verifier pins a key obtained separately.
- **Not proven**: that the agent's report is true.
- **Privacy**: spans carry `gen_ai.prompt` / `gen_ai.completion` in clear and are stored
  unredacted in `ingest/spans/`. Keep that directory as private as the data. Never commit
  `ingest/signing.key`.

`./run.sh` does steps 2 to 6 in a scratch directory (set `REEDE_BIN` if `reede` is not on PATH;
`REEDE_PORT` if 4318 is taken).

## Optional: a real model

Any OpenAI-compatible endpoint works; use the one you already run or trust.

```text
pip install langchain-openai
export REEDE_EXAMPLE_BASE_URL=<your OpenAI-compatible base URL>
export REEDE_EXAMPLE_API_KEY=<key>
export REEDE_EXAMPLE_MODEL=<model id>
python agent.py
```

Not run in CI; the fake-model path above is what was timed. Real prompts and completions
will be sealed into `ingest/spans/` in clear.

## Versions

Run against Python 3.14, `deepagents` 0.7.41, `langgraph` 1.2.24, `langsmith` 0.16.0,
`opentelemetry-*` 1.45.2 (pinned in `requirements.txt`).

Apache-2.0.
