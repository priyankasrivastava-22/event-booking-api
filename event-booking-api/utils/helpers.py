from database import SessionLocal
import secrets
import hashlib
import uuid
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        
def generate_transaction_id():
    return str(uuid.uuid4())

def generate_otp():
    return f"{secrets.randbelow(1000000):06d}"


def hash_otp(otp: str):
    return hashlib.sha256(otp.encode()).hexdigest()


def verify_otp(otp: str, otp_hash: str):
    return hashlib.sha256(otp.encode()).hexdigest() == otp_hash