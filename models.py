from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class Ticket(BaseModel):
    id: str
    subject: str
    body: str
    status: str

class SupportObservation(BaseModel):
    open_tickets: List[str] = Field(default_factory=list, description="IDs of currently open tickets.")
    current_ticket: Optional[Ticket] = Field(None, description="Details of the currently viewed ticket.")
    kb_search_results: Optional[str] = Field(None, description="Results from the last KB search.")
    feedback: str = Field("", description="System feedback from the last action.")

class SupportAction(BaseModel):
    action: Literal["list_tickets", "view_ticket", "search_kb", "reply_and_resolve", "escalate"]
    ticket_id: Optional[str] = Field(None, description="Target ticket ID.")
    query: Optional[str] = Field(None, description="Search query for KB.")
    message: Optional[str] = Field(None, description="Reply message for the customer.")
    department: Optional[str] = Field(None, description="Department to escalate to (e.g., 'billing', 'engineering').")