from database import SessionLocal
import uuid
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        
def generate_transaction_id():
    return str(uuid.uuid4())