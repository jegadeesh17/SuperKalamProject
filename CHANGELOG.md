# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/).
Entries are built from the repository's own commit subjects. No version has been released yet.

## [Unreleased]

### Added

- Evaluator calibration benchmark script and report, Pydantic settings and an agent test suite (`58c2f42`).
- Standard `/app` route for the web UI and a GitHub Actions workflow that deploys to Google Cloud Run (`782bf3b`).
- Favicon matching the app logo (`b9ff1d4`).
- Mock test platform redesign with a timer and an expanded knowledge base of PYQs (`191e0cd`).
- Support for the Groq API, graceful handling of unknown PYQs and fallbacks for API rate limits (`2f5144c`).
- Initial project setup of the agentic answer evaluator (`94a390c`).

### Changed

- Documentation refresh: standard README section order, `docs/README.md` index, this changelog, `docs/DECISIONS.md`, MIT `LICENSE`, commented `.env.example`, corrected `docs/SPEC.md` (retry behaviour, full route table, dangling reference) and wider `.gitignore`. No code changed.

### Fixed

- Evaluator output is validated with a Pydantic model, the Docker health check follows the runtime `PORT`, and the missing spec document was added (`c5ff69d`).
- Replaced the retired Groq model with `openai/gpt-oss-120b` and capped hidden reasoning tokens (`db271f3`).
- PYQ data is seeded at image build time and a missing LLM key is reported clearly (`c7a434d`).
- Added the missing `pydantic-settings` requirement and fixed the health check port (`aeefbcd`).
- Added `PYTHONPATH=/app`, a `sys.path` insert, a port fallback and a `.dockerignore` for the container (`dd25d90`).
- Removed the reserved `PORT` variable from the Cloud Run deploy workflow (`c4af70b`).
