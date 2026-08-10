import logging
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError

logger = logging.getLogger(__name__)

MOCK_PAYMENT_URL = "https://mock-payment-gateway.example.com/api/pay"

def initiate_payment(booking):
    """
    Mock payment gateway client.
    Sends payment initiation request for a given booking.
    """
    duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600.0
    amount = float(booking.lsa.hourly_rate) * duration_hours

    payload = {
        "booking_id": booking.id,
        "amount": round(amount, 2),
        "currency": "GBP",
        "parent_email": booking.parent.email,
        # In a real app we might pass a tokenized card, but we use this mock
    }

    # Redact sensitive fields for logging
    redacted_payload = payload.copy()
    redacted_payload["parent_email"] = "***REDACTED***"

    logger.info(f"Initiating payment for Booking {booking.id}. Payload: {redacted_payload}")

    try:
        response = requests.post(
            MOCK_PAYMENT_URL,
            json=payload,
            timeout=5.0  # Explicit timeout requirement
        )
        response.raise_for_status()
        
        # Assume successful response has a reference
        data = response.json()
        logger.info(f"Payment initiated successfully for Booking {booking.id}. Gateway Response: ***REDACTED***")
        return True, data.get("provider_reference", "mock-ref-123")
        
    except Timeout:
        logger.error(f"Payment gateway timeout for Booking {booking.id}.")
        return False, "TIMEOUT"
    except ConnectionError:
        logger.error(f"Payment gateway connection error for Booking {booking.id}.")
        return False, "CONNECTION_ERROR"
    except HTTPError as e:
        logger.error(f"Payment gateway HTTP error for Booking {booking.id}: {e.response.status_code}")
        return False, "HTTP_ERROR"
    except Exception as e:
        logger.error(f"Unexpected error initiating payment for Booking {booking.id}: {str(e)}")
        return False, "UNKNOWN_ERROR"
