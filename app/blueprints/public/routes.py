from urllib.parse import quote

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.extensions import db
from app.models import ClickEvent, Company, GalleryImage, Product, ServiceItem
from app.utils import get_source, hash_ip, whatsapp_link

public_bp = Blueprint("public", __name__)


def get_company_or_404(company_slug):
    company = Company.query.filter_by(slug=company_slug, status="active").first()
    if not company:
        abort(404)
    return company





def product_can_be_sold(product):
    if not product.is_available:
        return False
    if product.track_stock and (product.stock_quantity or 0) <= 0:
        return False
    return True


def register_click(company, event_type, action, item=None, item_name=None):
    event = ClickEvent(
        company_id=company.id,
        event_type=event_type,
        item_id=getattr(item, "id", None),
        item_name=getattr(item, "name", None) or item_name,
        action=action,
        source=get_source(),
        user_agent=(request.headers.get("User-Agent") or "")[:255],
        ip_hash=hash_ip(request.headers.get("X-Forwarded-For", request.remote_addr)),
    )
    db.session.add(event)
    db.session.commit()


@public_bp.route("/")
def home_redirect():
    company = Company.query.filter_by(status="active").order_by(Company.id.asc()).first()
    if company:
        return redirect(url_for("public.company_home", company_slug=company.slug))
    return "Nenhuma empresa ativa cadastrada.", 404


@public_bp.route("/<company_slug>")
def company_home(company_slug):
    company = get_company_or_404(company_slug)
    products = Product.query.filter_by(company_id=company.id, is_available=True).order_by(Product.is_featured.desc(), Product.created_at.desc()).all()
    services = ServiceItem.query.filter_by(company_id=company.id, is_active=True).order_by(ServiceItem.is_featured.desc(), ServiceItem.created_at.desc()).all()
    gallery_images = GalleryImage.query.filter_by(company_id=company.id, is_visible=True).order_by(GalleryImage.created_at.desc()).all()
    return render_template(
        "public/index.html",
        company=company,
        products=products,
        services=services,
        gallery_images=gallery_images,
    )


@public_bp.route("/<company_slug>/r/produto/<slug>")
def track_product(company_slug, slug):
    company = get_company_or_404(company_slug)
    product = Product.query.filter_by(company_id=company.id, slug=slug, is_available=True).first_or_404()
    if not product_can_be_sold(product):
        return redirect(url_for("public.company_home", company_slug=company.slug))
    register_click(company, "product", "whatsapp_click", item=product)
    message = quote(f"Olá, tenho interesse no produto {product.name}. Ainda está disponível?")
    return redirect(whatsapp_link(company, message))


@public_bp.route("/<company_slug>/r/servico/<slug>")
def track_service(company_slug, slug):
    company = get_company_or_404(company_slug)
    service = ServiceItem.query.filter_by(company_id=company.id, slug=slug, is_active=True).first_or_404()
    register_click(company, "service", "schedule_click", item=service)
    message = quote(f"Olá, gostaria de agendar ou saber mais sobre o serviço {service.name}.")
    return redirect(whatsapp_link(company, message))


@public_bp.route("/<company_slug>/r/whatsapp")
def track_whatsapp(company_slug):
    company = get_company_or_404(company_slug)
    register_click(company, "whatsapp", "general_click", item_name="WhatsApp geral")
    message = quote("Olá, vim pelo site e gostaria de mais informações.")
    return redirect(whatsapp_link(company, message))


@public_bp.route("/<company_slug>/r/instagram")
def track_instagram(company_slug):
    company = get_company_or_404(company_slug)
    register_click(company, "instagram", "profile_click", item_name="Instagram")
    if company.instagram:
        return redirect(company.instagram)
    return redirect(url_for("public.company_home", company_slug=company.slug))


@public_bp.route("/<company_slug>/r/localizacao")
def track_location(company_slug):
    company = get_company_or_404(company_slug)
    register_click(company, "location", "map_click", item_name="Localização")
    if company.address:
        return redirect(f"https://www.google.com/maps/search/?api=1&query={quote(company.address)}")
    return redirect(url_for("public.company_home", company_slug=company.slug))
