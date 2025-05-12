from dotenv import dotenv_values
import motor.motor_asyncio
from loguru import logger

config = dotenv_values(".env")

global Database

try:
    MONGO_DETAILS = config["MONGO_URL"]
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)
    Database = client[config["DB_NAME"]]
    logger.info("DB Connection Successful")
except Exception as er:
    print("DB Connection Failed",er)
