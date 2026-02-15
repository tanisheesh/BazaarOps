from dotenv import load_dotenv

# Load .env first so SUPABASE_* are available when db_service imports
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from routers import customer

# Create FastAPI app
app = FastAPI(
    title="BazaarOps Customer Service",
    description="Customer-facing service",
    version="1.0.0"
)
app.include_router(customer.router)
# Allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check - test if service is running
@app.get("/")
async def root():
    return {
        "service": "customer-service",
        "status": "running",
        "message": "Welcome to BazaarOps!"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Run the app (only when executing this file directly)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)