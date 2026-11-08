# Using ironbark

## Overview

Blacksmith shop reference: heat colour by temperature, quench medium per alloy, hammer strike order per billet.

## Quickstart

```bash
ironbark --help
# or, if installed from source without symlink:
python -m ironbark --help
```

## Commands

This CLI exposes **3** subcommands. Each was extracted from the source.

| Command | Source file |
|---------|-------------|
| `ironbark heat` | `ironbark.py` |
| `ironbark quench` | `ironbark.py` |
| `ironbark strike` | `ironbark.py` |

### Per-command help

```bash
ironbark --help                # top-level help
ironbark heat --help    # help for `heat`
```

## Worked example

1. Verify the CLI is on your PATH: `which ironbark` (or run via `cargo run --`/`python -m`).
2. Show all subcommands: `ironbark --help`.
3. Try the first detected subcommand:

```bash
ironbark heat --help
```

## Reference

### Entry points

| Kind | Name | Source |
|------|------|--------|
| Console script | `ironbark` | `ironbark:run_cli` (pyproject.toml) |

### Surface index (auto-extracted)

| Kind | Title | Source file |
|------|-------|-------------|
| command | `heat` | `ironbark.py` |
| command | `quench` | `ironbark.py` |
| command | `strike` | `ironbark.py` |

## Next steps

- Read [INSTALL.md](./INSTALL.md) if anything in the Quickstart didn't work.
- Inspect `.env.example` for the full list of environment variables this project understands.
- See [README.md](./README.md) for the architecture diagram + feature list.
