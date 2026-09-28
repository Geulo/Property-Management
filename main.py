import os

from flask import Flask, render_template

from src.user import user_bp
from src.property import property_bp

VERSION = "0.0.1"
NAME = "WoW"

app = Flask(__name__)
app.register_blueprint(user_bp)
app.register_blueprint(property_bp)

@app.route("/")
def login():
    return render_template("login.html") 

@app.route("/index")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)