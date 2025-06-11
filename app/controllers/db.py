import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables from .env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI is not set in the environment")

# Since DB name is in the URI, you don't need to specify it separately
client = AsyncIOMotorClient(MONGO_URI)

# Get DB name directly from URI path
db_name = MONGO_URI.rsplit("/", 1)[-1].split("?")[0]  # Extract "fmsdb"
db = client[db_name]
