import uvicorn
from fastapi.responses import HTMLResponse
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

# --- NEW: Add a visual landing page for human visitors ---
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Customer Support Environment</title>
            <style>
                body { 
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                    background-color: #0f172a; 
                    color: #e2e8f0; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    height: 100vh; 
                    margin: 0; 
                }
                .card { 
                    background-color: #1e293b; 
                    padding: 40px; 
                    border-radius: 12px; 
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5); 
                    text-align: center;
                    border: 1px solid #334155;
                }
                h1 { color: #38bdf8; margin-top: 0; }
                .status { 
                    display: inline-block;
                    background-color: #064e3b;
                    color: #34d399;
                    padding: 5px 15px;
                    border-radius: 9999px;
                    font-weight: bold;
                    margin: 20px 0;
                    border: 1px solid #059669;
                }
                p { color: #94a3b8; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🎫 Support-Env API</h1>
                <div class="status">🟢 Online & Ready</div>
                <p>This OpenEnv benchmark is successfully deployed.</p>
                <p><i>Awaiting connections from RL agents...</i></p>
            </div>
        </body>
    </html>
    """

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()