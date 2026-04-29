import os
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
APP_ENV = os.getenv("APP_ENV", "dev")
DB_NAME = f"putzplan_app_{APP_ENV}" if APP_ENV != "prod" else "putzplan_app"

client = AsyncIOMotorClient(MONGO_URI)
database = client[DB_NAME]
households_col = database["households"]
history_col = database["history"]
users_col = database["users"]
