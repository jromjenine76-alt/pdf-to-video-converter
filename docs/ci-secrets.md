# CI secrets expectations

This repository has both optional and required secret usage in workflows.

## Optional secret

- `OPENAI_API_KEY` in `.github/workflows/spellcraft-key-check.yml` is **optional**.
- The key-check workflow is informational. If the secret is missing, it emits a warning and still passes.

## Required secret

- `OPENAI_API_KEY` in `.github/workflows/spellcraft-voice-fingerprint.yml` is **required** for voice candidate generation.
- If the secret is missing (or the key cannot make API calls), that workflow can fail.

## Trigger/consistency expectations

- `spellcraft-key-check.yml` should run on all pushes, pull requests, and manual dispatch without restrictive path filters.
- Workflow linting in `.github/workflows/workflow-validation.yml` is used to catch workflow syntax/config regressions early.
