from functools import wraps

from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

# A login token is the user id, signed with SECRET_KEY and stamped with the time.
# The tasks service holds the same SECRET_KEY, so it can check a token without
# calling this service (it keeps working while property is down).
TOKEN_MAX_AGE_S = 8 * 60 * 60


def make_token(secret_key, user_id):
    return URLSafeTimedSerializer(secret_key, salt="login").dumps({"user_id": user_id})


def read_token(secret_key, token, max_age=TOKEN_MAX_AGE_S):
    # None for a forged, garbled or expired token (SignatureExpired is a BadSignature)
    try:
        data = URLSafeTimedSerializer(secret_key, salt="login").loads(token, max_age=max_age)
    except BadSignature:
        return None
    return data.get("user_id")


def require_user(view):
    # replaces the session check of Assignment 1: the UI sends "Authorization: Bearer <token>"
    @wraps(view)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip()
        user_id = read_token(current_app.config["SECRET_KEY"], token) if token else None
        if user_id is None:
            return jsonify(error="Log in first"), 401
        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapper
