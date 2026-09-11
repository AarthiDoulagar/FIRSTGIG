import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "firstgig-hackathon-dev-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "instance", "firstgig.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf", "zip", "txt", "md"}
