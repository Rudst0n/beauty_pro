from datetime import datetime, timedelta
import os
import secrets
from email.message import EmailMessage
from hashlib import sha256
import smtplib

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ClickEvent, Company, GalleryImage, PasswordResetToken, Product, ProductStockMovement, ServiceItem, User
from app.utils import create_slug, save_upload

admin_bp = Blueprint("admin", __name__)

VALID_COMPANY_STATUS = {"active", "inactive", "blocked"}
VALID_BUSINESS_TYPES = {"beauty", "barber", "esthetic", "neutral", "premium"}


def is_master_user():
    return current_user.is_authenticated and current_user.role == "super_admin"


def require_master_user():
    if not is_master_user():
        abort(403)


def get_company():
    return current_user.company


def ensure_unique_slug(model, company_id, base_slug, current_id=None):
    slug = base_slug
    count = 2
    while True:
        query = model.query.filter_by(company_id=company_id, slug=slug)
        if current_id:
            query = query.filter(model.id != current_id)
        exists = query.first()
        if not exists:
            return slug
        slug = f"{base_slug}-{count}"
        count += 1


def ensure_unique_company_slug(base_slug, current_id=None):
    slug = base_slug
    count = 2
    while True:
        query = Company.query.filter_by(slug=slug)
        if current_id:
            query = query.filter(Company.id != current_id)
        exists = query.first()
        if not exists:
            return slug
        slug = f"{base_slug}-{count}"
        count += 1


def to_bool(field_name):
    return request.form.get(field_name) == "on"



def parse_int_field(field_name, default=0):
    value = (request.form.get(field_name) or "").strip()
    if value == "":
        return default
    try:
        number = int(value)
        return max(number, 0)
    except ValueError:
        return default


def product_stock_status(product):
    if not product.track_stock:
        return "Sem controle"
    quantity = product.stock_quantity or 0
    alert = product.low_stock_alert or 0
    if quantity <= 0:
        return "Esgotado"
    if alert and quantity <= alert:
        return "Baixo estoque"
    return "Em estoque"


def product_stock_class(product):
    if not product.track_stock:
        return "stock-neutral"
    quantity = product.stock_quantity or 0
    alert = product.low_stock_alert or 0
    if quantity <= 0:
        return "stock-out"
    if alert and quantity <= alert:
        return "stock-low"
    return "stock-ok"


def product_stock_summary(company_id):
    tracked = Product.query.filter_by(company_id=company_id, track_stock=True).count()
    out_of_stock = Product.query.filter(
        Product.company_id == company_id,
        Product.track_stock == True,
        Product.stock_quantity <= 0,
    ).count()
    low_stock = Product.query.filter(
        Product.company_id == company_id,
        Product.track_stock == True,
        Product.stock_quantity > 0,
        Product.stock_quantity <= Product.low_stock_alert,
    ).count()
    return {
        "tracked": tracked,
        "out_of_stock": out_of_stock,
        "low_stock": low_stock,
    }


def normalize_email(value):
    return (value or "").strip().lower()



def hash_reset_token(token):
    return sha256(token.encode("utf-8")).hexdigest()


def password_is_strong(password):
    if len(password) < 8:
        return False
    has_letter = any(char.isalpha() for char in password)
    has_number = any(char.isdigit() for char in password)
    return has_letter and has_number


def send_password_reset_email(user, reset_link):
    mail_server = os.getenv("MAIL_SERVER")
    mail_port = int(os.getenv("MAIL_PORT", "587"))
    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    mail_sender = os.getenv("MAIL_DEFAULT_SENDER") or mail_username
    use_ssl = os.getenv("MAIL_USE_SSL", "false").strip().lower() in {"1", "true", "yes", "on"}
    use_tls = os.getenv("MAIL_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}

    if not mail_server or not mail_sender:
        return False

    message = EmailMessage()
    message["Subject"] = "Recuperação de senha - Beauty Pro"
    message["From"] = mail_sender
    message["To"] = user.email
    message.set_content(
        "Olá, " + user.name + ".\n\n"
        "Recebemos uma solicitação para redefinir sua senha no Beauty Pro.\n\n"
        "Acesse o link abaixo para criar uma nova senha. O link expira em 1 hora.\n\n"
        + reset_link + "\n\n"
        "Se você não solicitou esta alteração, ignore esta mensagem."
    )

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(mail_server, mail_port, timeout=15)
        else:
            server = smtplib.SMTP(mail_server, mail_port, timeout=15)

        with server:
            if use_tls and not use_ssl:
                server.starttls()
            if mail_username and mail_password:
                server.login(mail_username, mail_password)
            server.send_message(message)
        return True
    except Exception as error:
        print(f"Erro ao enviar e-mail de recuperação: {error}")
        return False


def summary_data(company_id, days=30):
    since = datetime.utcnow() - timedelta(days=days)

    total_clicks = ClickEvent.query.filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since).count()
    product_clicks = ClickEvent.query.filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since, ClickEvent.event_type == "product").count()
    service_clicks = ClickEvent.query.filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since, ClickEvent.event_type == "service").count()
    whatsapp_clicks = ClickEvent.query.filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since, ClickEvent.event_type == "whatsapp").count()

    top_product = db.session.query(ClickEvent.item_name, func.count(ClickEvent.id).label("total"))\
        .filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since, ClickEvent.event_type == "product")\
        .group_by(ClickEvent.item_name)\
        .order_by(func.count(ClickEvent.id).desc())\
        .first()

    top_service = db.session.query(ClickEvent.item_name, func.count(ClickEvent.id).label("total"))\
        .filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since, ClickEvent.event_type == "service")\
        .group_by(ClickEvent.item_name)\
        .order_by(func.count(ClickEvent.id).desc())\
        .first()

    return {
        "total_clicks": total_clicks,
        "product_clicks": product_clicks,
        "service_clicks": service_clicks,
        "whatsapp_clicks": whatsapp_clicks,
        "top_product": top_product.item_name if top_product else "Ainda sem dados",
        "top_service": top_service.item_name if top_service else "Ainda sem dados",
    }


def ranking(company_id, event_type, days=30):
    since = datetime.utcnow() - timedelta(days=days)
    return db.session.query(ClickEvent.item_name, func.count(ClickEvent.id).label("total"))\
        .filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since, ClickEvent.event_type == event_type)\
        .group_by(ClickEvent.item_name)\
        .order_by(func.count(ClickEvent.id).desc())\
        .all()


def daily_clicks(company_id, days=30):
    since = datetime.utcnow() - timedelta(days=days)
    rows = db.session.query(func.date(ClickEvent.created_at), func.count(ClickEvent.id))\
        .filter(ClickEvent.company_id == company_id, ClickEvent.created_at >= since)\
        .group_by(func.date(ClickEvent.created_at))\
        .order_by(func.date(ClickEvent.created_at).asc())\
        .all()
    return [{"date": row[0], "total": row[1]} for row in rows]


def master_summary(days=30):
    since = datetime.utcnow() - timedelta(days=days)
    return {
        "companies": Company.query.count(),
        "active_companies": Company.query.filter_by(status="active").count(),
        "inactive_companies": Company.query.filter(Company.status != "active").count(),
        "users": User.query.count(),
        "products": Product.query.count(),
        "services": ServiceItem.query.count(),
        "clicks": ClickEvent.query.filter(ClickEvent.created_at >= since).count(),
    }


def company_usage_rows():
    companies = Company.query.order_by(Company.created_at.desc()).all()
    rows = []
    for company in companies:
        rows.append({
            "company": company,
            "users": User.query.filter_by(company_id=company.id).count(),
            "products": Product.query.filter_by(company_id=company.id).count(),
            "services": ServiceItem.query.filter_by(company_id=company.id).count(),
            "gallery": GalleryImage.query.filter_by(company_id=company.id).count(),
            "clicks": ClickEvent.query.filter_by(company_id=company.id).count(),
        })
    return rows


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if is_master_user():
            return redirect(url_for("admin.master_dashboard"))
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()

        if user and user.is_active and user.check_password(password):
            login_user(user)
            if user.role == "super_admin":
                return redirect(url_for("admin.master_dashboard"))
            return redirect(url_for("admin.dashboard"))

        flash("E-mail ou senha inválidos.", "danger")

    return render_template("admin/login.html")




@admin_bp.route("/recuperar-senha", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        if is_master_user():
            return redirect(url_for("admin.master_dashboard"))
        return redirect(url_for("admin.dashboard"))

    reset_link = None

    if request.method == "POST":
        email = normalize_email(request.form.get("email"))
        user = User.query.filter_by(email=email).first()

        if user and user.is_active:
            token = secrets.token_urlsafe(48)
            token_hash = hash_reset_token(token)

            PasswordResetToken.query.filter_by(user_id=user.id, used_at=None).update({
                "used_at": datetime.utcnow()
            })

            reset_token = PasswordResetToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.utcnow() + timedelta(hours=1),
            )
            db.session.add(reset_token)
            db.session.commit()

            reset_link = url_for("admin.reset_password", token=token, _external=True)
            email_sent = send_password_reset_email(user, reset_link)

            if email_sent:
                flash("Enviamos as instruções de recuperação para o e-mail informado.", "success")
                reset_link = None
            else:
                flash("Link de recuperação gerado. Configure SMTP para envio automático por e-mail.", "warning")
        else:
            flash("Se o e-mail estiver cadastrado, enviaremos as instruções de recuperação.", "info")

    return render_template("admin/forgot_password.html", reset_link=reset_link)


@admin_bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        if is_master_user():
            return redirect(url_for("admin.master_dashboard"))
        return redirect(url_for("admin.dashboard"))

    token_hash = hash_reset_token(token)
    reset_token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()

    if not reset_token or not reset_token.is_valid:
        flash("Link de recuperação inválido ou expirado.", "danger")
        return redirect(url_for("admin.forgot_password"))

    if request.method == "POST":
        password = request.form.get("password") or ""
        password_confirm = request.form.get("password_confirm") or ""

        if password != password_confirm:
            flash("As senhas não conferem.", "danger")
            return render_template("admin/reset_password.html")

        if not password_is_strong(password):
            flash("A senha deve ter pelo menos 8 caracteres, contendo letras e números.", "danger")
            return render_template("admin/reset_password.html")

        reset_token.user.set_password(password)
        reset_token.used_at = datetime.utcnow()
        db.session.commit()

        flash("Senha redefinida com sucesso. Acesse o painel com a nova senha.", "success")
        return redirect(url_for("admin.login"))

    return render_template("admin/reset_password.html")


@admin_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
def admin_home():
    if current_user.is_authenticated and is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/master")
@login_required
def master_dashboard():
    require_master_user()
    data = master_summary()
    companies = company_usage_rows()[:8]
    recent_events = ClickEvent.query.order_by(ClickEvent.created_at.desc()).limit(12).all()
    return render_template("admin/master/dashboard.html", data=data, companies=companies, recent_events=recent_events)


@admin_bp.route("/master/empresas")
@login_required
def master_companies():
    require_master_user()
    rows = company_usage_rows()
    return render_template("admin/master/companies.html", rows=rows)


@admin_bp.route("/master/empresas/nova", methods=["GET", "POST"])
@login_required
def master_company_create():
    require_master_user()

    if request.method == "POST":
        try:
            name = (request.form.get("name") or "").strip()
            whatsapp = (request.form.get("whatsapp") or "").strip()
            admin_email = normalize_email(request.form.get("admin_email"))
            admin_password = request.form.get("admin_password") or ""
            admin_name = (request.form.get("admin_name") or "Administrador").strip()

            if not name:
                flash("Informe o nome da empresa.", "danger")
                return render_template("admin/master/company_form.html", company=None)

            if not whatsapp:
                flash("Informe o WhatsApp da empresa.", "danger")
                return render_template("admin/master/company_form.html", company=None)

            if admin_email and User.query.filter_by(email=admin_email).first():
                flash("Já existe um usuário com este e-mail.", "danger")
                return render_template("admin/master/company_form.html", company=None)

            base_slug = create_slug(request.form.get("slug") or name)
            company = Company(
                name=name,
                slug=ensure_unique_company_slug(base_slug),
                whatsapp=whatsapp,
                instagram=request.form.get("instagram"),
                address=request.form.get("address"),
                headline=request.form.get("headline") or "Beleza, cuidado e atendimento personalizado",
                description=request.form.get("description"),
                primary_color=request.form.get("primary_color") or "#111827",
                secondary_color=request.form.get("secondary_color") or "#b08d57",
                business_type=request.form.get("business_type") if request.form.get("business_type") in VALID_BUSINESS_TYPES else "beauty",
                hero_kicker=request.form.get("hero_kicker"),
                primary_button_text=request.form.get("primary_button_text"),
                secondary_button_text=request.form.get("secondary_button_text"),
                status=request.form.get("status") if request.form.get("status") in VALID_COMPANY_STATUS else "active",
            )
            db.session.add(company)
            db.session.commit()

            if admin_email and admin_password:
                user = User(
                    company_id=company.id,
                    name=admin_name,
                    email=admin_email,
                    role="admin",
                    is_active=True,
                )
                user.set_password(admin_password)
                db.session.add(user)
                db.session.commit()

            flash("Empresa cadastrada com sucesso.", "success")
            return redirect(url_for("admin.master_companies"))
        except IntegrityError:
            db.session.rollback()
            flash("Não foi possível cadastrar. Verifique se o slug ou e-mail já existem.", "danger")

    return render_template("admin/master/company_form.html", company=None)


@admin_bp.route("/master/empresas/<int:company_id>/editar", methods=["GET", "POST"])
@login_required
def master_company_edit(company_id):
    require_master_user()
    company = Company.query.get_or_404(company_id)

    if request.method == "POST":
        try:
            name = (request.form.get("name") or "").strip()
            whatsapp = (request.form.get("whatsapp") or "").strip()

            if not name:
                flash("Informe o nome da empresa.", "danger")
                return render_template("admin/master/company_form.html", company=company)

            if not whatsapp:
                flash("Informe o WhatsApp da empresa.", "danger")
                return render_template("admin/master/company_form.html", company=company)

            company.name = name
            company.slug = ensure_unique_company_slug(create_slug(request.form.get("slug") or name), current_id=company.id)
            company.whatsapp = whatsapp
            company.instagram = request.form.get("instagram")
            company.address = request.form.get("address")
            company.headline = request.form.get("headline")
            company.description = request.form.get("description")
            company.primary_color = request.form.get("primary_color") or "#111827"
            company.secondary_color = request.form.get("secondary_color") or "#b08d57"
            company.business_type = request.form.get("business_type") if request.form.get("business_type") in VALID_BUSINESS_TYPES else "beauty"
            company.hero_kicker = request.form.get("hero_kicker")
            company.primary_button_text = request.form.get("primary_button_text")
            company.secondary_button_text = request.form.get("secondary_button_text")
            company.status = request.form.get("status") if request.form.get("status") in VALID_COMPANY_STATUS else "active"
            db.session.commit()

            flash("Empresa atualizada com sucesso.", "success")
            return redirect(url_for("admin.master_companies"))
        except IntegrityError:
            db.session.rollback()
            flash("Não foi possível atualizar. Verifique se o slug já existe.", "danger")

    return render_template("admin/master/company_form.html", company=company)


@admin_bp.route("/master/empresas/<int:company_id>/status/<status>", methods=["POST"])
@login_required
def master_company_status(company_id, status):
    require_master_user()
    if status not in VALID_COMPANY_STATUS:
        abort(400)

    company = Company.query.get_or_404(company_id)
    company.status = status
    db.session.commit()

    labels = {
        "active": "ativada",
        "inactive": "inativada",
        "blocked": "bloqueada",
    }
    flash(f"Empresa {labels.get(status, 'atualizada')} com sucesso.", "success")
    return redirect(url_for("admin.master_companies"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    data = summary_data(company.id)
    stock_data = product_stock_summary(company.id)
    recent_events = ClickEvent.query.filter_by(company_id=company.id).order_by(ClickEvent.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", company=company, data=data, stock_data=stock_data, recent_events=recent_events)




@admin_bp.route("/estoque")
@login_required
def stock():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    items = Product.query.filter_by(company_id=company.id).order_by(Product.name.asc()).all()
    movements = ProductStockMovement.query.filter_by(company_id=company.id).order_by(ProductStockMovement.created_at.desc()).limit(25).all()
    summary = product_stock_summary(company.id)
    return render_template(
        "admin/products/stock.html",
        company=company,
        items=items,
        movements=movements,
        summary=summary,
        product_stock_status=product_stock_status,
        product_stock_class=product_stock_class,
    )


@admin_bp.route("/estoque/<int:item_id>/ajustar", methods=["POST"])
@login_required
def product_stock_adjust(item_id):
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    item = Product.query.filter_by(company_id=company.id, id=item_id).first_or_404()

    movement_type = request.form.get("movement_type") or "ajuste"
    if movement_type not in {"entrada", "saida", "ajuste"}:
        abort(400)

    quantity = parse_int_field("quantity", 0)
    previous_quantity = item.stock_quantity or 0

    if movement_type == "entrada":
        new_quantity = previous_quantity + quantity
    elif movement_type == "saida":
        new_quantity = max(previous_quantity - quantity, 0)
    else:
        new_quantity = quantity

    item.track_stock = True
    item.stock_quantity = new_quantity

    movement = ProductStockMovement(
        company_id=company.id,
        product_id=item.id,
        user_id=current_user.id,
        movement_type=movement_type,
        quantity=quantity,
        previous_quantity=previous_quantity,
        new_quantity=new_quantity,
        note=request.form.get("note"),
    )
    db.session.add(movement)
    db.session.commit()

    flash("Estoque atualizado com sucesso.", "success")
    return redirect(url_for("admin.stock"))


@admin_bp.route("/produtos")
@login_required
def products():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    items = Product.query.filter_by(company_id=company.id).order_by(Product.created_at.desc()).all()
    return render_template("admin/products/list.html", company=company, items=items)


@admin_bp.route("/produtos/novo", methods=["GET", "POST"])
@login_required
def product_create():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    if request.method == "POST":
        try:
            base_slug = create_slug(request.form.get("name") or "produto")
            image = save_upload(request.files.get("image"), company.slug, "products")
            item = Product(
                company_id=company.id,
                name=request.form.get("name"),
                slug=ensure_unique_slug(Product, company.id, base_slug),
                description=request.form.get("description"),
                price=request.form.get("price") or None,
                image=image,
                sku=request.form.get("sku"),
                track_stock=to_bool("track_stock"),
                stock_quantity=parse_int_field("stock_quantity", 0),
                low_stock_alert=parse_int_field("low_stock_alert", 3),
                is_available=to_bool("is_available"),
                is_featured=to_bool("is_featured"),
            )
            db.session.add(item)
            db.session.commit()
            flash("Produto cadastrado com sucesso.", "success")
            return redirect(url_for("admin.products"))
        except ValueError as error:
            flash(str(error), "danger")
        except IntegrityError:
            db.session.rollback()
            flash("Não foi possível salvar. Verifique os dados informados.", "danger")

    return render_template("admin/products/form.html", company=company, item=None)


@admin_bp.route("/produtos/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def product_edit(item_id):
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    item = Product.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    if request.method == "POST":
        try:
            item.name = request.form.get("name")
            item.slug = ensure_unique_slug(Product, company.id, create_slug(item.name), current_id=item.id)
            item.description = request.form.get("description")
            item.price = request.form.get("price") or None
            item.sku = request.form.get("sku")
            item.track_stock = to_bool("track_stock")
            item.stock_quantity = parse_int_field("stock_quantity", 0)
            item.low_stock_alert = parse_int_field("low_stock_alert", 3)
            item.is_available = to_bool("is_available")
            item.is_featured = to_bool("is_featured")
            image = save_upload(request.files.get("image"), company.slug, "products")
            if image:
                item.image = image
            db.session.commit()
            flash("Produto atualizado com sucesso.", "success")
            return redirect(url_for("admin.products"))
        except ValueError as error:
            flash(str(error), "danger")

    return render_template("admin/products/form.html", company=company, item=item)


@admin_bp.route("/produtos/<int:item_id>/excluir", methods=["POST"])
@login_required
def product_delete(item_id):
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    item = Product.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Produto excluído com sucesso.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/servicos")
@login_required
def services():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    items = ServiceItem.query.filter_by(company_id=company.id).order_by(ServiceItem.created_at.desc()).all()
    return render_template("admin/services/list.html", company=company, items=items)


@admin_bp.route("/servicos/novo", methods=["GET", "POST"])
@login_required
def service_create():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    if request.method == "POST":
        try:
            base_slug = create_slug(request.form.get("name") or "servico")
            image = save_upload(request.files.get("image"), company.slug, "services")
            item = ServiceItem(
                company_id=company.id,
                name=request.form.get("name"),
                slug=ensure_unique_slug(ServiceItem, company.id, base_slug),
                description=request.form.get("description"),
                price_from=request.form.get("price_from") or None,
                duration=request.form.get("duration"),
                image=image,
                is_active=to_bool("is_active"),
                is_featured=to_bool("is_featured"),
            )
            db.session.add(item)
            db.session.commit()
            flash("Serviço cadastrado com sucesso.", "success")
            return redirect(url_for("admin.services"))
        except ValueError as error:
            flash(str(error), "danger")

    return render_template("admin/services/form.html", company=company, item=None)


@admin_bp.route("/servicos/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def service_edit(item_id):
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    item = ServiceItem.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    if request.method == "POST":
        try:
            item.name = request.form.get("name")
            item.slug = ensure_unique_slug(ServiceItem, company.id, create_slug(item.name), current_id=item.id)
            item.description = request.form.get("description")
            item.price_from = request.form.get("price_from") or None
            item.duration = request.form.get("duration")
            item.is_active = to_bool("is_active")
            item.is_featured = to_bool("is_featured")
            image = save_upload(request.files.get("image"), company.slug, "services")
            if image:
                item.image = image
            db.session.commit()
            flash("Serviço atualizado com sucesso.", "success")
            return redirect(url_for("admin.services"))
        except ValueError as error:
            flash(str(error), "danger")

    return render_template("admin/services/form.html", company=company, item=item)


@admin_bp.route("/servicos/<int:item_id>/excluir", methods=["POST"])
@login_required
def service_delete(item_id):
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    item = ServiceItem.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Serviço excluído com sucesso.", "success")
    return redirect(url_for("admin.services"))


@admin_bp.route("/galeria")
@login_required
def gallery():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    items = GalleryImage.query.filter_by(company_id=company.id).order_by(GalleryImage.created_at.desc()).all()
    return render_template("admin/gallery/list.html", company=company, items=items)


@admin_bp.route("/galeria/nova", methods=["GET", "POST"])
@login_required
def gallery_create():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    if request.method == "POST":
        try:
            image = save_upload(request.files.get("image"), company.slug, "gallery")
            item = GalleryImage(
                company_id=company.id,
                title=request.form.get("title"),
                description=request.form.get("description"),
                category=request.form.get("category"),
                image=image,
                is_visible=to_bool("is_visible"),
            )
            db.session.add(item)
            db.session.commit()
            flash("Foto cadastrada com sucesso.", "success")
            return redirect(url_for("admin.gallery"))
        except ValueError as error:
            flash(str(error), "danger")

    return render_template("admin/gallery/form.html", company=company, item=None)


@admin_bp.route("/galeria/<int:item_id>/editar", methods=["GET", "POST"])
@login_required
def gallery_edit(item_id):
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    item = GalleryImage.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    if request.method == "POST":
        try:
            item.title = request.form.get("title")
            item.description = request.form.get("description")
            item.category = request.form.get("category")
            item.is_visible = to_bool("is_visible")
            image = save_upload(request.files.get("image"), company.slug, "gallery")
            if image:
                item.image = image
            db.session.commit()
            flash("Foto atualizada com sucesso.", "success")
            return redirect(url_for("admin.gallery"))
        except ValueError as error:
            flash(str(error), "danger")

    return render_template("admin/gallery/form.html", company=company, item=item)


@admin_bp.route("/galeria/<int:item_id>/excluir", methods=["POST"])
@login_required
def gallery_delete(item_id):
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    item = GalleryImage.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Foto excluída com sucesso.", "success")
    return redirect(url_for("admin.gallery"))


@admin_bp.route("/relatorios")
@login_required
def reports():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    data = summary_data(company.id)
    product_ranking = ranking(company.id, "product")
    service_ranking = ranking(company.id, "service")
    chart_data = daily_clicks(company.id)
    recent_events = ClickEvent.query.filter_by(company_id=company.id).order_by(ClickEvent.created_at.desc()).limit(40).all()
    return render_template(
        "admin/reports.html",
        company=company,
        data=data,
        product_ranking=product_ranking,
        service_ranking=service_ranking,
        chart_data=chart_data,
        recent_events=recent_events,
    )


@admin_bp.route("/configuracoes", methods=["GET", "POST"])
@login_required
def settings():
    if is_master_user():
        return redirect(url_for("admin.master_dashboard"))
    company = get_company()
    if request.method == "POST":
        company.name = request.form.get("name")
        company.whatsapp = request.form.get("whatsapp")
        company.instagram = request.form.get("instagram")
        company.address = request.form.get("address")
        company.headline = request.form.get("headline")
        company.description = request.form.get("description")
        company.primary_color = request.form.get("primary_color") or "#111827"
        company.secondary_color = request.form.get("secondary_color") or "#b08d57"
        company.business_type = request.form.get("business_type") if request.form.get("business_type") in VALID_BUSINESS_TYPES else "beauty"
        company.hero_kicker = request.form.get("hero_kicker")
        company.primary_button_text = request.form.get("primary_button_text")
        company.secondary_button_text = request.form.get("secondary_button_text")

        logo = save_upload(request.files.get("logo"), company.slug, "branding")
        if logo:
            company.logo = logo

        hero_image = save_upload(request.files.get("hero_image"), company.slug, "branding")
        if hero_image:
            company.hero_image = hero_image

        db.session.commit()
        flash("Configurações atualizadas com sucesso.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", company=company)
