import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")  # Change this in production
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///madrassati.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

     # JWT expiration time (in seconds)
    JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", 3600))  # Default: 1 hour
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")  # Default: HS256
    REDIS_URL = "redis://:password@localhost:6379/0"
