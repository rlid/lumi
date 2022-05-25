from flask import Blueprint

open2chat = Blueprint("open2chat", __name__)

from app.open2chat import views
