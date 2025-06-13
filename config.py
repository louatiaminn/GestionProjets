import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'f7b2d8b9e3c645e08c26f0e7b4c5f3a3e6e7c9b2d5f3a84c763f5a8b3c6d2e90'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///project_manager.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}