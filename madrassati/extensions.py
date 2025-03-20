from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_redis import FlaskRedis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from redislite import Redis
from madrassati.config import Config
db = SQLAlchemy()
migrate = Migrate()
redis_client = Redis ('/tmp/redis.db')
flask_limiter = Limiter(
get_remote_address,
    storage_uri=Config.REDIS_URL,
    strategy="fixed-window",
    storage_options={"socket_connect_timeout": 30},
)

