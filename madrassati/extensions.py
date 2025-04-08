from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from redislite import Redis
from madrassati.config import  Config
db = SQLAlchemy()
cors = CORS()
migrate = Migrate()
redis_client = Redis (Config.REDIS_DB_PATH)
REDIS_SOCKET_PATH = 'redis+socket://%s' % (redis_client.socket_file, )

flask_limiter = Limiter(
get_remote_address,
    storage_uri="memory://",
)

