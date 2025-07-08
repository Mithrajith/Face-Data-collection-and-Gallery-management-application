import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Add src directory to system path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import HOST, PORT, WORKERS, BASE_DIR
from api.routes import create_app

# Create the FastAPI app
app = create_app()

if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting server on {HOST}:{PORT} with {WORKERS} workers")
    uvicorn.run("main:app", host=HOST, port=PORT, workers=WORKERS)
