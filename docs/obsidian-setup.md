# Obsidian Setup

Obsidian is the recommended human-facing frontend for this capstone.

We can recommend it directly to students because it is free and the onboarding
cost is low.

If you prefer, the capstone still works with any editor or file browser.

Why:

- the vault is just files on disk;
- you can inspect `raw`, `wiki`, and `outputs` without extra product work;
- this matches the `LLM Knowledge Bases` workflow well.

## Install

Use the official download page:

- [Obsidian Download](https://obsidian.md/download)

Official docs on vaults:

- [Obsidian Help: Vault](https://obsidian.md/help/vault)

## Open The Vault

1. Install Obsidian.
2. Choose `Open folder as vault`.
3. Select the `vault/` folder inside your local clone of this repository.

After that, you should see:

- `index.md` as the vault entrypoint
- `log.md` as the run log
- `raw/` for source documents
- `wiki/` for compiled knowledge pages
- `outputs/` for generated answers and artifacts

## Recommended First Run

1. From the repo root, run:

```bash
just demo
```

2. In Obsidian, open:

- `index.md`
- `log.md`
- `wiki/index.md`
- the latest file in `outputs/`

This gives you the intended capstone loop immediately:

- source files on disk
- a stable entrypoint and run log
- compiled wiki page
- grounded output file
- all visible in one vault

## Scope Reminder

For this capstone, Obsidian is a frontend for browsing the vault.

It is **not** the main subject of the course.

We are not building an Obsidian plugin or a generic PKM platform.
