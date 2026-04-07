import sys
import os

# This allows the server folder to import models.py from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import SupportAction, SupportObservation, Ticket

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State

class HelpdeskEnvironment(Environment):
    # This tells OpenEnv it can run multiple agents testing this at the same time
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        # OpenEnv will automatically override this when testing different tasks
        self.task_name = "easy_password_reset" 
        self.step_count = 0
        self.max_steps = 10
        
        # State variables
        self.tickets = {}
        self.kb = {}
        self.current_ticket_id = None
        self.kb_results = None
        self.feedback = ""

    def _setup_task(self):
        """Loads the specific task data based on the difficulty requested."""
        if self.task_name == "easy_password_reset":
            self.tickets = {"T-101": {"id": "T-101", "subject": "Can't log in", "body": "I forgot my password.", "status": "open"}}
            self.kb = {"password": "To reset password, go to https://example.com/reset"}
            
        elif self.task_name == "medium_billing_refund":
            self.tickets = {"T-201": {"id": "T-201", "subject": "Refund requested", "body": "I want a refund.", "status": "open"}}
            self.kb = {"refund": "Refunds must be escalated to the 'billing' department."}
            
        elif self.task_name == "hard_multi_ticket_outage":
            self.tickets = {
                "T-301": {"id": "T-301", "subject": "Site down", "body": "502 error", "status": "open"},
                "T-302": {"id": "T-302", "subject": "API failing", "body": "502 gateway", "status": "open"}
            }
            self.kb = {"502": "Known AWS outage. Tell users we are working on it and resolve the ticket."}
        
        self.current_ticket_id = None
        self.kb_results = None
        self.feedback = "Environment initialized."

    def reset(self) -> SupportObservation:
        """Called at the start of every episode."""
        self.step_count = 0
        self.reward = 0.0
        self.done = False
        self._setup_task()
        return self._get_obs()

    def step(self, action: SupportAction) -> SupportObservation:
        """Processes the AI's action and updates the environment state."""
        self.step_count += 1
        self.feedback = ""
        self.reward = 0.0 # Reset step reward
        
        # Action: Reading a ticket
        if action.action == "view_ticket":
            if action.ticket_id in self.tickets:
                self.current_ticket_id = action.ticket_id
                self.feedback = f"Viewing ticket {action.ticket_id}."
                self.reward = 0.1  # Partial reward for investigating
            else:
                self.feedback = "Ticket not found."
                self.reward = -0.1 # Penalty for hallucinating ticket IDs

        # Action: Searching the Knowledge Base
        elif action.action == "search_kb":
            match = next((v for k, v in self.kb.items() if k in (action.query or "").lower()), None)
            if match:
                self.kb_results = match
                self.feedback = "Found KB article."
                self.reward = 0.2  # Partial reward for finding documentation
            else:
                self.kb_results = "No results found."
                self.feedback = "No KB matches."
        
        # Action: Replying to the customer
        elif action.action == "reply_and_resolve":
            if action.ticket_id in self.tickets:
                self.tickets[action.ticket_id]["status"] = "resolved"
                self.feedback = f"Ticket {action.ticket_id} resolved."
                
                # Grader logic for success
                if self.task_name == "easy_password_reset" and "example.com/reset" in (action.message or ""):
                    self.reward = 0.7
                    self.done = True
                elif self.task_name == "hard_multi_ticket_outage":
                    if all(t["status"] == "resolved" for t in self.tickets.values()):
                        self.reward = 0.8
                        self.done = True
                else:
                    self.reward = -0.5 # Penalty for wrong resolution
            else:
                self.feedback = "Invalid ticket ID."

        # Action: Escalating to another department
        elif action.action == "escalate":
            if action.ticket_id in self.tickets:
                self.tickets[action.ticket_id]["status"] = "escalated"
                self.feedback = f"Ticket escalated to {action.department}."
                
                if self.task_name == "medium_billing_refund" and action.department == "billing":
                    self.reward = 0.7
                    self.done = True
                else:
                    self.reward = -0.2

        # Check for timeout
        if self.step_count >= self.max_steps:
            self.done = True

        return self._get_obs()

    def _get_obs(self) -> SupportObservation:
        """Helper to package the current state into the Pydantic observation model."""
        curr_t = None
        if self.current_ticket_id:
            raw_t = self.tickets[self.current_ticket_id]
            curr_t = Ticket(**raw_t)
        
        return SupportObservation(
            open_tickets=[k for k, v in self.tickets.items() if v["status"] == "open"],
            current_ticket=curr_t,
            kb_search_results=self.kb_results,
            feedback=self.feedback
        )

    @property
    def state(self) -> State:
        """Required by OpenEnv for tracking episode metadata."""
        return State(step_count=self.step_count, episode_id=str(self.step_count))