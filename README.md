# Universal Log RCA

A universal, LLM-native log ingestion and root cause analysis system.
Ingests logs of any format from any domain. Produces structured,
evidence-grounded post-mortems with confidence scores and citations.

## Quick Start

Open `universal_log_rca_runbook.ipynb` in Google Colab.
Run cells top to bottom. Everything is created automatically.

## Requirements

- Google account (for Colab + Drive)
- Groq API key (free at console.groq.com) for cloud mode
- OR Ollama installed locally for fully-local mode

## Architecture

See `docs/architecture.md` (added in Phase 3).

## Phases

| Phase | Description |
|-------|-------------|
| 1 ✅ | Scaffold: Drive, config, schema, checkpoints |
| 2 🔒 | Ingestion + Statistical Filter |
| 3 🔒 | LLM Parsing Pipeline |
| 4 🔒 | Multi-Source Resolution |
| 5 🔒 | Reasoning Layer |
| 6 🔒 | End to End + UI |

## Data Governance

Raw log content is **never stored**. Only a SHA256 hash is kept
for audit trail purposes. PII is detected and stripped before
any vectorization or LLM call.

## License

MIT
