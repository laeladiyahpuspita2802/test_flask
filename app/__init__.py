from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
from pymongo import MongoClient
from flask_dance.contrib.google import make_google_blueprint
from config import Config
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import logging
import os

load_dotenv()
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

mail = Mail()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)

    CORS(app)
    mail.init_app(app)
    JWTManager(app)

    logging.basicConfig(level=logging.INFO) 

    # MongoDB Online
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    client = MongoClient(MONGO_URI)
    app.db = client["utercare_db"]

    # Google OAuth
    google_bp = make_google_blueprint(
        client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        redirect_to="auth.save_google_user",
        scope=["profile", "email"]
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.report import report_bp
    from app.routes.article import article_bp
    from app.routes.latihan import latihan_bp
    from app.routes.gerakan import gerakan_bp
    from app.routes.assesment import assesment_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(article_bp)
    app.register_blueprint(latihan_bp)
    app.register_blueprint(gerakan_bp)
    app.register_blueprint(assesment_bp)

    return app
