from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import audit_service


class UserService:
    @staticmethod
    def get_users(
        db: Session,
        branch_id: Optional[int] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[User], int]:
        query = db.query(User).filter(User.is_archived.is_(False))
        if branch_id is not None:
            query = query.filter(User.branch_id == branch_id)
        if role is not None:
            query = query.filter(User.role == role)
        if is_active is not None:
            query = query.filter(User.is_active.is_(is_active))

        total = query.count()
        users = query.order_by(User.id.desc()).offset(skip).limit(limit).all()
        return users, total

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User:
        user = db.query(User).filter(User.id == user_id, User.is_archived.is_(False)).first()
        if not user:
            raise NotFoundError(message_key="resource_not_found")
        return user

    @staticmethod
    def create_user(db: Session, data: UserCreate, creator_id: Optional[int] = None) -> User:
        existing = db.query(User).filter(User.email == data.email.lower().strip()).first()
        if existing:
            raise ConflictError(message_key="conflict_error", details="Email already registered")

        user = User(
            email=data.email.lower().strip(),
            phone=data.phone,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            branch_id=data.branch_id,
            preferred_lang=data.preferred_lang,
            is_active=data.is_active,
        )
        db.add(user)
        db.flush()

        # Auto-provision teacher profile if role is teacher
        if user.role == "teacher" and user.branch_id:
            from decimal import Decimal
            from app.models.teacher import Teacher
            teacher_prof = Teacher(
                user_id=user.id,
                branch_id=user.branch_id,
                phone=user.phone,
                pay_mode="hourly",
                pay_rate=Decimal("0.00"),
            )
            db.add(teacher_prof)

        # Auto-provision cash register if role is agent
        if user.role == "agent" and user.branch_id:
            from app.services.cash_service import cash_service
            cash_service.get_or_create_user_register(db, user.branch_id, user.id, user.full_name)

        audit_service.log(
            db=db,
            action="create_user",
            entity="User",
            entity_id=user.id,
            user_id=creator_id,
            after_json={"email": user.email, "role": user.role, "branch_id": user.branch_id},
        )
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update_user(db: Session, user_id: int, data: UserUpdate, updater_id: Optional[int] = None) -> User:
        user = UserService.get_by_id(db, user_id)
        before = {"email": user.email, "role": user.role, "branch_id": user.branch_id, "is_active": user.is_active}

        if data.email and data.email.lower().strip() != user.email:
            existing = db.query(User).filter(User.email == data.email.lower().strip(), User.id != user_id).first()
            if existing:
                raise ConflictError(message_key="conflict_error", details="Email already in use")
            user.email = data.email.lower().strip()

        for field, value in data.model_dump(exclude_unset=True).items():
            if field != "email" and hasattr(user, field):
                setattr(user, field, value)

        db.flush()
        audit_service.log(
            db=db,
            action="update_user",
            entity="User",
            entity_id=user.id,
            user_id=updater_id,
            before_json=before,
            after_json={"email": user.email, "role": user.role, "branch_id": user.branch_id, "is_active": user.is_active},
        )
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def suspend_user(db: Session, user_id: int, is_active: bool, actor_id: Optional[int] = None) -> User:
        user = UserService.get_by_id(db, user_id)
        user.is_active = is_active
        audit_service.log(
            db=db,
            action="suspend_user" if not is_active else "reactivate_user",
            entity="User",
            entity_id=user.id,
            user_id=actor_id,
            after_json={"is_active": is_active},
        )
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def reset_password(db: Session, user_id: int, new_password: str, actor_id: Optional[int] = None) -> None:
        user = UserService.get_by_id(db, user_id)
        user.password_hash = hash_password(new_password)
        audit_service.log(
            db=db,
            action="reset_password_by_admin",
            entity="User",
            entity_id=user.id,
            user_id=actor_id,
        )
        db.commit()


user_service = UserService()

