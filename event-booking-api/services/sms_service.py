# import os
#
# from twilio.rest import Client
# from twilio.base.exceptions import TwilioRestException
#
#
# # ============================================================
# # ENVIRONMENT
# # ============================================================
#
# TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
# TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
#
#
# # ============================================================
# # CONFIGURATION CHECK
# # ============================================================
#
# def _get_twilio_client():
#     """
#     Create and return a Twilio client.
#
#     Configuration is checked only when SMS functionality
#     is actually used.
#     """
#
#     if not TWILIO_ACCOUNT_SID:
#         raise RuntimeError(
#             "TWILIO_ACCOUNT_SID is not configured"
#         )
#
#     if not TWILIO_AUTH_TOKEN:
#         raise RuntimeError(
#             "TWILIO_AUTH_TOKEN is not configured"
#         )
#
#     if not TWILIO_PHONE_NUMBER:
#         raise RuntimeError(
#             "TWILIO_PHONE_NUMBER is not configured"
#         )
#
#     return Client(
#         TWILIO_ACCOUNT_SID,
#         TWILIO_AUTH_TOKEN
#     )
#
#
# # ============================================================
# # SEND SMS
# # ============================================================
#
# def send_sms(
#     recipient_phone: str,
#     message: str
# ):
#     """
#     Send an SMS through Twilio.
#
#     Returns the provider message SID when successful.
#     Raises RuntimeError when the provider rejects the request.
#     """
#
#     if not recipient_phone:
#         raise ValueError(
#             "Recipient phone number is required"
#         )
#
#     if not message:
#         raise ValueError(
#             "SMS message cannot be empty"
#         )
#
#     client = _get_twilio_client()
#
#     try:
#         sms = client.messages.create(
#             body=message,
#             from_=TWILIO_PHONE_NUMBER,
#             to=recipient_phone
#         )
#
#         return sms.sid
#
#     except TwilioRestException as exc:
#         raise RuntimeError(
#             f"SMS delivery failed: {exc.msg}"
#         ) from exc
#
#
# # ============================================================
# # SEND OTP SMS
# # ============================================================
#
# def send_otp_sms(
#     recipient_phone: str,
#     otp: str
# ):
#     """
#     Send an Eventora OTP through SMS.
#
#     The OTP itself is never stored in plaintext by the
#     application. This function only receives it temporarily
#     so it can be delivered to the user.
#     """
#
#     if not otp:
#         raise ValueError(
#             "OTP is required"
#         )
#
#     message = (
#         f"Your Eventora verification code is {otp}. "
#         f"It expires in 5 minutes. "
#         f"Do not share this code with anyone."
#     )
#
#     return send_sms(
#         recipient_phone=recipient_phone,
#         message=message
#     )


import os
import logging

logger = logging.getLogger(__name__)

TWILIO_ENABLED = os.getenv("TWILIO_ENABLED", "false").lower() == "true"


def send_otp_sms(phone: str, otp: str) -> bool:
    """
    Send OTP through SMS provider.

    Currently disabled unless TWILIO_ENABLED=true.
    This allows local development and testing without
    requiring Twilio credentials or the Twilio package.
    """

    if not TWILIO_ENABLED:
        logger.info(
            "SMS provider disabled. OTP generated for %s",
            phone
        )

        # Development mode only.
        # Do not expose OTP in production responses/logs.
        return True

    try:
        from twilio.rest import Client

        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")

        if not account_sid or not auth_token or not twilio_phone:
            logger.error(
                "Twilio is enabled but required credentials are missing."
            )
            return False

        client = Client(
            account_sid,
            auth_token
        )

        client.messages.create(
            body=f"Your EVENTORA verification code is {otp}.",
            from_=twilio_phone,
            to=phone
        )

        return True

    except ImportError:
        logger.error(
            "Twilio is enabled but the twilio package is not installed."
        )
        return False

    except Exception:
        logger.exception(
            "Failed to send OTP SMS."
        )
        return False