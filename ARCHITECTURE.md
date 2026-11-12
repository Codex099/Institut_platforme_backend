# ARCHITECTURE.md — Plateforme de Gestion d'un Réseau d'Établissements (Backend)

Ce document décrit l'architecture globale du backend, les conventions, et l'arborescence complète des fichiers avec le rôle de chaque composant. Il est tenu à jour à chaque évolution structurelle.

## 1. Principes d'architecture
- **Framework** : FastAPI (Python 3.11+) avec Pydantic v2 pour la validation et SQLAlchemy 2.x pour l'ORM.
- **Séparation stricte des couches** :
  - `routes/` : Points d'entrée HTTP, validation Pydantic, dépendances de sécurité et de filtrage par branche. **Aucune logique métier**.
  - `services/` : Contient **toute** la logique métier (réservations, expiration, calculs financiers, conflits de planning, règles de présence, etc.).
  - `models/` : Modèles déclaratifs SQLAlchemy (PostgreSQL).
  - `schemas/` : Schémas Pydantic (Request, Response, Filter, Pagination).
  - `core/` : Configuration, sécurité JWT, contrôle d'accès (RBAC + permissions fines), isolation par branche (`branch_scope`), exceptions et internationalisation (`ar`, `en`).
  - `db/` : Session SQLAlchemy, classe Base déclarative, mixins (`TimestampMixin`, `SoftDeleteMixin`), migrations Alembic.
- **Règles transverses** :
  - Monnaie : Dinar algérien (DA), montants stockés en `Numeric(12, 2)` (jamais de `float`).
  - Dates : UTC en base de données.
  - Multi-tenant / Multi-branches : Filtre automatique par `branch_id` via `branch_scope.py` (le Super Admin / DG a accès global, les directeurs de branche et agents sont cloisonnés sauf délégation expresse dans `branch_access_grants`).
  - Enseignant strictement restreint : Accès uniquement à ses groupes, séances et pointage manuel. 403 sur finances, paiements, rémunération et autres groupes.
  - Traçabilité et Audit : Toutes les opérations sensibles (interventions DG, modifications de présence, transactions financières, changements de capacité) sont enregistrées de manière immuable dans `audit_logs`.
  - Langues : Support des messages d'erreur et notifications via en-tête `Accept-Language` (`ar` et `en`, anglais par défaut).

---

## 2. Arborescence détaillée des fichiers

```text
c:\Users\hafid\Desktop\myAPPS\projet freelance\ecole_chlef\BackEnd\
├── main.py                         # Lanceur direct à la racine (python main.py)
├── run.py                          # Script de démarrage avec vérification DB et seed initial
├── start.bat                       # Script batch Windows pour lancement en 1 clic
├── ARCHITECTURE.md                 # Vue d'ensemble du projet et inventaire des composants
├── requirements.txt                # Dépendances Python du projet
├── .env.example                    # Modèle des variables d'environnement requises
├── alembic.ini                     # Configuration de l'outil de migration Alembic
│
├── app/
│   ├── __init__.py                 # Initialisation du package app
│   ├── main.py                     # Point d'entrée FastAPI, middleware CORS, gestionnaires d'erreurs, cycle de vie
│   │
│   ├── core/                       # Socle technique transverse
│   │   ├── __init__.py             # Export des composants core
│   │   ├── config.py               # Paramètres applicatifs typés via Pydantic BaseSettings
│   │   ├── security.py             # Hachage mots de passe (argon2/bcrypt) et gestion des tokens JWT (access/refresh)
│   │   ├── permissions.py          # Définition des rôles, matrice de permissions et dépendance `require_permission`
│   │   ├── branch_scope.py         # Dépendance de scoping multi-branche (DG vs Directeur de branche / Agent)
│   │   ├── exceptions.py           # Exceptions métier personnalisées et gestionnaires d'erreurs HTTP unifiés
│   │   └── i18n.py                 # Dictionnaires et résolution multilingue (arabe / anglais)
│   │
│   ├── db/                         # Accès aux données et migrations
│   │   ├── __init__.py             # Exports db
│   │   ├── base.py                 # Base déclarative SQLAlchemy, TimestampMixin et SoftDeleteMixin
│   │   ├── session.py              # Configuration de l'Engine, SessionLocal et dépendance `get_db`
│   │   └── migrations/             # Environnement de migrations Alembic
│   │       ├── env.py              # Script d'exécution des migrations Alembic
│   │       ├── script.py.mako      # Template de génération de migrations
│   │       └── versions/           # Scripts de révision de migrations de schéma
│   │
│   ├── models/                     # Modèles SQLAlchemy (1 fichier par entité métier)
│   │   ├── __init__.py             # Export de tous les modèles pour Alembic et les relations
│   │   ├── branch.py               # Entités Branch et BranchAccessGrant (accès inter-branches)
│   │   ├── user.py                 # Utilisateurs (DG, directeurs de branche, agents, enseignants, etc.)
│   │   ├── permission.py           # Permissions fines personnalisées (UserPermission)
│   │   ├── student.py              # Dossiers étudiants
│   │   ├── parent.py               # Profils parents et associations StudentParent
│   │   ├── teacher.py              # Profils enseignants et contrats de rémunération
│   │   ├── course.py               # Formations (langues, matières de soutien scolaire)
│   │   ├── level.py                # Niveaux pédagogiques et tarification associée
│   │   ├── group.py                # Groupes d'élèves, seuil de capacité et suivi des modifications de capacité
│   │   ├── room.py                 # Salles de cours et capacités physiques
│   │   ├── schedule.py             # Créneaux hebdomadaires récurrents (affectation groupe-salle-enseignant)
│   │   ├── session.py              # Séances de cours concrètes avec statuts (planned, held, cancelled, rescheduled)
│   │   ├── closure_day.py          # Jours fériés, congés et fermetures de l'établissement
│   │   ├── enrollment.py           # Inscriptions et réservations provisoires avec verrouillage
│   │   ├── document.py             # Métadonnées des documents déposés (photos, pièces d'identité, justificatifs)
│   │   ├── attendance.py           # Feuilles d'émargement et pointage manuel (présent/absent/retard)
│   │   ├── payment.py              # Enregistrement des paiements (partiels ou complets) et reçus
│   │   ├── installment.py          # Échéanciers de paiement pour les inscriptions
│   │   ├── cash_register.py        # Caisses des branches et des agents, historique des mouvements de caisse
│   │   ├── expense.py              # Enregistrement des dépenses de fonctionnement par branche
│   │   ├── fund_transfer.py        # Remises de fonds (Agent -> Directeur, Directeur -> DG) avec workflow de validation
│   │   ├── teacher_payroll.py      # Bulletins et calculs de rémunération des enseignants
│   │   ├── announcement.py         # Annonces internes et actualités publiques
│   │   ├── notification.py         # Notifications système pour les utilisateurs
│   │   ├── contact_message.py      # Messages reçus via le formulaire de contact du site public
│   │   ├── audit_log.py            # Journal d'audit immuable des actions sensibles
│   │   ├── import_job.py           # Suivi des travaux d'importation Excel (validation, prévisualisation, commit)
│   │   ├── setting.py              # Paramètres configurables (délais de réservation, politique salle, etc.)
│   │   └── otp.py                  # Table email_verifications pour les codes OTP envoyés par email
│   │
│   ├── schemas/                    # Schémas de validation et de sérialisation Pydantic v2
│   │   ├── __init__.py             # Export des schémas Pydantic
│   │   ├── common.py               # Schémas génériques (pagination, réponse standard, message d'erreur)
│   │   ├── auth.py                 # Schémas de login, token JWT, rafraîchissement et profil
│   │   ├── branch.py               # Schémas de création, modification et réponse pour les branches
│   │   ├── user.py                 # Schémas utilisateur et attribution de rôle
│   │   ├── permission.py           # Schémas pour les permissions fines et délégations
│   │   ├── student.py              # Schémas étudiant
│   │   ├── parent.py               # Schémas parent et lien parent-enfant
│   │   ├── teacher.py              # Schémas enseignant et configuration de paie
│   │   ├── course.py               # Schémas formation
│   │   ├── level.py                # Schémas niveau pédagogique
│   │   ├── group.py                # Schémas groupe et mise à jour de capacité
│   │   ├── room.py                 # Schémas salle de cours
│   │   ├── schedule.py             # Schémas créneaux horaires et vérification de conflits
│   │   ├── session.py              # Schémas séances concrètes, annulation et report
│   │   ├── closure_day.py          # Schémas jours de fermeture
│   │   ├── enrollment.py           # Schémas préinscription, réservation, confirmation
│   │   ├── document.py             # Schémas métadonnées documentaires et upload
│   │   ├── attendance.py           # Schémas pointage manuel et correction
│   │   ├── payment.py              # Schémas paiement, reçu et annulation
│   │   ├── installment.py          # Schémas échéances
│   │   ├── cash_register.py        # Schémas caisses et mouvements
│   │   ├── expense.py              # Schémas dépenses
│   │   ├── fund_transfer.py        # Schémas remises de fonds (création, confirmation, contestation)
│   │   ├── teacher_payroll.py      # Schémas états de paie enseignants
│   │   ├── announcement.py         # Schémas annonces et actualités
│   │   ├── notification.py         # Schémas notifications
│   │   ├── contact_message.py      # Schémas messages de contact public
│   │   ├── audit_log.py            # Schémas journal d'audit
│   │   ├── import_job.py           # Schémas import Excel (upload, preview, commit, report)
│   │   ├── setting.py              # Schémas paramètres applicatifs
│   │   └── otp.py                  # Schémas envoi et vérification code OTP Brevo
│   │
│   ├── services/                   # Couche logique métier pure
│   │   ├── __init__.py             # Export des services
│   │   ├── storage_service.py      # Abstraction du stockage des fichiers (disque local dev / S3 prod)
│   │   ├── auth_service.py         # Gestion de l'authentification, délivrance et renouvellement des tokens
│   │   ├── user_service.py         # Gestion des comptes utilisateurs, statuts et affectations
│   │   ├── permission_service.py   # Évaluation des droits d'accès et attribution des permissions
│   │   ├── audit_service.py        # Écriture systématique dans le journal d'audit
│   │   ├── notification_service.py # Génération et distribution des notifications internes
│   │   ├── enrollment_service.py   # Réservation avec verrouillage ligne, expiration, confirmation avec contrôle d'acompte
│   │   ├── schedule_service.py     # Détection des conflits (salle, enseignant, étudiant), fermetures, annulation/report
│   │   ├── attendance_service.py   # Pointage manuel, validation de présence, unicité séance/étudiant, fenêtres de saisie
│   │   ├── cash_service.py         # Gestion des caisses par branche et par agent, solde et mouvements
│   │   ├── payment_service.py      # Enregistrement des règlements, calcul des restes dus, contre-passation d'écritures
│   │   ├── receipt_service.py      # Génération des numéros de reçu séquentiels et documents PDF (ReportLab)
│   │   ├── fund_transfer_service.py# Workflow complet des remises de fonds et mise à jour synchrone des caisses
│   │   ├── payroll_service.py      # Calcul des rémunérations enseignants selon séances 'held' (horaire/séance/fixe)
│   │   ├── document_service.py     # Gestion sécurisée du cycle de vie des pièces jointes et vérification MIME
│   │   ├── import_service.py       # Import Excel en 3 phases (validation, prévisualisation, commit transactionnel)
│   │   ├── export_service.py       # Export des données tabulaires au format Excel (openpyxl) et rapports PDF
│   │   ├── report_service.py       # Synthèse des indicateurs opérationnels, de présence et financiers
│   │   ├── email_service.py        # Intégration API Brevo (Sendinblue) pour l'envoi d'emails transactionnels
│   │   ├── otp_service.py          # Gestion du cycle de vie des codes OTP (génération, expiration, validation)
│   │   └── scheduler.py            # Ordonnanceur APScheduler (expiration des réservations toutes les 5 min, rappels)
│   │
│   ├── routes/                     # Contrôleurs d'API REST (/api/v1)
│   │   ├── __init__.py             # Enregistrement et agrégation de l'ensemble des routeurs
│   │   ├── auth.py                 # Authentification (/auth/login, refresh, logout, me, change-password)
│   │   ├── public.py               # Endpoints ouverts (branches, catalogue, disponibilités, contact, OTP Brevo, préinscriptions)
│   │   ├── branches.py             # CRUD et administration des branches
│   │   ├── users.py                # Gestion des utilisateurs, rôles et réinitialisation de mot de passe
│   │   ├── permissions.py          # Gestion des permissions personnalisées et des accès inter-branches
│   │   ├── students.py             # Gestion des dossiers étudiants
│   │   ├── parents.py              # Gestion des parents et validation des liens de parenté
│   │   ├── teachers.py             # Gestion des enseignants, consultation de leurs groupes et séances
│   │   ├── courses.py              # Catalogue des formations
│   │   ├── levels.py               # Gestion des niveaux et grilles tarifaires
│   │   ├── groups.py               # Groupes d'élèves, affectation et modification stricte de capacité
│   │   ├── rooms.py                # Salles de classe et gestion des capacités
│   │   ├── schedules.py            # Créneaux d'emploi du temps hebdomadaires et vérification de conflits
│   │   ├── sessions.py             # Séances concrètes, génération par lot, annulation motivée et report
│   │   ├── closure_days.py         # Jours de congés et fermetures exceptionnelles
│   │   ├── enrollments.py          # Gestion des inscriptions, confirmations et prolongations de réservation
│   │   ├── documents.py            # Téléversement et téléchargement sécurisé sous contrôle de permissions
│   │   ├── attendance.py           # Feuilles d'émargement, pointage manuel individuel ou par lot
│   │   ├── payments.py             # Règlements, consultation des impayés et annulation comptable
│   │   ├── installments.py         # Suivi des échéances de paiement
│   │   ├── expenses.py             # Enregistrement des dépenses de fonctionnement
│   │   ├── cash_registers.py       # Caisses d'établissement et d'agents, mouvements associés
│   │   ├── fund_transfers.py       # Remises de fonds entre collaborateurs (création, confirmation, contestation)
│   │   ├── payroll.py              # Suivi des rémunérations enseignants et ordonnancement de paiement
│   │   ├── announcements.py        # Gestion des avis administratifs et publications
│   │   ├── notifications.py        # Consultation et acquittement des notifications utilisateur
│   │   ├── dashboard.py            # Tableaux de bord de synthèse (vue DG consolidée et vue Direction de Branche)
│   │   ├── reports.py              # Rapports analytiques périodiques filtrables
│   │   ├── imports.py              # Cycle d'importation Excel guidé (upload, preview, commit, rapport)
│   │   ├── exports.py              # Exportations de données en formats XLSX et PDF
│   │   ├── audit_logs.py           # Consultation filtrée de l'historique d'audit
│   │   └── settings.py             # Configuration globale et spécifique par branche
│   │
│   └── templates/                  # Modèles de documents PDF et modèles de feuilles Excel
│       └── receipts/               # Maquettes et utilitaires graphiques pour reçus officiels
│
└── tests/                          # Suite de tests unitaires et d'intégration automatisés
    ├── conftest.py                 # Fixtures Pytest (client de test HTTP, base de test, utilisateurs de test)
    ├── test_auth.py                # Tests d'authentification et de permissions
    ├── test_branch_scope.py        # Tests d'isolation hermétique entre branches
    ├── test_enrollment_capacity.py # Tests de gestion de capacité et concurrence sur réservations
    ├── test_schedule_conflicts.py  # Tests de détection de conflits (salle, enseignant, étudiant)
    ├── test_attendance.py          # Tests de pointage manuel et restrictions d'accès enseignant
    └── test_fund_transfers.py      # Tests du cycle de vie des remises de fonds et soldes de caisse
```

