# Installing IronBark

IronBark is a single standard-library Python file. There is nothing to build,
nothing to migrate and nothing to seed: the reference tables are literals
inside `ironbark.py`, so a checkout runs immediately.

## Prerequisites

| Requirement | Notes |
| --- | --- |
| Python 3.9 or newer | `python3 --version`. The system interpreter is fine. |
| A terminal | Any POSIX shell, PowerShell or cmd; output is plain UTF-8 text. |

No system packages, no compiler, no database server, no network access.

## 1. Install (optional)

You do **not** need this step to use IronBark — `python3 ironbark.py heat 780`
works from a bare checkout. Run it if you want the `ironbark` command on your
PATH and the test suite installed:

```bash
bash install.sh
```

It upgrades pip/setuptools/wheel, installs the one declared dev dependency
(`pytest`, pinned in `requirements.txt`), installs the project in editable mode
for the `ironbark` console command, runs a self-check, runs the test suite and
then **exits**. It never starts a long-running process, never uses `sudo`, and
never installs a system package. Re-running it is safe and idempotent.

## 2. Configure

Nothing. IronBark reads no environment variables, makes no network calls and
writes no files. There is no config file, cache, history or database to create.

## 3. Run

```bash
python3 ironbark.py --help
python3 ironbark.py heat 780
python3 ironbark.py quench 1084
python3 ironbark.py strike knife-blank
```

If you ran step 1, the same commands are available as:

```bash
ironbark heat 780
```

Full non-interactive walkthrough (the recommended first run):

```bash
bash demo.sh
```

## 4. Test

```bash
python3 -m pytest
```

51 tests, no network, no fixtures to download.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `SyntaxError` on start | Python older than 3.9. Check `python3 --version`. |
| Garbled `°` or box-drawing characters | A non-UTF-8 terminal. IronBark sets its output streams to UTF-8; if the terminal still garbles, run `LC_ALL=C.UTF-8 python3 ironbark.py heat 780` or pipe to a file. |
| `error: unrecognized arguments` | An extra word after the value. Quote multi-word names: `ironbark quench "1084 steel"`, or write them without the space (`10xx`). |
| Exit code 2 with a range line | The temperature is not a number or sits outside 200–1400 °C. |
| Exit code 1 with near matches | The alloy or billet is not in the table; the near matches suggest the closest records. |
| `ironbark: command not found` | Step 1 was skipped, or its `bin` directory is not on PATH. Use `python3 ironbark.py ...` instead. |
