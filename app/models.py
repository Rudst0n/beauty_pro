from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), nullable=False)
    slug = db.Column(db.String(160), nullable=False, unique=True, index=True)
    whatsapp = db.Column(db.String(30), nullable=False)
    instagram = db.Column(db.String(255), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    logo = db.Column(db.String(255), nullable=True)
    headline = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    primary_color = db.Column(db.String(20), nullable=False, default="#111827")
    secondary_color = db.Column(db.String(20), nullable=False, default="#b08d57")
    business_type = db.Column(db.String(40), nullable=False, default="beauty")
    hero_kicker = db.Column(db.String(140), nullable=True)
    hero_image = db.Column(db.String(255), nullable=True)
    primary_button_text = db.Column(db.String(80), nullable=True)
    secondary_button_text = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(30), nullable=False, default="active")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    users = db.relationship("User", backref="company", lazy=True)
    products = db.relationship("Product", backref="company", lazy=True, cascade="all, delete-orphan")
    services = db.relationship("ServiceItem", backref="company", lazy=True, cascade="all, delete-orphan")
    gallery_images = db.relationship("GalleryImage", backref="company", lazy=True, cascade="all, delete-orphan")
    click_events = db.relationship("ClickEvent", backref="company", lazy=True, cascade="all, delete-orphan")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    name = db.Column(db.String(140), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="admin")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("company_id", "slug", name="uq_product_company_slug"),
    )


class ServiceItem(db.Model):
    __tablename__ = "service_items"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(180), nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    price_from = db.Column(db.Numeric(10, 2), nullable=True)
    duration = db.Column(db.String(80), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("company_id", "slug", name="uq_service_company_slug"),
    )


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(80), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    is_visible = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ClickEvent(db.Model):
    __tablename__ = "click_events"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    event_type = db.Column(db.String(60), nullable=False, index=True)
    item_id = db.Column(db.Integer, nullable=True)
    item_name = db.Column(db.String(160), nullable=True)
    action = db.Column(db.String(80), nullable=False, default="click")
    source = db.Column(db.String(120), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    ip_hash = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(128), nullable=False, unique=True, index=True)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("password_reset_tokens", lazy=True))

    @property
    def is_valid(self):
        return self.used_at is None and self.expires_at >= datetime.utcnow()

