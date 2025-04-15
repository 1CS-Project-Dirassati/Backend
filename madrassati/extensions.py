from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_redis import FlaskRedis
from madrassati.config import Config
from fakeredis import TcpFakeServer
from threading import Thread

# setting up fake redis server
# allow address and port duplication for debugginngggg onlyyyyyy , change in production
TcpFakeServer.allow_reuse_address = True
TcpFakeServer.allow_reuse_port = True
server_address = ("127.0.0.1", 6379)
server = TcpFakeServer(server_address,server_type="redis")
t = Thread(target=server.serve_forever, daemon=True)
t.start()

db = SQLAlchemy()
cors = CORS()
migrate = Migrate()
redis_client = FlaskRedis(host=server_address[0], port=server_address[1])


flask_limiter = Limiter(
    get_remote_address,
    storage_uri="memory://",
)
