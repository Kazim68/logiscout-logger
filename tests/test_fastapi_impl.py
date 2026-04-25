from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

# import sys
# import os
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logiscout_logger import init, get_logger, asgiConfiguration, PROD

# Initialize logiscout
init(api_token="your_api_key", service_name="fastapi-test-service", env=PROD)

# Get logger
logger = get_logger("my_fastapi_app")

app = FastAPI()
app.add_middleware(asgiConfiguration)

# Helper functions to simulate business logic
def logic_step_1():
    try:
        logger.info("Executing logic step 1")
    except Exception as e:
        print(f"Error in logic_step_1: {e}")

def logic_step_2():
    try:
        logger.debug("Executing logic step 2 (detailed)")
    except Exception as e:
        print(f"Error in logic_step_2: {e}")

def logic_step_3():
    try:
        logger.warning("Executing logic step 3 - something minor happened")
    except Exception as e:
        print(f"Error in logic_step_3: {e}")

def logic_step_4():
    try:
        logger.warning("Executing logic step 4 - simulated error scenario (not real exception)")
        raise ValueError("Simulated error in logic step 4")
    except Exception as e:
        logger.error(f"Exception `Error in logic_step_4: {e}", exc_info=True)

@app.get("/endpoint1")
async def endpoint1():
    logger.info("Endpoint 1 called")
    logic_step_1()
    logic_step_2()
    logic_step_3()
    return {"message": "Endpoint 1 executed"}

@app.get("/endpoint2")
async def endpoint2():
    logger.info("Endpoint 2 called")
    logic_step_4()
    return {"message": "Endpoint 2 executed"}

client = TestClient(app)

def test_fastapi_middleware():
    # print("--- Testing FastAPI (ASGI) Middleware ---")

    # # Test Endpoint 1
    # print("\n[Request 1] Calling /endpoint1")
    response1 = client.get("/endpoint1")
    # print(f"Response Status: {response1.status_code}")
    # print(f"Response Headers: {response1.headers}")

    corr_id_1 = response1.headers.get("x-correlation-id")
    # print(f"Captured Correlation ID: {corr_id_1}")

    assert response1.status_code == 200

    # Test Endpoint 2
    # print("\n[Request 2] Calling /endpoint2")
    response2 = client.get("/endpoint2")
    # print(f"Response Status: {response2.status_code}")
    # print(f"Response Headers: {response2.headers}")

    corr_id_2 = response2.headers.get("x-correlation-id")
    # print(f"Captured Correlation ID: {corr_id_2}")

    assert response2.status_code == 200

    print("\n✅ FastAPI Middleware Tests Passed")

if __name__ == "__main__":
    test_fastapi_middleware()
