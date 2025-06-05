from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
import uuid
import time
import asyncio
from typing import List, Dict, Any, Optional
import threading
from datetime import datetime

app = FastAPI(title="Data Ingestion API")

# Define enums for priority and status
class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class BatchStatus(str, Enum):
    YET_TO_START = "yet_to_start"
    TRIGGERED = "triggered"
    COMPLETED = "completed"

# Define request and response models
class IngestRequest(BaseModel):
    ids: List[int] = Field(..., description="List of IDs to process")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority of the request")

class IngestResponse(BaseModel):
    ingestion_id: str

class BatchInfo(BaseModel):
    batch_id: str
    ids: List[int]
    status: BatchStatus

class StatusResponse(BaseModel):
    ingestion_id: str
    status: BatchStatus
    batches: List[BatchInfo]

# In-memory storage for ingestion requests and their batches
ingestion_store: Dict[str, Dict[str, Any]] = {}

# Queue for processing batches with priority
processing_queue = []
queue_lock = threading.Lock()
processing_semaphore = threading.Semaphore(3)  # Allow processing of 3 IDs at a time
last_batch_time = 0
rate_limit_lock = threading.Lock()

def get_overall_status(batches):
    """Determine the overall status based on batch statuses."""
    if all(batch["status"] == BatchStatus.COMPLETED for batch in batches):
        return BatchStatus.COMPLETED
    elif any(batch["status"] == BatchStatus.TRIGGERED for batch in batches):
        return BatchStatus.TRIGGERED
    else:
        return BatchStatus.YET_TO_START

def process_id(id: int):
    """Simulate processing a single ID."""
    time.sleep(1)  # Simulate API call delay
    return {"id": id, "data": "processed"}

async def process_batch(batch_info, ingestion_id):
    """Process a batch of IDs asynchronously."""
    global last_batch_time
    
    # Update batch status to triggered
    batch_info["status"] = BatchStatus.TRIGGERED
    
    # Rate limiting: ensure at least 5 seconds between batches
    with rate_limit_lock:
        current_time = time.time()
        if current_time - last_batch_time < 5:
            await asyncio.sleep(5 - (current_time - last_batch_time))
        last_batch_time = time.time()
    
    # Process each ID in the batch
    for id in batch_info["ids"]:
        with processing_semaphore:
            # Simulate processing the ID
            result = process_id(id)
            # In a real system, you would do something with the result
    
    # Update batch status to completed
    batch_info["status"] = BatchStatus.COMPLETED

async def batch_processor():
    """Background task to process batches from the queue."""
    while True:
        if processing_queue:
            with queue_lock:
                # Sort by priority (HIGH > MEDIUM > LOW) and then by created_time
                processing_queue.sort(key=lambda x: (
                    0 if x["priority"] == Priority.HIGH else 
                    1 if x["priority"] == Priority.MEDIUM else 2,
                    x["created_time"]
                ))
                
                # Get the highest priority batch
                next_batch = processing_queue.pop(0)
            
            # Process the batch
            await process_batch(next_batch["batch_info"], next_batch["ingestion_id"])
        
        await asyncio.sleep(0.1)  # Small delay to prevent CPU hogging

# Start the background task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(batch_processor())

@app.post("/ingest", response_model=IngestResponse)
async def ingest_data(request: IngestRequest):
    # Generate a unique ingestion ID
    ingestion_id = str(uuid.uuid4())
    
    # Split IDs into batches of 3
    batches = []
    for i in range(0, len(request.ids), 3):
        batch_id = str(uuid.uuid4())
        batch_ids = request.ids[i:i+3]
        batch_info = {
            "batch_id": batch_id,
            "ids": batch_ids,
            "status": BatchStatus.YET_TO_START
        }
        batches.append(batch_info)
        
        # Add to processing queue
        with queue_lock:
            processing_queue.append({
                "ingestion_id": ingestion_id,
                "batch_info": batch_info,
                "priority": request.priority,
                "created_time": datetime.now()
            })
    
    # Store the ingestion request
    ingestion_store[ingestion_id] = {
        "ingestion_id": ingestion_id,
        "batches": batches,
        "status": BatchStatus.YET_TO_START
    }
    
    return {"ingestion_id": ingestion_id}

@app.get("/status/{ingestion_id}", response_model=StatusResponse)
async def get_status(ingestion_id: str):
    # Check if ingestion ID exists
    if ingestion_id not in ingestion_store:
        raise HTTPException(status_code=404, detail="Ingestion ID not found")
    
    # Get the ingestion data
    ingestion_data = ingestion_store[ingestion_id]
    
    # Determine overall status
    overall_status = get_overall_status(ingestion_data["batches"])
    ingestion_data["status"] = overall_status
    
    return ingestion_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 