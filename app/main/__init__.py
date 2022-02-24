from flask import Blueprint

main = Blueprint("main", __name__)

from app.main import views_nav, views_public, views_workflow, views_websocket, views_payment, errors
