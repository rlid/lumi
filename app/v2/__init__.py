from flask import Blueprint

v2 = Blueprint("v2", __name__)

from app.v2 import views
