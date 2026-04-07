import os
import sys

# Run using `uvicorn server.app:app --host 0.0.0.0 --port 8000`

# This ensures Python can find your models.py file in the root folder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openenv.core.env_server.http_server import create_app
from models import SupportAction, SupportObservation
from server.environment import HelpdeskEnvironment

# This single function call builds the entire FastAPI web server!
app = create_app(
    HelpdeskEnvironment,
    SupportAction,
    SupportObservation,
    env_name=os.getenv("ENV_NAME", "helpdesk_env")
)