from flask import Flask
from logiscout_logger import init, get_logger, wsgiConfiguration, PROD

# Initialize logiscout
init(endpoint="http://localhost:9000/logs", service_name="flask-test-service", env=PROD)

# Get logger
logger = get_logger("my_flask_app")

app = Flask(__name__)
app.wsgi_app = wsgiConfiguration(app.wsgi_app)

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
        logger.error("Executing logic step 4 - simulated error scenario (not real exception)")
    except Exception as e:
        print(f"Error in logic_step_4: {e}")

@app.route("/endpoint1")
def endpoint1():
    logger.info("Endpoint 1 called")
    logic_step_1()
    logic_step_2()
    logic_step_3()
    return {"message": "Endpoint 1 executed"}

@app.route("/endpoint2")
def endpoint2():
    logger.info("Endpoint 2 called")
    logic_step_4()
    return {"message": "Endpoint 2 executed"}

def test_flask_middleware():
    print("--- Testing Flask (WSGI) Middleware ---")
    client = app.test_client()

    # Test Endpoint 1
    print("\n[Request 1] Calling /endpoint1")
    response1 = client.get("/endpoint1")
    print(f"Response Status: {response1.status_code}")
    print(f"Response Headers: {response1.headers}")

    # Flask headers access might be case sensitive depending on version, usually it handles it
    corr_id_1 = response1.headers.get("x-correlation-id")
    print(f"Captured Correlation ID (from headers - might be None if not injected back): {corr_id_1}")

    assert response1.status_code == 200

    # Test Endpoint 2
    print("\n[Request 2] Calling /endpoint2")
    response2 = client.get("/endpoint2")

    assert response2.status_code == 200
    print("\n✅ Flask Middleware Tests Ran (Check console logs for correlation_id presence)")

if __name__ == "__main__":
    test_flask_middleware()
