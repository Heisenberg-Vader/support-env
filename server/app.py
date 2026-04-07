import uvicorn
from openenv.core.env_server.http_server import create_app
from models import SupportAction, SupportObservation
from server.environment import HelpdeskEnvironment

# Create the FastAPI app
app = create_app(
    HelpdeskEnvironment,
    SupportAction,
    SupportObservation,
    env_name="support_env",
)

# NEW: Add a main function to start the server
def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# NEW: Add the execution guard
if __name__ == "__main__":
    main()