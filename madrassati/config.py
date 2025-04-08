import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")  # Change this in production
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///madrassati.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

     # JWT expiration time (in seconds)
    JWT_EXPIRATION = int(os.getenv("JWT_EXPIRATION", 3600))  # Default: 1 hour
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")  # Default: HS256
    # Create a Redis instance using redislite
    REDIS_DB_PATH = os.path.join('/tmp/my_redis.db')
    # --- Mailjet Configuration ---
    #MAILJET_API_KEY = os.environ.get('MAILJET_API_KEY')
    #MAILJET_SECRET_KEY = os.environ.get('MAILJET_SECRET_KEY')
    MAILJET_API_KEY = os.getenv("MAILJET_API_KEY", "b19bb27f7b9468e24bbc507887e40117")  # Replace with your Mailjet API key
    MAILJET_SECRET_KEY = os.getenv('MAILJET_SECRET_KEY', '60c5e4f603cc671ceb46f936f0c1c5fc')  # Replace with your Mailjet secret key
    # Default sender email address (verified in your Mailjet account)
    MAIL_SENDER = os.environ.get('MAIL_SENDER', 'cmax0890@gmail.com')
    MAIL_SENDER_NAME = os.environ.get('MAIL_SENDER_NAME', 'Dirassati App')
