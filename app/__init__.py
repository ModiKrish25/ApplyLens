import os
from flask import Flask
from config import Config
from .extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(os.path.dirname(app.config["UPLOAD_FOLDER"]), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORT_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User  # noqa: F401  (needed for flask-login user loader)

    from .routes.auth import auth_bp
    from .routes.dashboard import dash_bp
    from .routes.resumes import resumes_bp
    from .routes.jobs import jobs_bp
    from .routes.applications import apps_bp
    from .routes.analytics import analytics_bp
    from .routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(resumes_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(apps_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)

    with app.app_context():
        db.create_all()

    return app
