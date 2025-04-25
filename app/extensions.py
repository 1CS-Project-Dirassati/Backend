"""
Extensions module

Each extension is initialized when app is created.
"""

from threading import Thread

from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow


from fakeredis import TcpFakeServer
from flask_redis import FlaskRedis

db = SQLAlchemy()

bcrypt = Bcrypt()
migrate = Migrate()
cors = CORS()


jwt = JWTManager()
ma = Marshmallow()

TcpFakeServer.allow_reuse_address = True
TcpFakeServer.allow_reuse_port = True

server_address = ("127.0.0.1", 6379)
server = TcpFakeServer(server_address, server_type="redis")
t = Thread(target=server.serve_forever, daemon=True)
t.start()

redis_client = FlaskRedis(host=server_address[0], port=server_address[1])
