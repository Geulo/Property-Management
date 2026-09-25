from flask import Flask, render_template

from src.database import Database

VERSION = "0.0.1"
NAME = "WoW"

app = Flask(__name__)

db = Database(version=VERSION, name=NAME)
db = Database.connect_sqlite()

@app.route("/")
def home():
    return render_template("login.html") 


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)