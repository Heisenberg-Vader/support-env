---
title: Support Env
emoji: 🎫
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
app_file: server/app.py
---

# OpenEnv: Customer Support Environment

An interactive, RL-ready benchmark environment built on the [OpenEnv](https://github.com/meta-pytorch/openenv) framework. This project simulates a Helpdesk/Customer Support ticketing system to test the reasoning, tool-use, and resolution capabilities of Large Language Models (LLMs) and autonomous agents.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-yellow)

## Overview

The **Customer Support Environment** acts as an HTTP-based reinforcement learning environment. AI agents interact with the system by receiving observations (open tickets, KB search results, feedback) and must output strict JSON actions to triage, research, and resolve user issues.

### Key Features
* **Fully Stateless:** Designed for cloud deployment and concurrent agent testing. The environment safely re-hydrates task state per session.
* **Graded Difficulties:** Includes multiple task configurations (Easy, Medium, Hard) to test progressive reasoning capabilities.
* **Partial Rewards:** Implements dense reward shaping (e.g., `+0.1` for viewing a ticket, `+0.2` for searching the KB) to guide RL training.
* **OpenEnv Compliant:** Fully compatible with the Meta PyTorch OpenEnv specification.
* **Docker Ready:** Optimized `Dockerfile` and `pyproject.toml` for seamless deployment to Hugging Face Spaces.

---

## The Environment

### 1. Observations
At each step, the agent receives a JSON observation representing the current state of the helpdesk:
```json
{
  "open_tickets": ["T-101", "T-102"],
  "current_ticket": {
    "id": "T-101",
    "subject": "Can't log in",
    "body": "I forgot my password.",
    "status": "open"
  },
  "kb_search_results": "To reset password, go to [https://example.com/reset](https://example.com/reset)",
  "feedback": "Found KB article.",
  "reward": 0.2,
  "done": false
}
```

### 2. Available Actions
The agent must respond with one of the following validated JSON actions:
* `{"action": "view_ticket", "ticket_id": "T-101"}`
* `{"action": "search_kb", "query": "password"}`
* `{"action": "reply_and_resolve", "ticket_id": "T-101", "message": "..."}`
* `{"action": "escalate", "ticket_id": "T-201", "department": "billing"}`

### 3. Tasks
The environment supports different task scenarios dynamically loaded upon reset:
* `easy_password_reset`: Single ticket, simple KB lookup, direct resolution.
* `medium_billing_refund`: Requires realizing the agent cannot resolve it and must escalate to the correct department.
* `hard_multi_ticket_outage`: Multiple tickets related to a single root cause (502 Outage) requiring bulk resolution.

---

## Local Setup & Installation

This project uses `uv` for lightning-fast dependency management.

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/YOUR_USERNAME/support-env.git](https://github.com/YOUR_USERNAME/support-env.git)
   cd support-env
   ```

2. **Install dependencies:**
   ```bash
   pip install uv
   uv sync
   ```

3. **Run the Environment Server:**
   ```bash
   uvicorn server.app:app --host 0.0.0.0 --port 7860
   ```
   *The server will start at `http://127.0.0.1:7860`. You will see a landing page confirming the API is live.*

---

## Testing an Agent

A baseline evaluation script (`inference.py`) is included to test models against the environment using the OpenAI API spec (compatible with Hugging Face Serverless Inference).

1. **Set your API Key:**
   ```bash
   export HF_TOKEN="your_fine_grained_token"
   ```

2. **Run the evaluation:**
   ```bash
   python inference.py
   ```
   *The script will output `[START]`, `[STEP]`, and `[END]` logs compatible with OpenEnv scoring benchmarks.*
