from flask import send_from_directory
import os
from flask import Flask, render_template
from config import Config
from extensions import db, login_manager
from models import User, Notification
from services.notify import mark_overdue_projects


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "submissions"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "avatars"), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.client import client_bp
    from routes.gigs import gigs_bp
    from routes.projects import projects_bp
    from routes.reviews import reviews_bp
    from routes.disputes import disputes_bp
    from routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(client_bp)
    app.register_blueprint(gigs_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(disputes_bp)
    app.register_blueprint(admin_bp)

    @app.before_request
    def _overdue():
        try:
            mark_overdue_projects()
        except Exception:
            db.session.rollback()

    @app.context_processor
    def inject_unread():
        from flask_login import current_user

        unread = 0
        if current_user.is_authenticated:
            unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {"unread_count": unread}

    @app.route("/uploads/submissions/<path:filename>")
    def uploaded_submission(filename):
        folder = os.path.join(app.config["UPLOAD_FOLDER"], "submissions")
        return send_from_directory(folder, filename)

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0"),
