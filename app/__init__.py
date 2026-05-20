import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_wtf.csrf import CSRFError

from app.config import Config
from app.extensions import csrf, db, login_manager
from app.models import User
from app.utils import money

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    app.jinja_env.filters["money"] = money

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return "Sessão expirada ou formulário inválido. Volte para a página anterior e tente novamente.", 400

    from app.blueprints.public.routes import public_bp
    from app.blueprints.admin.routes import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.models import Company, Product, ServiceItem, GalleryImage
    from app.utils import create_slug

    @app.cli.command("init-db")
    def init_db():
        """Cria o banco e insere dados iniciais."""
        db.create_all()

        admin_email = os.getenv("ADMIN_EMAIL", "admin@codecraft.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "123456")

        company = Company.query.filter_by(slug="salao-modelo").first()
        if not company:
            company = Company(
                name="Salão Modelo",
                slug="salao-modelo",
                whatsapp="5541992755940",
                instagram="https://instagram.com/",
                address="Curitiba, PR",
                headline="Realce sua beleza com cuidado, estilo e atendimento personalizado",
                description="Serviços de beleza, cuidados capilares e produtos selecionados para deixar seu cabelo ainda mais bonito.",
                primary_color="#b86b77",
                status="active",
            )
            db.session.add(company)
            db.session.commit()

        user = User.query.filter_by(email=admin_email).first()
        if not user:
            user = User(
                company_id=company.id,
                name="Administrador",
                email=admin_email,
                role="admin",
                is_active=True,
            )
            user.set_password(admin_password)
            db.session.add(user)

        if Product.query.filter_by(company_id=company.id).count() == 0:
            products = [
                Product(company_id=company.id, name="Kit Hidratação", slug=create_slug("Kit Hidratação"), description="Tratamento para cabelos ressecados e sem brilho.", price=89.90, is_available=True, is_featured=True),
                Product(company_id=company.id, name="Óleo Reparador", slug=create_slug("Óleo Reparador"), description="Finalização com brilho, maciez e controle de frizz.", price=39.90, is_available=True, is_featured=True),
                Product(company_id=company.id, name="Máscara Capilar", slug=create_slug("Máscara Capilar"), description="Máscara profissional para cuidado semanal.", price=79.90, is_available=True, is_featured=False),
            ]
            db.session.add_all(products)

        if ServiceItem.query.filter_by(company_id=company.id).count() == 0:
            services = [
                ServiceItem(company_id=company.id, name="Progressiva", slug=create_slug("Progressiva"), description="Alinhamento capilar com acabamento profissional.", price_from=180.00, duration="2h a 3h", is_active=True, is_featured=True),
                ServiceItem(company_id=company.id, name="Coloração", slug=create_slug("Coloração"), description="Mudança de cor com cuidado e avaliação personalizada.", price_from=120.00, duration="2h", is_active=True, is_featured=True),
                ServiceItem(company_id=company.id, name="Hidratação", slug=create_slug("Hidratação"), description="Tratamento para brilho, maciez e recuperação dos fios.", price_from=70.00, duration="1h", is_active=True, is_featured=False),
            ]
            db.session.add_all(services)

        if GalleryImage.query.filter_by(company_id=company.id).count() == 0:
            gallery = [
                GalleryImage(company_id=company.id, title="Antes e depois", description="Resultado de transformação capilar.", category="Antes e depois", is_visible=True),
                GalleryImage(company_id=company.id, title="Coloração", description="Trabalho de coloração personalizado.", category="Coloração", is_visible=True),
            ]
            db.session.add_all(gallery)

        db.session.commit()
        print("Banco criado com sucesso.")
        print(f"Acesso ao painel: {admin_email} / {admin_password}")
        print("Site público: http://127.0.0.1:5000/salao-modelo")

    return app
