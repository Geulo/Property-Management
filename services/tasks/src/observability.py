import logging
import os
import sys
import time

from flask import g, request

log = logging.getLogger("service")


def register_request_logging(app):
    # one line per request on stdout: method, path, status, duration
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(message)s")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # its own access line would double ours

    @app.before_request
    def start_timer():
        g.started = time.perf_counter()

    @app.after_request
    def log_request(response):
        duration_ms = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
        log.info("%s %s %s %.1fms", request.method, request.path, response.status_code, duration_ms)
        return response


def register_cors(app):
    # the browser may call this service only from the UI's origin
    allowed_origin = os.environ.get("CORS_ORIGIN", "http://localhost:8080")

    @app.after_request
    def add_cors_headers(response):
        if request.headers.get("Origin") == allowed_origin:
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            response.headers["Vary"] = "Origin"
        return response
