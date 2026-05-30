# ChatGPT Codex Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone local coding bridge for ChatGPT Custom GPT Actions.

**Architecture:** A dependency-free Python package exposes a locked-down workspace HTTP API, generates OpenAPI for ChatGPT Actions, and provides CLI helpers for setup, public-route guidance, optional access TTL, token rotation, and GPT instructions. The server never stores ChatGPT credentials and only accepts bearer-authenticated tool calls; optional TTL can be enabled for short-lived sessions.

**Tech Stack:** Python 3.10+ standard library and `unittest`, with macOS Terminal and Windows PowerShell setup paths. The local server runs without external runtime dependencies; ChatGPT web access requires a public HTTPS route, and the built-in tunnel command can create one when its helper is installed.

---

### Task 1: Project Skeleton And Tests

**Files:**
- Create: `tests/test_security.py`
- Create: `tests/test_workspace.py`
- Create: `tests/test_openapi.py`
- Create: `tests/test_server.py`
- Create: `pyproject.toml`
- Create: `src/chatgpt_codex/*.py`

- [x] Write behavior tests before production implementation.
- [ ] Implement minimal package modules until tests pass.
- [ ] Add README, examples, license, and install script.
- [ ] Run full tests and package import checks.
- [ ] Initialize remote `git@github.com:hutiefang76/chatgpt-codex.git`, commit, and push.
