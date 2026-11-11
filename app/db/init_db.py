import logging
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.branch import Branch
from app.models.setting import Setting
from app.models.user import User

logger = logging.getLogger(__name__)


def seed_database(db: Session):
    """Initialise uniquement le compte Administrateur principal, l'école siège et les paramètres globaux.
    
    L'administrateur aura ensuite le plein pouvoir pour créer tous les autres comptes
    (Directeurs de branche, Agents administratifs, Enseignants, etc.) via l'application.
    """
    # 1. Vérifier si l'administrateur principal existe déjà
    admin = db.query(User).filter(User.role == "super_admin").first()
    if admin:
        return  # Base déjà initialisée

    logger.info("🌱 Initialisation de la base de données avec le compte Administrateur unique...")

    # 2. Création de la branche principale (École de Chlef - Siège)
    main_branch = db.query(Branch).filter(Branch.code == "CHL").first()
    if not main_branch:
        main_branch = Branch(
            name="École Chlef - Siège",
            code="CHL",
            address="12 Rue de la République",
            city="Chlef",
            phone="027771122",
            email="contact@ecole-chlef.dz",
            is_active=True,
        )
        db.add(main_branch)
        db.flush()

    # 3. Création du compte Administrateur Principal UNIQUE
    # Ce super_admin possède tous les droits globaux (y compris créer tous les autres comptes)
    super_admin = User(
        email="admin@ecole-chlef.dz",
        phone="0657776952",
        password_hash=hash_password("Admin1234"),
        full_name="Administrateur Principal",
        role="super_admin",
        branch_id=main_branch.id,
        preferred_lang="en",
        is_active=True,
    )
    db.add(super_admin)
    db.flush()

    # Assigner l'administrateur comme directeur de la branche principale par défaut
    main_branch.director_id = super_admin.id

    # 4. Paramètres globaux du réseau (requis par le PRD)
    default_settings = [
        Setting(key="reservation_hours", value="48", branch_id=None),
        Setting(key="deposit_min", value="2000.00", branch_id=None),
        Setting(key="default_group_capacity", value="15", branch_id=None),
        Setting(key="room_capacity_policy", value="warn", branch_id=None),
        Setting(key="attendance_edit_window_hours", value="24", branch_id=None),
    ]
    for s in default_settings:
        existing = db.query(Setting).filter(Setting.key == s.key, Setting.branch_id.is_(None)).first()
        if not existing:
            db.add(s)

    db.commit()
    logger.info("✅ Initialisation réussie : Compte Administrateur unique créé (admin@ecole-chlef.dz).")
