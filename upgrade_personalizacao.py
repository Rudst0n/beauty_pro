from sqlalchemy import text

from app import create_app
from app.extensions import db


COLUMNS = {
    "secondary_color": "VARCHAR(20) DEFAULT '#b08d57'",
    "business_type": "VARCHAR(40) DEFAULT 'beauty'",
    "hero_kicker": "VARCHAR(140)",
    "hero_image": "VARCHAR(255)",
    "primary_button_text": "VARCHAR(80)",
    "secondary_button_text": "VARCHAR(80)",
}

DEFAULT_UPDATES = [
    "UPDATE companies SET secondary_color = '#b08d57' WHERE secondary_color IS NULL OR secondary_color = ''",
    "UPDATE companies SET business_type = 'beauty' WHERE business_type IS NULL OR business_type = ''",
    "UPDATE companies SET primary_button_text = 'Agendar pelo WhatsApp' WHERE primary_button_text IS NULL OR primary_button_text = ''",
    "UPDATE companies SET secondary_button_text = 'Ver produtos' WHERE secondary_button_text IS NULL OR secondary_button_text = ''",
]


def main():
    app = create_app()

    with app.app_context():
        rows = db.session.execute(text("PRAGMA table_info(companies)")).fetchall()
        existing_columns = {row[1] for row in rows}

        for column_name, column_definition in COLUMNS.items():
            if column_name not in existing_columns:
                db.session.execute(text(f"ALTER TABLE companies ADD COLUMN {column_name} {column_definition}"))
                print(f"Coluna adicionada: {column_name}")
            else:
                print(f"Coluna já existe: {column_name}")

        for statement in DEFAULT_UPDATES:
            db.session.execute(text(statement))

        db.session.commit()
        print("Upgrade de personalização avançada aplicado com sucesso.")


if __name__ == "__main__":
    main()
