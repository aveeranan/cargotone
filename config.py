import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "cargotone-dev-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8
APP_NAME = "CargoTone CRM"
