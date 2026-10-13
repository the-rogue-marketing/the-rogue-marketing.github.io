---
layout: post
title: "uv for AI Engineers: Fast, Reproducible Python Environments for LLM and Agent Projects"
description: "How to use Astral's uv to manage Python versions, dependencies, lockfiles and Docker builds for AI applications, with commands you can copy."
date: 2026-10-13 09:00:00 +0000
author: naila-iqbal
image: assets/images/python-uv-ai-projects-2026.webp
categories:
  - Developer Engineering & Tools
tags:
  - Python
  - DevOps
  - AI Agents
  - PydanticAI
keywords: "uv python package manager, uv vs pip, uv lock file, uv docker, python environment ai projects, astral uv tutorial"
faqs:
  - question: "What is uv?"
    answer: "uv is a Python package and project manager from Astral, written in Rust. It replaces pip, pip-tools, virtualenv and pyenv workflows with a single fast tool."
  - question: "Does uv work with existing requirements.txt files?"
    answer: "Yes. You can run uv pip install -r requirements.txt, or import the dependencies into a pyproject.toml managed project with uv add -r requirements.txt."
  - question: "Should I commit uv.lock?"
    answer: "Yes for applications. The lockfile pins exact versions across platforms so every developer, CI job and container installs the same dependency set."
---

AI projects have heavy, fast-moving dependency trees: model SDKs, PydanticAI, vector database clients, tokenizers, and sometimes CUDA-specific wheels. Slow installs and environments that differ between machines waste hours.

**uv**, built by Astral in Rust, has become the default choice for many Python teams because it resolves and installs packages far faster than pip and gives you a lockfile out of the box.

---

## 1. Start a Project

```bash
# Install uv (macOS / Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a project with a pinned Python version
uv init support-agent
cd support-agent
uv python pin 3.12

# Add dependencies
uv add pydantic-ai httpx
uv add --dev pytest ruff
```

`uv add` updates `pyproject.toml`, resolves versions, writes `uv.lock`, and syncs the `.venv` in one step.

---

## 2. Run Without Activating Anything

```bash
uv run python -m support_agent
uv run pytest -q
```

`uv run` makes sure the environment matches the lockfile before it executes the command, so it cannot drift silently.

---

## 3. Reproducible Installs in CI

```bash
uv sync --locked
```

With `--locked`, the command fails if `pyproject.toml` and `uv.lock` disagree, catching dependency changes that were never committed.

---

## 4. Small, Cache-Friendly Docker Images

```dockerfile
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .
RUN uv sync --locked --no-dev

CMD ["uv", "run", "python", "-m", "support_agent"]
```

Copying the dependency files first lets Docker cache the dependency layer, so code-only changes rebuild in seconds.

---

## 5. Quick Migration Checklist

1. Run `uv init` in the existing repository, or keep your current `pyproject.toml`.
2. Import existing pins with `uv add -r requirements.txt`.
3. Commit `pyproject.toml`, `uv.lock` and `.python-version`.
4. Replace `pip install` steps in CI with `uv sync --locked`.
5. Replace `python script.py` with `uv run script.py` in docs and Makefiles.
