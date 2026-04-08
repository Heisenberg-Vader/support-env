import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import SupportAction, SupportObservation, Ticket

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

class HelpdeskEnvironment(Environment):
    SUPPORTS_CONCURRENT_SESSIONS = False
    
    supported_tasks = [
        "easy_password_reset", 
        "medium_billing_refund", 
        "hard_multi_ticket_outage"
    ]

    _task_cycler = 0 
    _active_task = "easy_password_reset"
    _global_tickets = {}
    _global_step_count = 0
    _global_current_ticket_id = None
    _global_kb_results = None
    _global_accumulated_reward = 0.0

    def __init__(self):
        self.task_name = HelpdeskEnvironment._active_task 
        self.step_count = HelpdeskEnvironment._global_step_count
        self.tickets = HelpdeskEnvironment._global_tickets
        self.current_ticket_id = HelpdeskEnvironment._global_current_ticket_id
        self.kb_results = HelpdeskEnvironment._global_kb_results
        self.accumulated_reward = HelpdeskEnvironment._global_accumulated_reward
        
        self.max_steps = 10
        self.kb = {}
        self.feedback = ""
        self.reward = 0.0
        self.done = False
        self._load_kb()
        
    def _load_kb(self):
        if self.task_name == "easy_password_reset":
            self.kb = {"password": "To reset password, go to https://example.com/reset"}
        elif self.task_name == "medium_billing_refund":
            self.kb = {"refund": "Refunds must be escalated to the 'billing' department."}
        elif self.task_name == "hard_multi_ticket_outage":
            self.kb = {"502": "Known AWS outage. Tell users we are working on it and resolve the ticket.",
                       "gateway": "Known AWS outage. Tell users we are working on it and resolve the ticket."}

    def _setup_task(self):
        self.tickets = {}
        self._load_kb()

        if self.task_name == "easy_password_reset":
            self.tickets = {"T-101": {"id": "T-101", "subject": "Can't log in", "body": "I forgot my password.", "status": "open"}}
        elif self.task_name == "medium_billing_refund":
            self.tickets = {"T-201": {"id": "T-201", "subject": "Refund requested", "body": "I want a refund.", "status": "open"}}
        elif self.task_name == "hard_multi_ticket_outage":
            self.tickets = {
                "T-301": {"id": "T-301", "subject": "Site down", "body": "502 error", "status": "open"},
                "T-302": {"id": "T-302", "subject": "API failing", "body": "502 gateway", "status": "open"}
            }
        
        self.current_ticket_id = None
        self.kb_results = None
        self.accumulated_reward = 0.0 # Reset budget for the new task
        self.feedback = f"Environment correctly loaded: {self.task_name}"
        self._save_state()

    def _save_state(self):
        HelpdeskEnvironment._active_task = self.task_name
        HelpdeskEnvironment._global_tickets = self.tickets
        HelpdeskEnvironment._global_step_count = self.step_count
        HelpdeskEnvironment._global_current_ticket_id = self.current_ticket_id
        HelpdeskEnvironment._global_kb_results = self.kb_results
        HelpdeskEnvironment._global_accumulated_reward = self.accumulated_reward

    def reset(self, config: dict = None, **kwargs) -> SupportObservation:
        target_task = None
        
        if config and "task_name" in config:
            target_task = config["task_name"]
        elif "task_id" in kwargs:
            target_task = kwargs["task_id"]
        elif "task_name" in kwargs:
            target_task = kwargs["task_name"]
            
        if not target_task:
            target_task = self.supported_tasks[HelpdeskEnvironment._task_cycler % len(self.supported_tasks)]
            HelpdeskEnvironment._task_cycler += 1
            
        self.task_name = target_task
        self.step_count = 0
        self.reward = 0.0
        self.accumulated_reward = 0.0
        self.done = False
        self._setup_task()
        return self._get_obs()

    def step(self, action: SupportAction) -> SupportObservation:
        if not self.tickets:
            self._setup_task()
            
        self.step_count += 1
        self.feedback = ""
        self.reward = 0.0 
        
        safe_ticket_id = (action.ticket_id or "").strip().upper()

        if action.action == "view_ticket":
            if safe_ticket_id in self.tickets:
                self.current_ticket_id = safe_ticket_id
                self.feedback = f"Viewing ticket {safe_ticket_id}."
                self.reward = 0.1  
            else:
                self.feedback = f"Ticket '{safe_ticket_id}' not found."
                self.reward = -0.1 

        elif action.action == "search_kb":
            match = next((v for k, v in self.kb.items() if k in (action.query or "").lower()), None)
            if match:
                self.kb_results = match
                self.feedback = "Found KB article."
                self.reward = 0.2  
            else:
                self.kb_results = "No results found."
                self.feedback = "No KB matches."
        
        elif action.action == "reply_and_resolve":
            if safe_ticket_id in self.tickets:
                self.tickets[safe_ticket_id]["status"] = "resolved"
                self.feedback = f"Ticket {safe_ticket_id} resolved."
                
                if self.task_name == "easy_password_reset" and "example.com/reset" in (action.message or ""):
                    self.reward = 0.69
                    self.done = True
                elif self.task_name == "hard_multi_ticket_outage":
                    if all(t["status"] == "resolved" for t in self.tickets.values()):
                        self.reward = 0.69
                        self.done = True
                    else:
                        self.reward = 0.3 
                else:
                    self.reward = -0.5 
            else:
                self.feedback = "Invalid ticket ID."

        elif action.action == "escalate":
            if safe_ticket_id in self.tickets:
                self.tickets[safe_ticket_id]["status"] = "escalated"
                self.feedback = f"Ticket escalated to {action.department}."
                
                if self.task_name == "medium_billing_refund" and action.department == "billing":
                    self.reward = 0.69
                    self.done = True
                else:
                    self.reward = -0.2

        if self.step_count >= self.max_steps:
            self.done = True

        # --- THE BUDGET CHECK ---
        # Mathematically guarantees the total score across all steps NEVER exceeds 0.99
        if self.reward > 0:
            remaining_budget = 0.99 - self.accumulated_reward
            self.reward = max(0.0, min(self.reward, remaining_budget))
            self.accumulated_reward += self.reward

        self._save_state()
        return self._get_obs()

    def _get_obs(self) -> SupportObservation:
        curr_t = None
        if self.current_ticket_id:
            raw_t = self.tickets[self.current_ticket_id]
            curr_t = Ticket(**raw_t)
        
        return SupportObservation(
            open_tickets=[k for k, v in self.tickets.items() if v["status"] == "open"],
            current_ticket=curr_t,
            kb_search_results=self.kb_results,
            feedback=self.feedback,
            reward=getattr(self, "reward", 0.0),
            done=getattr(self, "done", False)
        )

    @property
    def state(self) -> State:
        return State(step_count=self.step_count, episode_id=str(self.step_count))
        
    def get_score(self) -> float:
        if self.done and self.accumulated_reward > 0:
            return min(0.99, self.accumulated_reward)
        return 0.01