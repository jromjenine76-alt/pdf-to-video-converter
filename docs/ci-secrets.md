# CI secrets expectations

This repository has both optional and required secret usage in workflows.

## Optional secret

- `OPENAI_API_KEY` in `.github/workflows/spellcraft-key-check.yml` is optional.
- The key-check workflow is informational. If the secret is missing, it emits a warning and still passes.
- `OPENAI_API_KEY` in `.github/workflows/spellcraft-marin-storytelling.yml` is also optional.
- The Marin storytelling workflow warns and skips narration generation when the secret is missing or billing is inactive.

## Required secret

- `OPENAI_API_KEY` in `.github/workflows/spellcraft-voice-fingerprint.yml` is required for voice candidate generation.
- If the secret is missing, or the key cannot make API calls, that workflow can fail.

## Trigger expectations

- `spellcraft-key-check.yml` runs on all pushes, pull requests, and manual dispatch without restrictive path filters.
- `workflow-validation.yml` runs on pull requests and main-branch pushes that touch `.github/workflows/**`, plus manual dispatch.
