import os
import sys
import uvicorn
from sqlalchemy import text

# Add current directory to python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from urllib.parse import urlparse, urlunparse
from app.core.config import settings
from app.db.base import Base
import app.models  # Load all models into metadata
from app.db.session import engine, SessionLocal
from app.db.init_db import seed_database


def ensure_postgres_db_exists():
    """Crée automatiquement la base de données PostgreSQL si elle n'existe pas encore."""
    if "postgresql" not in settings.DATABASE_URL:
        return
    parsed = urlparse(settings.DATABASE_URL)
    target_db = parsed.path.lstrip("/")
    if not target_db:
        return

    maint_url = urlunparse((parsed.scheme, parsed.netloc, "/postgres", "", "", ""))
    try:
        from sqlalchemy import create_engine
        maint_engine = create_engine(maint_url, isolation_level="AUTOCOMMIT")
        with maint_engine.connect() as conn:
            exists = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'")
            ).scalar()
            if not exists:
                print(f"[*] Base de données '{target_db}' introuvable. Création automatique...")
                conn.execute(text(f'CREATE DATABASE "{target_db}"'))
                print(f"[+] Base de données '{target_db}' créée avec succès !")
        maint_engine.dispose()
    except Exception:
        pass


def check_and_init_db():
    print("\n" + "=" * 65)
    print("  PLATEFORME DE GESTION DU RÉSEAU D'ÉCOLES DE FORMATION")
    print("  Backend FastAPI REST API v1.0")
    print("=" * 65)
    print(f"\n[*] Configuration active :")
    print(f"    - Environnement : {settings.ENV}")
    print(f"    - URL Base      : {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

    # Auto-création si la base de données n'existe pas encore
    ensure_postgres_db_exists()

    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
        print("    - Connexion DB  : [OK] Connecte avec succes!")

        # Create tables and seed initial data if not already present
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()

    except Exception as e:
        print("\n[!] ATTENTION : Impossible de se connecter a la base de donnees PostgreSQL.")
        print(f"    Detail de l'erreur : {e}\n")
        print("    👉 Pour utiliser PostgreSQL :")
        print("       1. Assurez-vous que le service PostgreSQL est demarre.")
        print("       2. Verifiez le mot de passe dans votre fichier .env :")
        print("          DATABASE_URL=\"postgresql+psycopg://postgres:<VOTRE_MOT_DE_PASSE>@localhost:5432/ecole_chlef_db\"")
        print("\n    💡 En attendant, le serveur FastAPI demarre et la documentation reste explorable.")

    print("\n" + "-" * 65)
    print("🚀 Serveur pret a demarrer :")
    print("   👉 Swagger UI Docs : http://127.0.0.1:8000/docs")
    print("   👉 ReDoc Docs      : http://127.0.0.1:8000/redoc")
    print("   👉 Health Check    : http://127.0.0.1:8000/health")
    print("-" * 65 + "\n")


def main():
    check_and_init_db()
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
