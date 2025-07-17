import os
import sys
from fastapi import FastAPI

# Add src directory to system path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import HOST, PORT, WORKERS
from api.routes import create_app
from periodic_tasks import scheduler

# Create the FastAPI app
app = create_app()

@app.on_event("startup")
def startup_event():
    """
    Start the scheduler when the application starts.
    """
    scheduler.start()
    print("Scheduler started.")

@app.on_event("shutdown")
def shutdown_event():
    """
    Stop the scheduler when the application shuts down.
    """
    scheduler.shutdown()
    print("Scheduler shut down.")

if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting server on {HOST}:{PORT} with {WORKERS} workers")
    uvicorn.run("main:app", host=HOST, port=PORT, workers=WORKERS)
