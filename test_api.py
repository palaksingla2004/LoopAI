import requests
import time
import json
import threading
import uuid
import datetime
from concurrent.futures import ThreadPoolExecutor

# API base URL - change this when deploying
BASE_URL = "http://localhost:8000"

def test_ingest_endpoint():
    """Test the /ingest endpoint with various payloads"""
    print("\n=== Testing Ingest Endpoint ===")
    
    # Test case 1: Basic ingestion with MEDIUM priority
    payload = {"ids": [1, 2, 3, 4, 5], "priority": "MEDIUM"}
    response = requests.post(f"{BASE_URL}/ingest", json=payload)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    ingestion_id1 = response.json()["ingestion_id"]
    print(f"✅ Basic ingestion successful: {ingestion_id1}")
    
    # Test case 2: Ingestion with HIGH priority
    payload = {"ids": [6, 7, 8, 9], "priority": "HIGH"}
    response = requests.post(f"{BASE_URL}/ingest", json=payload)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    ingestion_id2 = response.json()["ingestion_id"]
    print(f"✅ HIGH priority ingestion successful: {ingestion_id2}")
    
    # Test case 3: Ingestion with LOW priority
    payload = {"ids": [10, 11, 12], "priority": "LOW"}
    response = requests.post(f"{BASE_URL}/ingest", json=payload)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    ingestion_id3 = response.json()["ingestion_id"]
    print(f"✅ LOW priority ingestion successful: {ingestion_id3}")
    
    # Test case 4: Large batch of IDs
    payload = {"ids": list(range(100, 120)), "priority": "MEDIUM"}
    response = requests.post(f"{BASE_URL}/ingest", json=payload)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    ingestion_id4 = response.json()["ingestion_id"]
    print(f"✅ Large batch ingestion successful: {ingestion_id4}")
    
    return [ingestion_id1, ingestion_id2, ingestion_id3, ingestion_id4]

def test_status_endpoint(ingestion_ids):
    """Test the /status endpoint for various ingestion IDs"""
    print("\n=== Testing Status Endpoint ===")
    
    # Test case 1: Valid ingestion ID
    for ingestion_id in ingestion_ids:
        response = requests.get(f"{BASE_URL}/status/{ingestion_id}")
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        status_data = response.json()
        print(f"✅ Status for {ingestion_id}: {status_data['status']}")
        print(f"   Batches: {len(status_data['batches'])}")
    
    # Test case 2: Invalid ingestion ID
    invalid_id = str(uuid.uuid4())
    response = requests.get(f"{BASE_URL}/status/{invalid_id}")
    assert response.status_code == 404, f"Expected status code 404, got {response.status_code}"
    print(f"✅ Invalid ID correctly returns 404")

def monitor_processing(ingestion_ids, duration=60):
    """Monitor the processing of ingestion requests for a specified duration"""
    print(f"\n=== Monitoring Processing for {duration} seconds ===")
    start_time = time.time()
    statuses = {id: [] for id in ingestion_ids}
    
    while time.time() - start_time < duration:
        for ingestion_id in ingestion_ids:
            try:
                response = requests.get(f"{BASE_URL}/status/{ingestion_id}")
                if response.status_code == 200:
                    status_data = response.json()
                    current_status = {
                        "timestamp": time.time() - start_time,
                        "overall_status": status_data["status"],
                        "batch_statuses": [
                            {"batch_id": batch["batch_id"], "status": batch["status"]}
                            for batch in status_data["batches"]
                        ]
                    }
                    statuses[ingestion_id].append(current_status)
            except Exception as e:
                print(f"Error monitoring {ingestion_id}: {e}")
        
        time.sleep(2)  # Check every 2 seconds
    
    # Print summary of processing
    print("\n=== Processing Summary ===")
    for ingestion_id, status_history in statuses.items():
        if status_history:
            final_status = status_history[-1]
            print(f"Ingestion ID: {ingestion_id}")
            print(f"Final status: {final_status['overall_status']}")
            completed_batches = sum(1 for batch in final_status["batch_statuses"] if batch["status"] == "completed")
            total_batches = len(final_status["batch_statuses"])
            print(f"Completed batches: {completed_batches}/{total_batches}")
            
            # Calculate processing rate
            if len(status_history) > 1:
                status_changes = []
                for i in range(1, len(status_history)):
                    prev = status_history[i-1]
                    curr = status_history[i]
                    
                    # Count newly completed batches
                    prev_completed = set(batch["batch_id"] for batch in prev["batch_statuses"] 
                                        if batch["status"] == "completed")
                    curr_completed = set(batch["batch_id"] for batch in curr["batch_statuses"] 
                                        if batch["status"] == "completed")
                    newly_completed = curr_completed - prev_completed
                    
                    if newly_completed:
                        status_changes.append({
                            "timestamp": curr["timestamp"],
                            "newly_completed": len(newly_completed)
                        })
                
                if status_changes:
                    for i in range(1, len(status_changes)):
                        time_diff = status_changes[i]["timestamp"] - status_changes[i-1]["timestamp"]
                        if time_diff > 0:
                            rate = status_changes[i]["newly_completed"] / time_diff
                            print(f"Processing rate between {status_changes[i-1]['timestamp']:.1f}s and {status_changes[i]['timestamp']:.1f}s: {rate:.2f} batches/second")
                            if time_diff < 5 and status_changes[i]["newly_completed"] > 0:
                                print(f"⚠️ Rate limit may have been violated! Time between batches: {time_diff:.2f}s")
    
    return statuses

def test_priority_handling():
    """Test that higher priority requests are processed before lower priority ones"""
    print("\n=== Testing Priority Handling ===")
    
    # Submit a MEDIUM priority request
    payload1 = {"ids": [1, 2, 3, 4, 5], "priority": "MEDIUM"}
    response1 = requests.post(f"{BASE_URL}/ingest", json=payload1)
    ingestion_id1 = response1.json()["ingestion_id"]
    print(f"Submitted MEDIUM priority request: {ingestion_id1}")
    
    # Wait a bit to ensure the first request is in the queue
    time.sleep(2)
    
    # Submit a HIGH priority request
    payload2 = {"ids": [6, 7, 8, 9], "priority": "HIGH"}
    response2 = requests.post(f"{BASE_URL}/ingest", json=payload2)
    ingestion_id2 = response2.json()["ingestion_id"]
    print(f"Submitted HIGH priority request: {ingestion_id2}")
    
    # Monitor both requests for a while
    print("Monitoring processing to verify priority handling...")
    statuses = monitor_processing([ingestion_id1, ingestion_id2], duration=30)
    
    # Analyze the results to verify priority handling
    # This is a simplified analysis and might need adjustment based on actual processing times
    if statuses[ingestion_id1] and statuses[ingestion_id2]:
        # Find when batches from the HIGH priority request started completing
        high_priority_completion_times = []
        for status in statuses[ingestion_id2]:
            for batch in status["batch_statuses"]:
                if batch["status"] == "completed":
                    high_priority_completion_times.append(status["timestamp"])
                    break
            if high_priority_completion_times:
                break
        
        # Find when batches from the MEDIUM priority request started completing
        medium_priority_completion_times = []
        for status in statuses[ingestion_id1]:
            for batch in status["batch_statuses"]:
                if batch["status"] == "completed":
                    medium_priority_completion_times.append(status["timestamp"])
                    break
            if medium_priority_completion_times:
                break
        
        if high_priority_completion_times and medium_priority_completion_times:
            if min(high_priority_completion_times) < min(medium_priority_completion_times):
                print("✅ HIGH priority request processed before MEDIUM priority request")
            else:
                print("❌ Priority handling may not be working correctly")
        else:
            print("⚠️ Not enough data to verify priority handling")
    else:
        print("⚠️ Not enough data collected to verify priority handling")

def test_rate_limiting():
    """Test that the API respects the rate limit of 1 batch per 5 seconds"""
    print("\n=== Testing Rate Limiting ===")
    
    # Submit a request with multiple batches
    payload = {"ids": list(range(1, 10)), "priority": "HIGH"}
    response = requests.post(f"{BASE_URL}/ingest", json=payload)
    ingestion_id = response.json()["ingestion_id"]
    print(f"Submitted request with multiple batches: {ingestion_id}")
    
    # Monitor the processing to verify rate limiting
    print("Monitoring processing to verify rate limiting...")
    statuses = monitor_processing([ingestion_id], duration=30)
    
    # Analyze the results to verify rate limiting
    if statuses[ingestion_id]:
        # Track when batches change to completed status
        completion_times = []
        batch_statuses = {batch["batch_id"]: [] for status in statuses[ingestion_id] 
                         for batch in status["batch_statuses"]}
        
        for status in statuses[ingestion_id]:
            for batch in status["batch_statuses"]:
                batch_id = batch["batch_id"]
                batch_statuses[batch_id].append({
                    "timestamp": status["timestamp"],
                    "status": batch["status"]
                })
        
        # Find when each batch completed
        for batch_id, status_history in batch_statuses.items():
            for i in range(1, len(status_history)):
                if (status_history[i-1]["status"] != "completed" and 
                    status_history[i]["status"] == "completed"):
                    completion_times.append(status_history[i]["timestamp"])
                    break
        
        # Check if the rate limit was respected
        completion_times.sort()
        violations = 0
        for i in range(1, len(completion_times)):
            time_diff = completion_times[i] - completion_times[i-1]
            if time_diff < 5:
                violations += 1
                print(f"⚠️ Rate limit violation: {time_diff:.2f}s between completions")
        
        if violations == 0 and len(completion_times) > 1:
            print("✅ Rate limit respected")
        elif len(completion_times) <= 1:
            print("⚠️ Not enough data to verify rate limiting")
        else:
            print(f"❌ Rate limit violated {violations} times")
    else:
        print("⚠️ Not enough data collected to verify rate limiting")

def run_all_tests():
    """Run all tests"""
    print("Starting API tests...")
    
    try:
        # Test the ingest endpoint
        ingestion_ids = test_ingest_endpoint()
        
        # Test the status endpoint
        test_status_endpoint(ingestion_ids)
        
        # Test priority handling
        test_priority_handling()
        
        # Test rate limiting
        test_rate_limiting()
        
        print("\n=== All tests completed ===")
        
        # Final monitoring of all ingestion requests
        print("\n=== Final Monitoring of All Requests ===")
        monitor_processing(ingestion_ids, duration=60)
        
    except Exception as e:
        print(f"Error during testing: {e}")

if __name__ == "__main__":
    run_all_tests() 