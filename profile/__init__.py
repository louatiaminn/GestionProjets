from flask import Blueprint

profile = Blueprint('profile', __name__)

from . import user_profile