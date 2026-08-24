import os  # Read configuration from environment variables

INVENTORY_HOLD_MINUTES = int(os.getenv("INVENTORY_HOLD_MINUTES", "15"))  # Default inventory hold duration in minutes