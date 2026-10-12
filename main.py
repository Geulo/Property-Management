import os
import secrets

from flask import Flask

from src.database import Database
from src.property import property_bp
from src.schema import create_schema
from src.task import task_bp
from src.user import user_bp

VERSION = "0.1.0"


def create_app():
    app = Flask(__name__)
    # random fallback so the app still starts without config; sessions reset on restart
    app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

    app.register_blueprint(user_bp)
    app.register_blueprint(property_bp)
    app.register_blueprint(task_bp)

    # tables are created on startup, so clone + install + start just works
    connection = Database.connect_sqlite()
    create_schema(connection)
    connection.close()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
