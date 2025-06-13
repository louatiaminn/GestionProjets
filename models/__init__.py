from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models to make them available
from .models import *