
# LangGraph Examples: Setup & Usage

This directory contains examples and demos using [LangGraph](https://github.com/langchain-ai/langgraph). The recommended way to set up your environment is with the [uv](https://github.com/astral-sh/uv) package manager for fast, reproducible Python environments.

---

## 1. Install `uv` (Recommended)

`uv` is a super-fast Python package manager and environment tool. It works on all major operating systems (Windows, macOS, Linux).


### Install with pip or pipx
- Open your terminal (**Windows:** Command Prompt or PowerShell as Administrator)
- Run:
  ```bash
  pip install uv
  # or, if you have pipx:
  pipx install uv
  ```
- For the latest install methods, see the [Astral uv site](https://github.com/astral-sh/uv#installation).

---

## 2. Sync Your Environment (No Manual venv Needed)

`uv sync` will automatically create a virtual environment (if one doesn't exist) and install all dependencies from `requirements.txt` or `pyproject.toml`.

- To set up the environment for the whole repo:
  ```bash
  uv sync
  ```
---

## 3. Adding More Packages

- To add a new package (e.g., `requests`) to your environment and requirements:
  ```bash
  uv add requests
  ```

---

## 4. Environment Variables

- Copy `.env.example` to `.env` and fill in your secrets (e.g., API keys):
  ```bash
  cp .env.example .env
  # On Windows (Command Prompt):
  copy .env.example .env
  ```
- Edit `.env` and add your values as needed.

---

## 5. Running Examples

- After syncing, check the README in any Level folder (e.g., `Level3/README.md`) for specific instructions and try out the code:
  ```bash
  cd Level3
  # See README.md for details
  python tool_as_node.py
  ```

---

## 6. Notes for Windows Users
- `uv sync` and `uv add` work natively on Windows.
- If you get execution policy errors in PowerShell, run:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
- If you have both Python 2 and 3, use `python3` instead of `python`.

---

## 7. More about `uv`
- [uv documentation](https://github.com/astral-sh/uv)
- `uv` is a drop-in replacement for pip, pip-tools, and virtualenv, but much faster.

---

## 8. Troubleshooting
- If you have issues with `uv`, try upgrading:
  ```bash
  pip install --upgrade uv
  ```
- If you get missing package errors, check the correct requirements file for the example you are running.

---

Happy experimenting with LangGraph!
