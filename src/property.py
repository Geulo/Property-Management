import sqlite3

from flask import Blueprint, redirect, render_template, request

from src.database import Database

property_bp = Blueprint("property_bp", __name__)

@property_bp.route("/index", methods=["GET", "POST"])
def create_property():
    try:
        connection = Database.connect_sqlite()
        cursor = connection.cursor()
        
        # property_name = request.form["property_name"]
        # address = request.form["address"]
        # user_id = request.form["user_id"]
        
        # cursor.execute("INSERT INTO properties(property_name, address, user_id) VALUES (?,?,?)", ())
        
        
        connection.commit()
        connection.close()
        return redirect("/index")   
    
    except sqlite3.IntegrityError:
        connection.close()
        print("property creation failed")
        return redirect("/index")