from flask import Blueprint

v3 = Blueprint("v3", __name__)

from app.v3 import views
