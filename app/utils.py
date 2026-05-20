import hashlib
import re
import unicodedata
from pathlib import Path
from uuid import uuid4

from flask import current_app, request
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def create_slug(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value or uuid4().hex[:12]


def money(value):
    if value is None:
        return "Sob consulta"
    number = float(value)
    return f"R$ {number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def only_digits(value):
    return re.sub(r"\D", "", value or "")


def whatsapp_link(company, message):
    phone = only_digits(company.whatsapp)
    return f"https://wa.me/{phone}?text={message}"


def hash_ip(ip_address):
    if not ip_address:
        return None
    secret = current_app.config.get("SECRET_KEY", "")
    payload = f"{ip_address}:{secret}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def get_source():
    return request.args.get("utm_source") or request.referrer or "direct"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_storage, company_slug, folder):
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("Formato inválido. Use PNG, JPG, JPEG ou WEBP.")

    original_name = secure_filename(file_storage.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    filename = f"{uuid4().hex}.{extension}"

    relative_folder = Path(company_slug) / folder
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"]) / relative_folder
    upload_folder.mkdir(parents=True, exist_ok=True)

    file_storage.save(upload_folder / filename)
    return str(Path("uploads") / relative_folder / filename).replace("\\", "/")
