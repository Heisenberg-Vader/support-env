import asyncio
import os
import json
import httpx
from typing import List, Optional
from openai import OpenAI

# --- Configuration matching the Prompt Requirements ---
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "dummy")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
TASK_NAME = os.getenv("MY_ENV_V4_TASK", "easy_password_reset")
BENCHMARK = os.getenv("MY_ENV_V4_BENCHMARK", "support_env")
ENV_URL = os.getenv("ENV_URL", "http://localhost:8000") 

MAX_STEPS = 10
SUCCESS_SCORE_THRESHOLD = 0.5 

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
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    action_clean = action.replace('\n', ' ').replace('\r', '')
    print(f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)

def get_model_action(client: OpenAI, obs_json: dict) -> str:
    prompt = f"Observation:\n{json.dumps(obs_json, indent=2)}\n\nNext JSON action:"
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
        return '{"action": "search_kb", "query": "error"}'

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    rewards = []
    steps_taken = 0
    score = 0.0
    
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    async with httpx.AsyncClient(base_url=ENV_URL, timeout=30.0) as http_client:
        # Reset Env via HTTP
        resp = await http_client.post("/reset", json={"task_name": TASK_NAME})
        obs = resp.json().get("observation", {})
        
        for step in range(1, MAX_STEPS + 1):
            action_str = get_model_action(client, obs)
            
            try:
                action_payload = json.loads(action_str)
            except:
                action_payload = {"action": "list_tickets"} # Fallback if LLM outputs bad JSON
            
            # Step Env via HTTP
            resp = await http_client.post("/step", json=action_payload)
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
        
        # Calculate final score based on cumulative reward (max is roughly 1.0 for the easy task)
        total_rewards = sum(rewards)
        score = min(max(total_rewards / 1.0, 0.0), 1.0) 
        success = score >= SUCCESS_SCORE_THRESHOLD

        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    asyncio.run(main())