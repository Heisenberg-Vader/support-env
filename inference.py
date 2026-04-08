import asyncio
import os
import json
import httpx
from typing import List, Optional
from openai import OpenAI

API_KEY = os.getenv("HF_TOKEN") or "dummy"
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK = os.getenv("MY_ENV_V4_BENCHMARK", "support_env")
ENV_URL = os.getenv("ENV_URL", "http://127.0.0.1:7860") 

MAX_STEPS = 10
SUCCESS_SCORE_THRESHOLD = 0.5 

TASKS = [
    "easy_password_reset",
    "medium_billing_refund",
    "hard_multi_ticket_outage"
]

SYSTEM_PROMPT = """
You are an AI Customer Support Agent. You receive an observation containing open tickets, current ticket details, and KB results.
You must output a JSON action to interact with the system.
Actions:
{"action": "view_ticket", "ticket_id": "T-101"}
{"action": "search_kb", "query": "password"}
{"action": "reply_and_resolve", "ticket_id": "T-101", "message": "Go to example.com/reset"}
{"action": "escalate", "ticket_id": "T-201", "department": "billing"}

Output ONLY valid JSON matching the action schema. Do not wrap in markdown.
"""

def log_start(task: str, env: str, model: str) -> None:
    print(f"\n{'='*50}\n[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    action_clean = action.replace('\n', ' ').replace('\r', '')
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}\n{'='*50}", flush=True)

# --- FIX: Added 'history' parameter so the LLM remembers what it just did ---
def get_model_action(client: OpenAI, obs_json: dict, history: list) -> str:
    history_str = json.dumps(history) if history else "None"
    
    prompt = (
        f"Previous Actions Taken: {history_str}\n\n"
        f"Current Observation:\n{json.dumps(obs_json, indent=2)}\n\n"
        f"Look at the Previous Actions. DO NOT repeat them endlessly. Make logical progress.\n"
        f"Next JSON action:"
    )
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=150,
            stream=False,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as exc:
        print(f"\n[DEBUG] LLM API Call Failed: {exc}\n", flush=True)
        # Safe fallback so it doesn't loop search_kb forever
        return '{"action": "view_ticket", "ticket_id": "ERROR"}'

async def run_episode(http_client: httpx.AsyncClient, client: OpenAI, task_name: str) -> None:
    rewards = []
    steps_taken = 0
    score = 0.0
    action_history = [] # Tracker for the LLM's memory
    
    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    max_retries = 5
    resp = None
    for attempt in range(max_retries):
        try:
            payload = {"config": {"task_name": task_name}, "task_id": task_name}
            resp = await http_client.post("/reset", json=payload)
            resp.raise_for_status()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"[FATAL] Failed to connect to environment after {max_retries} attempts. Error: {e}")
                return
            print(f"Waiting for server to wake up... (Attempt {attempt + 1}/{max_retries})")
            await asyncio.sleep(3)
    
    if resp is None or resp.status_code != 200:
        status = resp.status_code if resp else "Unknown"
        text = resp.text if resp else "No response"
        print(f"[FATAL] Server returned {status}: {text}")
        return
        
    obs = resp.json().get("observation", {})
    
    for step in range(1, MAX_STEPS + 1):
        # Pass the history into the prompt
        action_str = get_model_action(client, obs, action_history)
        
        try:
            action_payload = json.loads(action_str)
        except:
            action_payload = {"action": "list_tickets"} 
            
        # Record the action
        action_history.append(action_payload)
        
        try:
            resp = await http_client.post("/step", json={"action": action_payload})
            resp.raise_for_status()
        except Exception as e:
            print(f"[FATAL] Step {step} failed with error: {e}")
            break
            
        step_data = resp.json()
        
        obs = step_data.get("observation", {})
        reward = step_data.get("reward", 0.0)
        done = step_data.get("done", False)
        error = step_data.get("error", None)

        rewards.append(reward)
        steps_taken = step
        
        log_step(step=step, action=action_str, reward=reward, done=done, error=error)

        if done:
            break
    
    total_rewards = sum(rewards)
    score = min(max(total_rewards / 1.0, 0.0), 1.0) 
    success = score >= SUCCESS_SCORE_THRESHOLD

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    async with httpx.AsyncClient(base_url=ENV_URL, timeout=30.0) as http_client:
        for task in TASKS:
            await run_episode(http_client, client, task)

if __name__ == "__main__":
    asyncio.run(main())