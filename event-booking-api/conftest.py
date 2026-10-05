import os

# Test-only values. These are never used outside a local test run or CI —
# real SECRET_KEY / PHONE_ENCRYPTION_KEY / PHONE_HMAC_SECRET values live only
# in Render's environment variables and, later, in GitHub Actions secrets.
#
# This file must set these BEFORE anything imports core.security, because
# security.py reads and validates them at import time (it raises RuntimeError
# if they're missing). conftest.py is loaded by pytest before test collection,
# which is what makes that ordering work.
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
os.environ.setdefault("PHONE_ENCRYPTION_KEY", "E7hfvkI39O885ADu15rXVEIytIao61EvzweP3_Wuu5M=")
os.environ.setdefault("PHONE_HMAC_SECRET", "test-hmac-secret-not-for-production")

# database.py falls back to a local SQLite file when DATABASE_URL isn't set.
# For tests we pin that fallback to its own file so a test run never touches
# whatever database a locally running server happens to be pointed at.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")