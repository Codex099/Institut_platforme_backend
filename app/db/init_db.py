import logging
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.models.branch import Branch
from app.models.setting import Setting
from app.models.user import User

logger = logging.getLogger(__name__)


def seed_database(db: Session):
    """Initialise le compte Administrateur principal, l'école siège et les paramètres globaux.
    
    Toutes les valeurs sont dynamiquement lues depuis le fichier .env (via settings).
    Aucune valeur n'est codée en dur.
    """
    # 1. Vérifier si l'administrateur principal existe déjà
    admin = db.query(User).filter(User.role == "super_admin").first()
    if admin:
        return  # Base déjà initialisée

    logger.info("🌱 Initialisation de la base de données avec le compte Administrateur unique...")

    # 2. Création de la branche principale depuis les variables d'environnement (.env)
    main_branch = db.query(Branch).filter(Branch.code == settings.DEFAULT_BRANCH_CODE).first()
    if not main_branch:
        main_branch = Branch(
            name=settings.DEFAULT_BRANCH_NAME,
            code=settings.DEFAULT_BRANCH_CODE,
            address=settings.DEFAULT_BRANCH_ADDRESS,
            city=settings.DEFAULT_BRANCH_CITY,
            phone=settings.DEFAULT_BRANCH_PHONE,
            email=settings.DEFAULT_BRANCH_EMAIL,
            is_active=True,
        )
        db.add(main_branch)
        db.flush()

    # 3. Création du compte Administrateur Principal depuis les variables d'environnement (.env)
    super_admin = User(
        email=settings.INITIAL_ADMIN_EMAIL.lower().strip(),
        phone=settings.INITIAL_ADMIN_PHONE,
        password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
        full_name=settings.INITIAL_ADMIN_FULL_NAME,
        role="super_admin",
        branch_id=main_branch.id,
        preferred_lang="en",
        is_active=True,
    )
    db.add(super_admin)
    db.flush()

    # Assigner l'administrateur comme directeur de la branche principale par défaut
    main_branch.director_id = super_admin.id

    # 4. Paramètres globaux du réseau depuis les variables d'environnement (.env)
    default_settings = [
        Setting(key="reservation_hours", value=str(settings.DEFAULT_RESERVATION_HOURS), branch_id=None),
        Setting(key="deposit_min", value=f"{settings.DEFAULT_DEPOSIT_MIN:.2f}", branch_id=None),
        Setting(key="default_group_capacity", value=str(settings.DEFAULT_GROUP_CAPACITY), branch_id=None),
        Setting(key="room_capacity_policy", value=settings.ROOM_CAPACITY_POLICY, branch_id=None),
        Setting(key="attendance_edit_window_hours", value=str(settings.ATTENDANCE_EDIT_WINDOW_HOURS), branch_id=None),
    ]
    for s in default_settings:
        existing = db.query(Setting).filter(Setting.key == s.key, Setting.branch_id.is_(None)).first()
        if not existing:
            db.add(s)

    db.commit()
    logger.info(
        "✅ Initialisation réussie : Compte Administrateur unique créé (%s).",
        settings.INITIAL_ADMIN_EMAIL,
    )
