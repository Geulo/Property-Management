import os

from flask import Flask, jsonify

from src.database import Database
from src.observability import register_cors, register_request_logging
from src.schema import check_database, create_schema
from src.task import task_bp


def create_app():
    app = Flask(__name__)
    # no fallback: must be the property service's key, or no login token is accepted
    app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]

    register_request_logging(app)
    register_cors(app)
    app.register_blueprint(task_bp)

    @app.route("/health")
    def health():
        # reports only this service's own state, never the property service's
        try:
            connection = Database.connect(attempts=1)
            try:
                db_ok = check_database(connection)
            finally:
                connection.close()
        except Exception:
            db_ok = False

        body = {
            "status": "ok" if db_ok else "error",
            "db": "ok" if db_ok else "error",
            "version": os.environ.get("GIT_SHA", "dev"),
        }
        return jsonify(body), 200 if db_ok else 503

    # tables are created on startup, so compose up just works (migrations come later)
    connection = Database.connect()
    create_schema(connection)
    connection.close()

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    create_app().run(host="0.0.0.0", port=port, debug=debug)
