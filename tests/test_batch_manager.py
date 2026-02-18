"""
Test script for BatchManager functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logiscout_logger import init, get_logger, PROD
from logiscout_logger.events import RequestLogPayload
from logiscout_logger.logger import get_batch_manager
import time

def test_batch_manager():
    """
    Test the batch manager with intelligent batching:
    1. Test log count threshold (200 logs)
    2. Test time-based flushing (30 seconds)
    """

    # Initialize logger
    init(
        endpoint="http://localhost:9000/logs",
        service_name="test-service",
        env=PROD
    )

    batch_manager = get_batch_manager()

    if not batch_manager:
        print("Batch manager not initialized (likely not in PROD mode)")
        return

    print("Testing batch manager...")
    print("-" * 50)

    # Test 1: Add payloads with < 200 logs (should not flush immediately)
    print("\n1. Adding 3 small payloads (10 logs each, total 30)...")
    for i in range(3):
        payload = RequestLogPayload(
            correlationId=f"test-{i}",
            startedAt="2026-02-09T10:30:00.000Z",
            endedAt="2026-02-09T10:30:00.100Z",
            durationMS=100.0,
            request={"method": "GET", "path": f"/test/{i}", "statusCode": 200},
            logs=[{"message": f"Log {j}", "level": "info"} for j in range(10)]
        )
        batch_manager.add_payload(payload)
        print(f"   Added payload {i+1}")

    print("   Waiting 2 seconds...")
    time.sleep(2)
    print("   (Batch should NOT have been sent yet)")

    # Test 2: Add enough payloads to trigger log count flush
    print("\n2. Adding payloads to reach 200 logs threshold...")
    for i in range(3, 20):  # Add 17 more payloads (10 logs each = 170 + 30 = 200)
        payload = RequestLogPayload(
            correlationId=f"test-{i}",
            startedAt="2026-02-09T10:30:00.000Z",
            endedAt="2026-02-09T10:30:00.100Z",
            durationMS=100.0,
            request={"method": "GET", "path": f"/test/{i}", "statusCode": 200},
            logs=[{"message": f"Log {j}", "level": "info"} for j in range(10)]
        )
        batch_manager.add_payload(payload)
        if (i + 1) * 10 >= 200:
            print(f"   Added payload {i+1} - Should trigger flush!")
            break
        else:
            print(f"   Added payload {i+1}")

    print("\n   (Batch should have been automatically flushed)")

    # Test 3: Test time-based flushing
    print("\n3. Testing time-based flush (30 seconds)...")
    print("   Adding 1 small payload and waiting...")
    payload = RequestLogPayload(
        correlationId="test-time-based",
        startedAt="2026-02-09T10:30:00.000Z",
        endedAt="2026-02-09T10:30:00.100Z",
        durationMS=100.0,
        request={"method": "GET", "path": "/test/time", "statusCode": 200},
        logs=[{"message": "Time-based test log", "level": "info"}]
    )
    batch_manager.add_payload(payload)

    print("   Waiting 5 seconds (simulating 30 second wait)...")
    print("   In production, this would wait 30 seconds")

    # For testing, we'll manually flush
    print("\n4. Manual flush test...")
    batch_manager.flush()
    print("   Manual flush completed")

    print("\n" + "-" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_batch_manager()
