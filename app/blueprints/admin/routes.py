from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import ClickEvent, Company, GalleryImage, Product, ServiceItem, User
from app.utils import create_slug, save_upload

admin_bp = Blueprint("admin", __name__)


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


def to_bool(field_name):
    return request.form.get(field_name) == "on"


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


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = User.query.filter_by(email=email).first()

        if user and user.is_active and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin.dashboard"))

        flash("E-mail ou senha inválidos.", "danger")

    return render_template("admin/login.html")


@admin_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
def admin_home():
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    company = get_company()
    data = summary_data(company.id)
    recent_events = ClickEvent.query.filter_by(company_id=company.id).order_by(ClickEvent.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", company=company, data=data, recent_events=recent_events)


@admin_bp.route("/produtos")
@login_required
def products():
    company = get_company()
    items = Product.query.filter_by(company_id=company.id).order_by(Product.created_at.desc()).all()
    return render_template("admin/products/list.html", company=company, items=items)


@admin_bp.route("/produtos/novo", methods=["GET", "POST"])
@login_required
def product_create():
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
    company = get_company()
    item = Product.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    if request.method == "POST":
        try:
            item.name = request.form.get("name")
            item.slug = ensure_unique_slug(Product, company.id, create_slug(item.name), current_id=item.id)
            item.description = request.form.get("description")
            item.price = request.form.get("price") or None
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
    company = get_company()
    item = Product.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Produto excluído com sucesso.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/servicos")
@login_required
def services():
    company = get_company()
    items = ServiceItem.query.filter_by(company_id=company.id).order_by(ServiceItem.created_at.desc()).all()
    return render_template("admin/services/list.html", company=company, items=items)


@admin_bp.route("/servicos/novo", methods=["GET", "POST"])
@login_required
def service_create():
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
    company = get_company()
    item = ServiceItem.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Serviço excluído com sucesso.", "success")
    return redirect(url_for("admin.services"))


@admin_bp.route("/galeria")
@login_required
def gallery():
    company = get_company()
    items = GalleryImage.query.filter_by(company_id=company.id).order_by(GalleryImage.created_at.desc()).all()
    return render_template("admin/gallery/list.html", company=company, items=items)


@admin_bp.route("/galeria/nova", methods=["GET", "POST"])
@login_required
def gallery_create():
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
    company = get_company()
    item = GalleryImage.query.filter_by(company_id=company.id, id=item_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Foto excluída com sucesso.", "success")
    return redirect(url_for("admin.gallery"))


@admin_bp.route("/relatorios")
@login_required
def reports():
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
    company = get_company()
    if request.method == "POST":
        company.name = request.form.get("name")
        company.whatsapp = request.form.get("whatsapp")
        company.instagram = request.form.get("instagram")
        company.address = request.form.get("address")
        company.headline = request.form.get("headline")
        company.description = request.form.get("description")
        company.primary_color = request.form.get("primary_color") or "#b86b77"
        db.session.commit()
        flash("Configurações atualizadas com sucesso.", "success")
        return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", company=company)
