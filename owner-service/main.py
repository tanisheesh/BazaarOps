from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import owner
import os

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="BazaarOps Owner Service",
    description="Owner-facing service for store management",
    version="1.0.0"
)

# Enable CORS (so Next.js can talk to us)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include owner routes
app.include_router(owner.router)

# Root endpoint - test if service is running
@app.get("/")
async def root():
    return {
        "service": "owner-service",
        "status": "running",
        "message": "Owner Service is live!"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
