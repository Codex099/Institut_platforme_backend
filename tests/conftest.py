import os
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.branch import Branch
from app.models.cash_register import CashRegister
from app.models.course import Course
from app.models.group import Group
from app.models.level import Level
from app.models.room import Room
from app.models.teacher import Teacher
from app.models.user import User

# Use in-memory SQLite with StaticPool for fast isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def seed_data(db):
    """Seed initial branches, users, and core configuration for tests."""
    # 1. Branches
    branch1 = Branch(name="École Chlef Centre", code="CHL", city="Chlef", is_active=True)
    branch2 = Branch(name="École Alger", code="ALG", city="Alger", is_active=True)
    db.add_all([branch1, branch2])
    db.flush()

    # 2. Users for each role
    dg_user = User(
        email="dg@ecole.dz",
        password_hash=hash_password("dgpassword"),
        full_name="Directeur Général",
        role="super_admin",
        branch_id=None,
        is_active=True,
    )
    bd_user = User(
        email="directeur.chlef@ecole.dz",
        password_hash=hash_password("bdpassword"),
        full_name="Directeur Chlef",
        role="branch_director",
        branch_id=branch1.id,
        is_active=True,
    )
    agent_user = User(
        email="agent.chlef@ecole.dz",
        password_hash=hash_password("agentpassword"),
        full_name="Agent Chlef",
        role="agent",
        branch_id=branch1.id,
        is_active=True,
    )
    teacher_user = User(
        email="teacher@ecole.dz",
        password_hash=hash_password("teacherpassword"),
        full_name="Professeur Ahmed",
        role="teacher",
        branch_id=branch1.id,
        is_active=True,
    )
    db.add_all([dg_user, bd_user, agent_user, teacher_user])
    db.flush()

    # 3. Teacher profile
    teacher_profile = Teacher(
        user_id=teacher_user.id,
        branch_id=branch1.id,
        phone="0550112233",
        specialties="Anglais",
        pay_mode="hourly",
        pay_rate=Decimal("1500.00"),
    )
    db.add(teacher_profile)

    # 4. Cash registers
    reg_branch = CashRegister(branch_id=branch1.id, owner_user_id=None, name="Caisse Principale Chlef", balance=Decimal("100000.00"))
    reg_agent = CashRegister(branch_id=branch1.id, owner_user_id=agent_user.id, name="Caisse Agent Chlef", balance=Decimal("50000.00"))
    db.add_all([reg_branch, reg_agent])

    # 5. Course, Level, Room, Group
    course = Course(branch_id=branch1.id, type="language", name_en="English B1", name_ar="إنجليزية B1", subject="English")
    db.add(course)
    db.flush()

    level = Level(course_id=course.id, name_en="Intermediate", name_ar="متوسط", price=Decimal("15000.00"), registration_fee=Decimal("2000.00"), default_capacity=10)
    db.add(level)
    db.flush()

    room = Room(branch_id=branch1.id, name="Salle 01", capacity=12)
    db.add(room)
    db.flush()

    group = Group(level_id=level.id, branch_id=branch1.id, name="Groupe A1", capacity=2)  # Small capacity to test limit easily
    db.add(group)

    db.commit()

    return {
        "branch1": branch1,
        "branch2": branch2,
        "dg": dg_user,
        "director": bd_user,
        "agent": agent_user,
        "teacher": teacher_user,
        "teacher_profile": teacher_profile,
        "course": course,
        "level": level,
        "room": room,
        "group": group,
    }


def make_auth_headers(user: User) -> dict:
    token = create_access_token(
        subject=str(user.id),
        role=user.role,
        branch_id=user.branch_id,
        extra_claims={"granted_branches": []},
    )
    return {"Authorization": f"Bearer {token}"}

