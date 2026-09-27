import os

from flask import Flask, redirect, render_template, request

from src.schema import create_schema
from src.user import user_bp

VERSION = "0.0.1"
NAME = "WoW"

create_schema()

app = Flask(__name__)
app.register_blueprint(user_bp)

@app.route("/")
def home():
    return render_template("login.html") 


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)