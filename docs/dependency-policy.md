# Dependency Policy

## Goal

The capstone should test agent engineering skill, not the student's ability to
purchase and configure multiple third-party data subscriptions.

## Core Path

The required student path should work with:

- Python `3.11`
- `uv`
- `just`
- local fixtures
- deterministic smoke tests

The default live LLM path for later milestones should use:

- `OPENAI_API_KEY`

This path must remain enough to:

- run the demo;
- complete core milestones;
- pass local tests;
- understand the architecture.

Current note:

- `M0` is fully local and does not require `OPENAI_API_KEY` yet.

## Search And Social Policy

### Required

- local fixture-backed source discovery
- manual URL input

### Optional Recommended

- `Brave Search API` as a live web-search adapter

Why it is only optional:

- it adds billing and quota setup;
- it creates support surface around rate limits and provider churn;
- core milestones should not depend on fresh web results.

### Stretch Only

- `X API`

Why it is not part of the core path:

- higher access volatility;
- extra auth and credit-management complexity;
- too much student effort shifts from agent architecture to platform setup.

## Architecture Rule

The repository should teach interfaces, not vendor lock-in.

Recommended shape:

- `SourceDiscovery`
  - `fixtures`
  - `manual_urls`
  - optional `brave_search`
- `Fetcher`
- `Normalizer`
- later optional `SocialSource`

## Student Contract

Students should be able to complete the capstone without:

- Brave billing
- X credits
- social-platform app approval

Optional live integrations should feel like product extensions, not a paywall.
