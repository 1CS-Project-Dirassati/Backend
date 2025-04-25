import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # Change the secret key in production run.
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24))
    DEBUG = False
    ACCESS_EXPIRES_SECONDS = os.environ.get(
        "ACCESS_TOKEN_EXPIRES_SECONDS", 60 * 15
    )  # Example: 15 mins
    REFRESH_EXPIRES_DAYS = os.environ.get(
        "REFRESH_TOKEN_EXPIRES_DAYS", 30
    )  # Example: 30 days
    OTP_EXPIRATION_SECONDS = os.environ.get(
        "OTP_EXPIRATION_SECONDS", 300
    )  # Example: 5 mins
    OTP_EXPIRATION_MINUTES = os.environ.get(
        "OTP_EXPIRATION_MINUTES", 5
    )  # Example: 5 mins
    PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS = os.environ.get(
        "PASSWORD_RESET_TOKEN_MAX_AGE_SECONDS", 3600
    )  # Example: 1 hour
    FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")

    # mailjet api keys
    MAILJET_API_KEY = os.environ.get("MAILJET_API_KEY")
    MAILJET_SECRET_KEY = os.environ.get("MAILJET_SECRET_KEY")
    MAILJET_SENDER = os.environ.get("MAILJET_SENDER")
    MAILJET_SENDER_NAME = os.environ.get("MAILJET_SENDER_NAME", "Dirassati")
    # JWT Extended config
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", os.urandom(24))
    ## Set the token to expire every week
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    RESET_LINK_EXPIRATION_MINUTES = os.environ.get(
        "RESET_LINK_EXPIRATION_MINUTES", 5
    )  # Example: 5 mins


class DevelopmentConfig(Config):
    OTP_EXPIRATION_TIME = 300  # 5 minutes
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "data-dev.sqlite")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Add logger


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    # In-memory SQLite for testing
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "data.sqlite")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


config_by_name = dict(
    development=DevelopmentConfig,
    testing=TestingConfig,
    production=ProductionConfig,
    default=DevelopmentConfig,
)
