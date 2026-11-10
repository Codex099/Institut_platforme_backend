# PRD — Backend : Plateforme de gestion d'un réseau d'établissements de formation

## 1. Contexte
Un réseau d'établissements (enseignement des langues et soutien scolaire) a besoin d'une plateforme centralisée : site public avec préinscription en ligne, et espaces privés pour la direction générale, les directeurs de branche, les agents administratifs, les enseignants, les étudiants et les parents. Le backend est le cœur unique du système : il porte toutes les données, les règles métier, la sécurité et les permissions. Le site web (autre PRD, autre agent) ne fait qu'appeler cette API.

## 2. Objectif de cette partie
Le backend doit :
- Exposer une API REST versionnée (`/api/v1`) consommée par le site web.
- Gérer l'authentification, les rôles, les permissions fines et l'isolation des données par branche.
- Gérer les branches, utilisateurs, étudiants, parents, enseignants.
- Gérer le catalogue (formations, niveaux, groupes, salles, emplois du temps, séances) avec détection de conflits.
- Gérer les préinscriptions, la réservation provisoire de places (avec expiration automatique) et la confirmation après paiement.
- Gérer les présences par **pointage manuel uniquement** (saisie par un utilisateur autorisé, avec règles anti-doublon et traçabilité). L'enseignant n'utilise la plateforme que pour cela. Pas de QR Code dans cette version.
- Gérer les finances internes : paiements (partiels), échéances, remises, reçus PDF, dépenses, caisses, remises/réceptions de fonds entre responsables, rémunération des enseignants.
- Gérer les horaires : affecter chaque groupe à une salle et à un enseignant sur des créneaux hebdomadaires (« le groupe X est dans la salle Y avec l'enseignant Z, tel jour de telle heure à telle heure »), détecter les conflits et produire les séances concrètes.
- Gérer les documents (upload sécurisé), notifications, annonces, journal d'audit.
- Fournir import/export Excel et exports PDF, plus des rapports filtrables.

Hors périmètre (géré par une autre partie/agent ou exclu du projet) :
- Aucune interface utilisateur : le backend ne rend aucune page HTML.
- Pas d'application mobile native, pas de paiement en ligne par carte, pas de visioconférence/cours en ligne.
- Pas de comptabilité légale certifiée : le module financier est un outil de suivi interne.

## 3. Stack technique imposée
- Python 3.11+, FastAPI, Pydantic v2
- SQLAlchemy 2.x (ORM) + Alembic (migrations)
- Base de données : PostgreSQL (production et dev ; SQLite interdit car les verrous de ligne sont requis pour les réservations)
- Authentification : JWT local (access token court + refresh token), hachage `argon2` ou `bcrypt`
- Tâches planifiées : APScheduler (expiration des réservations, rappels d'échéances)
- Fichiers : couche d'abstraction `StorageService` (disque local en dev, stockage objet compatible S3 en production)
- PDF : `reportlab` ou `weasyprint` (reçus, rapports)
- Excel : `openpyxl`
- Déploiement cible : serveur cloud (1 vCPU, 4 Go RAM, 50 Go SSD), HTTPS obligatoire, sauvegardes automatiques de la base

> Note : le backend est développé avec **FastAPI (Python)**. La mention de Node.js / NestJS dans le cahier des charges était indicative et sera remplacée par FastAPI ; la stack ci-dessus est celle imposée pour ce développement.

## 4. Structure de dossiers imposée
```
backend/
├── app/
│   ├── main.py                     # point d'entrée, montage des routers, CORS, handlers d'erreurs
│   ├── core/
│   │   ├── config.py               # settings via variables d'environnement
│   │   ├── security.py             # JWT, hashing, dépendances get_current_user
│   │   ├── permissions.py          # décorateurs/dépendances require_permission(resource, action)
│   │   ├── branch_scope.py         # filtrage automatique par branche selon l'utilisateur
│   │   ├── exceptions.py           # exceptions métier + mapping HTTP
│   │   └── i18n.py                 # messages d'erreur/notifications ar/en
│   ├── db/
│   │   ├── session.py              # engine, SessionLocal, get_db
│   │   ├── base.py                 # Base déclarative + mixins (timestamps, soft delete)
│   │   └── migrations/             # Alembic
│   ├── models/                     # 1 fichier SQLAlchemy par entité
│   │   ├── branch.py, user.py, permission.py, student.py, parent.py, teacher.py
│   │   ├── course.py, level.py, group.py, room.py, schedule.py, session.py, closure_day.py
│   │   ├── enrollment.py, document.py, attendance.py
│   │   ├── payment.py, installment.py, cash_register.py, expense.py, fund_transfer.py, teacher_payroll.py
│   │   ├── announcement.py, notification.py, contact_message.py
│   │   ├── audit_log.py, import_job.py, setting.py
│   ├── schemas/                    # schémas Pydantic request/response, même découpage que models/
│   ├── routes/                     # 1 router par ressource, AUCUNE logique métier
│   │   ├── auth.py, public.py, branches.py, users.py, permissions.py
│   │   ├── students.py, parents.py, teachers.py
│   │   ├── courses.py, levels.py, groups.py, rooms.py, schedules.py, sessions.py, closure_days.py
│   │   ├── enrollments.py, documents.py, attendance.py
│   │   ├── payments.py, installments.py, expenses.py, cash_registers.py, fund_transfers.py, payroll.py
│   │   ├── announcements.py, notifications.py
│   │   ├── dashboard.py, reports.py, imports.py, exports.py, audit_logs.py, settings.py
│   ├── services/                   # TOUTE la logique métier
│   │   ├── auth_service.py, user_service.py, permission_service.py
│   │   ├── enrollment_service.py   # réservation, expiration, confirmation, verrous
│   │   ├── schedule_service.py     # conflits salle/enseignant/étudiant, jours de fermeture, annulation et report de séances
│   │   ├── attendance_service.py   # règles de pointage manuel et anti-doublons
│   │   ├── payment_service.py, receipt_service.py, cash_service.py, fund_transfer_service.py, payroll_service.py
│   │   ├── document_service.py, storage_service.py
│   │   ├── import_service.py, export_service.py, report_service.py
│   │   ├── notification_service.py, audit_service.py
│   │   └── scheduler.py            # jobs APScheduler
│   └── templates/                  # modèles PDF (reçu, rapports) et fichiers Excel modèles
├── tests/                          # pytest, un fichier par module métier
├── alembic.ini
├── requirements.txt
├── .env.example
└── ARCHITECTURE.md                 # vue d'ensemble, générée et tenue à jour par l'agent
```

## 5. Instructions pour l'agent

### Architecture et conventions
- Respecte strictement la séparation routes / services / models / schemas. Une route ne contient que : validation d'entrée (schema), vérification de permission (dépendance), appel au service, retour de la réponse.
- Avant toute chose, crée un fichier `ARCHITECTURE.md` à la racine du projet contenant l'arborescence complète (dossiers + fichiers) avec, pour chaque fichier important, une description d'une ligne de son rôle. Ce fichier doit être tenu à jour à chaque ajout ou suppression de fichier significatif. Il sert de vue d'ensemble rapide pour ne pas avoir à relire tout le code à chaque nouvelle session.
- Nomme les routes, tables et champs en anglais, en `snake_case`. Les routes sont en kebab-case pluriel (`/fund-transfers`). Tout est préfixé `/api/v1`.
- Pagination standard (`page`, `page_size`, max 100) et filtres sur toutes les listes.
- Gère les erreurs avec des exceptions HTTP explicites (400/401/403/404/409/422/500) et un format JSON uniforme `{ "code": "...", "message": "..." }`. Jamais de stack trace renvoyée au client.
- Toutes les valeurs sensibles (secrets JWT, DSN base, clés de stockage) passent par variables d'environnement. Documente-les dans `.env.example`.
- Montants : `Numeric(12, 2)`, jamais de `float`. Dates en UTC en base.
- Suppression : archivage logique (`is_archived`/`deleted_at`) pour les données métier ; les opérations financières confirmées ne se suppriment jamais, elles s'annulent par une opération traçable.

### Sécurité (obligatoire)
- Contrôle d'accès **côté serveur** sur chaque route : rôle + permission (`view`, `create`, `update`, `delete_archive`, `validate`, `export`) + périmètre de branche.
- Un utilisateur non Directeur Général ne voit que les données de sa branche, sauf accès inter-branches explicite accordé par le DG (table `branch_access_grants`). Applique ce filtre dans une dépendance centrale (`branch_scope.py`), jamais route par route à la main.
- Le Directeur Général (`super_admin`) a tous les droits sur toutes les branches ; toute intervention sensible est écrite dans `audit_logs`.
- Un enseignant n'accède qu'aux groupes qui lui sont affectés, et **uniquement pour le suivi des présences** : liste de ses groupes, liste des étudiants de ces groupes (nom, numéro, photo), ses séances, enregistrement et historique des présences/absences/retards. Il n'a AUCUN accès aux paiements, finances, rémunération, documents des dossiers, ni aux données des autres groupes. Refuse (403) toute autre route pour le rôle `teacher`. Un étudiant n'accède qu'à ses données. Un parent n'accède qu'aux enfants dont l'association a été validée.
- Journalise dans `audit_logs` (utilisateur, action, entité, avant/après JSON, IP, date) : connexions, création/modification de comptes et permissions, paiements, annulations, remises de fonds, modifications manuelles de présence, modifications d'horaires, interventions du DG.
- Limitation de débit sur `/auth/login` et sur les endpoints publics (préinscription, contact). Validation stricte des uploads (type MIME, extension, taille max configurable), noms de fichiers générés côté serveur, jamais de chemin fourni par le client.
- Les fichiers ne sont servis que via un endpoint authentifié qui vérifie les permissions (pas d'URL publique directe), sauf documents explicitement publics.

### Règles métier critiques
1. **Limites des groupes (règle personnalisable)** : la taille maximale d'un groupe n'est pas figée dans le code, elle est définie et modifiable par le Directeur Général et par le directeur de branche (sur sa branche), jamais par un agent ni un enseignant (permission dédiée `groups:set_capacity`).
   - Valeur par défaut en cascade : `groups.capacity` (si définie) → `levels.default_capacity` → paramètre `default_group_capacity` de la branche → paramètre du réseau. La capacité d'un groupe peut être modifiée à tout moment.
   - Refuse (409) de réduire la capacité sous le nombre de places déjà occupées (inscriptions `confirmed` + réservations `pending_payment` non expirées).
   - Le directeur de branche et le DG peuvent exceptionnellement inscrire au-delà de la limite avec `allow_over_capacity=true` et un motif obligatoire ; l'agent ne le peut jamais. Chaque dépassement et chaque changement de limite sont tracés dans `audit_logs`.
   - Politique salle/groupe configurable par branche (paramètre `room_capacity_policy` : `none`, `warn` ou `block`) : compare la capacité de la salle à celle du groupe lors de l'affectation d'un créneau. Par défaut `warn`.
   - La capacité effective est celle qu'utilisent la réservation, la préinscription en ligne et l'affichage des places restantes.
   **Réservation provisoire / capacité des groupes** :
   - La préinscription crée un dossier `enrollment` au statut `pending_payment` avec `reserved_until = now + settings.reservation_hours`.
   - Les places occupées d'un groupe = inscriptions `confirmed` + `pending_payment` non expirées.
   - La création d'une réservation s'exécute dans une transaction avec `SELECT ... FOR UPDATE` sur la ligne du groupe pour empêcher le dépassement de capacité et la double réservation de la dernière place.
   - Un job planifié (toutes les 5 minutes) passe en `expired` les réservations dépassées, libère la place et notifie. Une expiration est aussi vérifiée à la lecture et lors d'une tentative de confirmation.
   - Aucune inscription n'est `confirmed` sans paiement enregistré (au minimum le montant d'acompte défini en configuration).
2. **Affectation horaire (cœur de l'emploi du temps)** : un créneau (`schedule_slot`) affecte un groupe à une salle et à un enseignant pour un jour de la semaine et une plage horaire. L'enseignant d'un groupe et sa salle se déduisent uniquement de ses créneaux (un groupe peut avoir des salles ou des enseignants différents selon les jours). La comparaison entre la capacité de la salle et celle du groupe dépend de la politique `room_capacity_policy` (voir règle 1). Les séances concrètes sont générées à partir des créneaux.
   **Conflits d'emploi du temps** : refuse (409) toute affectation/séance qui chevauche une autre séance de la même salle ou du même enseignant (même jour, plages horaires qui se recouvrent). Retourne le détail du conflit.
   - **Conflit côté étudiant** : refuse (409) l'inscription (création ou confirmation d'un `enrollment`) d'un étudiant à un groupe dont les créneaux chevauchent ceux d'un autre groupe où il est déjà inscrit (`confirmed` ou `pending_payment` non expirée). Retourne les créneaux en conflit. Le directeur de branche (permission `validate`) peut forcer l'inscription avec `allow_overlap=true` ; ce forçage est tracé dans `audit_logs`.
   - **Jours de fermeture** : la table `closure_days` définit les jours fériés et vacances (pour tout le réseau ou pour une branche). `POST /sessions/generate` ignore ces jours et retourne la liste des dates ignorées. Créer ou étendre une fermeture qui touche des séances déjà générées passe ces séances en `cancelled` (motif = nom de la fermeture) et notifie les personnes concernées.
   - **Annulation d'une séance** : passe la séance en `cancelled` avec un motif obligatoire, par un utilisateur autorisé (directeur de branche, agent autorisé, DG). Interdit sur une séance déjà `held`. Une séance annulée n'accepte aucun pointage, n'est jamais comptée comme absence, n'est pas comptée dans la rémunération de l'enseignant (modes `hourly` et `per_session`) et reste visible dans l'emploi du temps avec son statut.
   - **Report d'une séance** : crée une nouvelle séance (nouvelle date, heure, salle, enseignant éventuellement modifiés) liée à l'originale par `rescheduled_from_session_id` ; l'originale passe en `rescheduled`. Applique les mêmes contrôles de conflits (salle, enseignant, étudiants du groupe) et refuse un report sur un jour de fermeture.
   - Statuts de séance : `planned`, `held`, `cancelled`, `rescheduled`.
3. **Présences** :
   - Méthode unique : pointage manuel par un utilisateur autorisé (enseignant sur ses groupes, directeur de branche, agent autorisé, DG). Aucun QR Code dans cette version ; le champ `method` est conservé (valeur `manual`) pour permettre d'ajouter d'autres méthodes plus tard sans migration lourde.
   - Vérifie à chaque enregistrement : l'utilisateur a le droit de pointer ce groupe, l'étudiant a une inscription `confirmed` au groupe de la séance, la séance existe et n'est pas annulée, unicité `(session_id, student_id)` (un nouveau pointage met à jour la ligne existante au lieu de la dupliquer).
   - L'enseignant ne peut pointer que ses propres séances, pendant la journée de la séance (fenêtre de modification configurable) ; au-delà, seul le directeur de branche ou le DG peut corriger.
   - Toute modification manuelle est tracée (qui, quand, ancienne/nouvelle valeur).
   - Statuts : `present`, `absent`, `late`.
4. **Remises de fonds** (agent → directeur de branche ; directeur de branche → DG) :
   - L'émetteur crée l'opération (`pending`) avec montant, date, motif. Le destinataire confirme la réception (`confirmed`) ou la conteste (`contested`, motif obligatoire). Annulation (`cancelled`) uniquement par une procédure autorisée et tracée.
   - Génère un numéro de référence unique, un reçu PDF à la confirmation, et écrit l'opération dans les historiques des deux parties.
   - Une opération `confirmed` est immuable ; toute correction passe par une opération de contrepartie tracée.
   - À la confirmation, les soldes de caisse concernés sont mis à jour dans la même transaction.
5. **Paiements** : paiements partiels autorisés, calcul du reste à payer, échéanciers, remises/réductions soumises à une permission `validate`. Chaque paiement génère un reçu numéroté séquentiel par branche. Un paiement ne se supprime pas : il s'annule via une écriture de contrepartie.
6. **Rémunération des enseignants** : modes `hourly`, `per_session`, `fixed`, calcul par période à partir des séances effectivement tenues (statut `held` ; les séances `cancelled` ne sont jamais comptées), paramétrable par contrat enseignant.
7. **Import Excel** : processus en 3 temps — `upload + validation` (détection de doublons, erreurs ligne par ligne), `prévisualisation`, `commit`. Fournit un rapport des lignes importées et rejetées. Jamais d'écriture en base avant le `commit`.
8. **Notifications** : créées via `notification_service` pour préinscription, réservation en attente, paiement enregistré, échéance proche, absence, annulation ou report d'une séance (envoyée à l'enseignant, aux étudiants du groupe et à leurs parents), nouveau jour de fermeture, changement d'horaire, remise de fonds, alertes admin. Stockées en base, lues via l'API.
9. **Langues** : les messages d'erreur et notifications respectent l'en-tête `Accept-Language` (`ar`, `en`), avec l'anglais comme langue par défaut. Seules deux langues sont gérées : arabe et anglais (pas de français). Les contenus publics (formations, actualités) stockent les champs textuels traduisibles (`name_ar`, `name_en`).

### Rôles
`super_admin` (Directeur Général), `branch_director`, `agent`, `teacher`, `student`, `parent`. Les permissions par défaut de chaque rôle sont définies dans `permissions.py`, surchargeables par utilisateur via `user_permissions`. Le rôle `teacher` est volontairement limité à la consultation de ses groupes et à la gestion des présences.

## 6. Modèle de données
Toutes les tables ont `id` (UUID ou BigInt), `created_at`, `updated_at`. `branch_id` est présent sur toute table métier rattachée à une branche.

### Organisation et accès
| Table | Champs clés | Contraintes / relations |
|---|---|---|
| branches | name, address, city, phone, email, is_active, director_id | director_id → users |
| users | email (unique), phone, password_hash, full_name, role, branch_id (nullable pour DG), is_active, preferred_lang, last_login_at | role enum ; unique email |
| user_permissions | user_id, resource, action | action ∈ view/create/update/delete_archive/validate/export |
| branch_access_grants | user_id, branch_id, granted_by, expires_at | accès inter-branches accordé par le DG |
| audit_logs | user_id, action, entity, entity_id, before_json, after_json, ip, created_at | append-only |
| settings | key, value, branch_id (nullable) | ex : reservation_hours, deposit_min, default_group_capacity, room_capacity_policy (none/warn/block) |

### Personnes
| Table | Champs clés | Contraintes / relations |
|---|---|---|
| students | user_id (nullable), branch_id, student_number (unique), first_name, last_name, birth_date, gender, phone, address, photo_document_id, status | status : candidate / active / archived |
| parents | user_id, full_name, phone, email, address | |
| student_parents | student_id, parent_id, relationship, is_validated, validated_by, validated_at | un parent → plusieurs enfants |
| teachers | user_id, branch_id, phone, specialties, pay_mode (hourly/per_session/fixed), pay_rate, contract_notes | |

### Pédagogie
| Table | Champs clés | Contraintes / relations |
|---|---|---|
| courses | branch_id, type (language/tutoring), name_ar/en, subject, description_*, is_published | formation (langue ou matière de soutien) |
| levels | course_id, name_*, price, registration_fee, program_description, default_capacity | default_capacity optionnelle |
| rooms | branch_id, name, capacity | |
| groups | level_id, branch_id, name, capacity, capacity_updated_by, capacity_updated_at, start_date, end_date, status | capacity > 0, modifiable uniquement par DG / directeur de branche ; ni salle ni enseignant fixes : ils sont définis par les créneaux |
| schedule_slots | group_id, room_id, teacher_id, weekday, start_time, end_time, valid_from, valid_to | **affectation horaire** : relie un groupe à une salle et à un enseignant sur un créneau hebdomadaire ; contrôle de conflits |
| sessions | group_id, room_id, teacher_id, session_date, start_time, end_time, status (planned/held/cancelled/rescheduled), cancel_reason, cancelled_by, cancelled_at, rescheduled_from_session_id | séance concrète ; report lié à l'originale |
| closure_days | branch_id (nullable = tout le réseau), name_ar/en, start_date, end_date, reason, created_by | jours fériés et vacances ; end_date ≥ start_date |

### Inscriptions et documents
| Table | Champs clés | Contraintes / relations |
|---|---|---|
| enrollments | student_id, group_id, branch_id, source (online/onsite), status (pending_payment/confirmed/expired/cancelled), reserved_until, total_fee, discount_amount, discount_reason, created_by, confirmed_by, confirmed_at | index (group_id, status) |
| documents | owner_type, owner_id, kind (id/photo/registration/proof/admin/pedagogical), file_key, original_name, mime, size, uploaded_by, visibility | accès filtré par permissions |

### Présences
| Table | Champs clés | Contraintes / relations |
|---|---|---|
| attendance | session_id, student_id, status, method (manual), recorded_by, recorded_at, modified_by, modified_at | unique (session_id, student_id) |

### Finances
| Table | Champs clés | Contraintes / relations |
|---|---|---|
| payments | enrollment_id, branch_id, amount, method (cash/transfer/check), receipt_number (unique par branche), received_by, paid_at, status (valid/cancelled), cancelled_by, cancel_reason | |
| installments | enrollment_id, due_date, amount, status (due/paid/late) | |
| cash_registers | branch_id, owner_user_id, name, balance | une caisse par branche + une par agent |
| cash_movements | register_id, type (in/out), amount, source_type, source_id, created_by | historique des mouvements |
| expenses | branch_id, category, amount, expense_date, description, receipt_document_id, created_by | |
| fund_transfers | reference (unique), branch_id, from_user_id, to_user_id, amount, reason, status (pending/confirmed/contested/cancelled), created_at, confirmed_at, contested_reason, cancelled_by | |
| teacher_payroll | teacher_id, period_start, period_end, hours, sessions_count, amount_due, amount_paid, status, paid_at | |

### Communication
| Table | Champs clés |
|---|---|
| announcements | branch_id (nullable = réseau), title_*, body_*, audience, is_public, published_at |
| notifications | user_id, type, title, body, data_json, read_at |
| contact_messages | name, email, phone, message, branch_id, status |
| import_jobs | type, branch_id, status, file_key, report_json, created_by |

## 7. Routes API à implémenter
Légende Auth : P = public ; A = authentifié (permission selon rôle/branche).

### Auth et public
| Méthode | Route | Description | Auth |
|---|---|---|---|
| POST | /api/v1/auth/login | Connexion (access + refresh) | P |
| POST | /api/v1/auth/refresh | Renouvelle le token | P |
| POST | /api/v1/auth/logout | Invalide le refresh token | A |
| GET | /api/v1/auth/me | Profil, rôle, permissions, branche | A |
| POST | /api/v1/auth/change-password | Changement de mot de passe | A |
| GET | /api/v1/public/branches | Liste des branches actives | P |
| GET | /api/v1/public/courses | Catalogue (filtres branche, type, niveau) avec tarifs | P |
| GET | /api/v1/public/groups | Groupes disponibles et places restantes | P |
| GET | /api/v1/public/announcements | Actualités et annonces publiques | P |
| POST | /api/v1/public/contact | Formulaire de contact | P |
| POST | /api/v1/public/preregistrations | Préinscription en ligne (crée étudiant + dossier + réservation) | P |
| POST | /api/v1/public/preregistrations/{id}/documents | Upload des documents du candidat (jeton de dossier) | P |
| GET | /api/v1/public/preregistrations/{reference} | Suivi du statut d'un dossier | P |

### Administration
| Méthode | Route | Description | Auth |
|---|---|---|---|
| GET/POST | /api/v1/branches | Lister / créer des branches | A (DG) |
| GET/PUT/PATCH | /api/v1/branches/{id} | Détail, modification, activation/désactivation, affectation du directeur | A |
| GET/POST | /api/v1/users | Lister / créer des comptes | A |
| GET/PUT | /api/v1/users/{id} | Détail / modification, affectation de branche et de rôle | A |
| POST | /api/v1/users/{id}/reset-password | Réinitialisation | A |
| POST | /api/v1/users/{id}/suspend | Suspension / réactivation | A |
| GET/PUT | /api/v1/users/{id}/permissions | Lire / définir les permissions | A (DG) |
| POST/DELETE | /api/v1/branch-access-grants | Accorder / retirer un accès inter-branches | A (DG) |
| GET | /api/v1/audit-logs | Journal d'activité filtrable | A |
| GET/PUT | /api/v1/settings | Paramètres (durée de réservation, acompte, fenêtre de modification des présences, capacité par défaut des groupes, politique salle/groupe) | A (DG ; directeur de branche pour sa branche) |

### Personnes
| Méthode | Route | Description | Auth |
|---|---|---|---|
| GET/POST | /api/v1/students | Lister / créer un dossier étudiant | A |
| GET/PUT/PATCH | /api/v1/students/{id} | Détail / modification / archivage | A |
| GET/POST | /api/v1/parents | Lister / créer | A |
| POST | /api/v1/parents/{id}/children | Associer un enfant (en attente de validation) | A |
| POST | /api/v1/parents/{id}/children/{student_id}/validate | Valider l'association | A |
| GET/POST | /api/v1/teachers | Lister / créer | A |
| GET/PUT | /api/v1/teachers/{id} | Détail / modification (mode et taux de rémunération) | A |
| GET | /api/v1/teachers/me/groups | Groupes pour lesquels l'enseignant connecté a au moins un créneau actif | A (teacher) |
| GET | /api/v1/teachers/me/sessions | Séances du jour / de la semaine à pointer | A (teacher) |
| GET | /api/v1/students/me, /api/v1/parents/me/children | Espace étudiant / parent | A |

### Pédagogie
| Méthode | Route | Description | Auth |
|---|---|---|---|
| CRUD | /api/v1/courses, /api/v1/levels, /api/v1/rooms | Formations, niveaux, salles | A |
| CRUD | /api/v1/groups | Groupes (niveau, capacité, dates) ; la capacité n'est modifiable que par le DG et le directeur de branche | A |
| PATCH | /api/v1/groups/{id}/capacity | Modifie la limite du groupe (refus si inférieure aux places occupées), tracé dans le journal | A (DG, directeur de branche) |
| GET | /api/v1/groups/{id}/students | Liste des étudiants du groupe | A |
| GET | /api/v1/groups/{id}/availability | Places restantes | A |
| CRUD | /api/v1/schedules | Créneaux hebdomadaires, avec contrôle de conflits | A |
| POST | /api/v1/schedules/check-conflicts | Vérification préalable d'un créneau (salle, enseignant, étudiants du groupe, jours de fermeture) | A |
| GET | /api/v1/schedules/timetable | Emploi du temps par groupe / enseignant / salle / étudiant | A |
| CRUD | /api/v1/sessions | Séances concrètes | A |
| POST | /api/v1/sessions/generate | Génère les séances à partir des créneaux sur une période (ignore les jours de fermeture) | A |
| POST | /api/v1/sessions/{id}/cancel | Annule une séance (motif obligatoire) et notifie | A |
| POST | /api/v1/sessions/{id}/reschedule | Reporte une séance (nouvelle date/heure/salle) avec contrôle des conflits et notification | A |
| CRUD | /api/v1/closure-days | Jours fériés et vacances (réseau ou branche) | A (DG pour le réseau, directeur de branche pour sa branche) |

### Inscriptions, documents, présences
| Méthode | Route | Description | Auth |
|---|---|---|---|
| GET/POST | /api/v1/enrollments | Lister / créer (préinscription sur place, réservation provisoire) | A |
| GET | /api/v1/enrollments/{id} | Détail du dossier | A |
| POST | /api/v1/enrollments/{id}/confirm | Confirmer après paiement | A |
| POST | /api/v1/enrollments/{id}/cancel | Annuler et libérer la place | A |
| POST | /api/v1/enrollments/{id}/extend-reservation | Prolonger la réservation | A |
| POST | /api/v1/documents | Upload d'un document lié à un dossier | A |
| GET | /api/v1/documents/{id}/download | Téléchargement contrôlé | A |
| DELETE | /api/v1/documents/{id} | Archivage du document | A |
| GET | /api/v1/sessions/{id}/attendance | Liste de présence d'une séance | A |
| POST | /api/v1/attendance/manual | Pointage manuel d'une séance (un ou plusieurs étudiants, en lot) | A |
| PATCH | /api/v1/attendance/{id} | Correction manuelle tracée | A |
| GET | /api/v1/students/{id}/attendance | Historique de présences | A |

### Finances
| Méthode | Route | Description | Auth |
|---|---|---|---|
| GET/POST | /api/v1/payments | Lister / enregistrer un paiement | A |
| POST | /api/v1/payments/{id}/cancel | Annulation tracée | A |
| GET | /api/v1/payments/{id}/receipt | Reçu PDF | A |
| GET | /api/v1/payments/unpaid | Impayés et sommes restantes | A |
| GET/POST | /api/v1/installments | Échéances | A |
| GET/POST | /api/v1/expenses | Dépenses | A |
| GET | /api/v1/cash-registers | Caisses et soldes | A |
| GET | /api/v1/cash-registers/{id}/movements | Mouvements | A |
| GET/POST | /api/v1/fund-transfers | Lister / créer une remise de fonds | A |
| POST | /api/v1/fund-transfers/{id}/confirm | Confirmer la réception | A |
| POST | /api/v1/fund-transfers/{id}/contest | Contester | A |
| POST | /api/v1/fund-transfers/{id}/cancel | Annuler (procédure autorisée) | A |
| GET | /api/v1/fund-transfers/{id}/receipt | Reçu PDF | A |
| GET/POST | /api/v1/payroll | États et calcul de rémunération des enseignants | A (DG, directeur de branche) |
| POST | /api/v1/payroll/{id}/pay | Enregistrer le paiement d'un enseignant | A |

### Communication, tableaux de bord, rapports
| Méthode | Route | Description | Auth |
|---|---|---|---|
| CRUD | /api/v1/announcements | Annonces | A |
| GET | /api/v1/notifications | Mes notifications | A |
| POST | /api/v1/notifications/{id}/read, /api/v1/notifications/read-all | Marquer comme lues | A |
| GET | /api/v1/dashboard/general | Tableau de bord DG (agrégats réseau, comparaison des branches, alertes) | A (DG) |
| GET | /api/v1/dashboard/branch | Tableau de bord de la branche | A |
| GET | /api/v1/reports/{type} | Rapports filtrables (période, branche, formation, groupe, utilisateur) : journalier, mensuel, financier, présences | A |
| GET | /api/v1/exports/{resource}?format=xlsx|pdf | Exportation | A |
| GET | /api/v1/imports/templates/{resource} | Modèle Excel téléchargeable | A |
| POST | /api/v1/imports | Upload + validation | A |
| GET | /api/v1/imports/{id}/preview | Prévisualisation, erreurs, doublons | A |
| POST | /api/v1/imports/{id}/commit | Validation de l'importation | A |
| GET | /api/v1/imports/{id}/report | Rapport importés / rejetés | A |

## 8. Critères de complétion
- [ ] `ARCHITECTURE.md` créé dès l'initialisation et à jour
- [ ] Structure routes / services / models / schemas respectée, aucune logique métier dans les routes
- [ ] Migrations Alembic opérationnelles, toutes les tables créées
- [ ] Authentification JWT (login, refresh, logout) fonctionnelle, rôles et permissions appliqués côté serveur
- [ ] Isolation par branche vérifiée par tests (un directeur ne voit pas une autre branche sans grant ; le DG voit tout)
- [ ] Enseignant limité à ses groupes ET aux seules routes de présence (liste des groupes/étudiants, séances, pointage) ; 403 vérifié par tests sur paiements, finances et rémunération
- [ ] Étudiant limité à ses données, parent aux enfants validés
- [ ] Préinscription en ligne et sur place : dossier + réservation provisoire + statut `pending_payment`
- [ ] Limites de groupes personnalisables par le DG et le directeur de branche (capacité par groupe, par niveau, par branche), refus de descendre sous les places occupées, dépassement exceptionnel motivé et tracé, interdit à l'agent
- [ ] Politique salle/groupe (`none` / `warn` / `block`) configurable par branche
- [ ] Test de concurrence : deux réservations simultanées de la dernière place → une seule réussit
- [ ] Expiration automatique des réservations (job planifié) et libération de la place
- [ ] Confirmation d'inscription impossible sans paiement
- [ ] Détection des conflits salle/enseignant (409 avec détail)
- [ ] Contrôle de chevauchement d'un même étudiant entre deux groupes (409, forçage par le directeur tracé)
- [ ] Jours fériés et vacances : `closure_days` géré, ignoré par `sessions/generate`, annulation automatique des séances déjà générées concernées
- [ ] Annulation et report de séance avec motif, lien vers la séance d'origine, contrôle des conflits et notification de l'enseignant, des étudiants et des parents
- [ ] Séance annulée : aucun pointage possible, jamais comptée comme absence ni dans la rémunération (tests)
- [ ] Présences : pointage manuel (présent / absent / en retard) avec règles anti-doublon, droits par rôle et modifications tracées
- [ ] Paiements partiels, échéances, reste à payer, reçus PDF numérotés
- [ ] Remises de fonds : workflow pending → confirmed/contested/cancelled, reçu PDF, soldes de caisse cohérents, immuabilité des opérations confirmées
- [ ] Dépenses, caisses, mouvements financiers, rémunération des enseignants (3 modes)
- [ ] Upload sécurisé de documents avec téléchargement contrôlé par permissions
- [ ] Import Excel en 3 temps (validation / prévisualisation / commit) avec rapport, exports Excel et PDF
- [ ] Notifications générées pour tous les événements listés au cahier des charges
- [ ] Journal d'audit alimenté pour toutes les opérations sensibles et interventions du DG
- [ ] Messages d'erreur et notifications disponibles en ar / en
- [ ] Tests pytest sur les règles critiques (capacité, conflits, présences, finances, permissions)
- [ ] `.env.example` complet, documentation Swagger/OpenAPI accessible, HTTPS et CORS configurés pour le déploiement
