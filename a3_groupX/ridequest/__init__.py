"""RideQuest Flask application factory."""

import os
from pathlib import Path

from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
bootstrap = Bootstrap5()
csrf = CSRFProtect()
login_manager = LoginManager()


def create_app(test_config=None):
    """Create and configure the RideQuest Flask application."""
    app = Flask(__name__)
    database_path = Path(app.root_path) / "sitedata.sqlite"

    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY", "ridequest-local-submission-key"
        ),
        DEBUG=False,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=5 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.root_path) / "static" / "uploads"),
        ALLOWED_IMAGE_EXTENSIONS={"jpg", "jpeg", "png", "webp", "svg"},
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    bootstrap.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    from .models import User

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    from .auth import auth_bp
    from .errors import register_error_handlers
    from .events import events_bp
    from .views import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    register_error_handlers(app)

    from .forms import EmptyForm

    @app.context_processor
    def inject_shared_template_values():
        return {
            "logout_form": EmptyForm(),
            "status_class": lambda status: {
                "Open": "status-open",
                "Sold Out": "status-sold",
                "Inactive": "status-inactive",
                "Cancelled": "status-cancelled",
            }.get(status, "status-inactive"),
        }

    return app
