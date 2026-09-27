# ============================================================
# backend/app/routers/admin.py
# ============================================================

import datetime
import hashlib
import secrets
from typing import Any

import pyotp
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.mailer import send_verification_email
from app.models import Project, User, UserRole
from app.admin_security import (
    get_current_admin,
    get_enrolling_admin,
    issue_admin_access_token,
    issue_enrollment_token,
    login_throttle,
    qr_svg,
    require_confirmation,
    throttle_keys,
    verify_totp,
)
from app.schemas.auth import UserLogin
from app.security import get_password_hash, verify_password
from app.security_policy import protect_totp_secret


router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================
# Schemas locaux admin
# ============================================================

class AdminUserRoleUpdate(BaseModel):
    role: UserRole


class AdminUserStatusUpdate(BaseModel):
    is_active: bool

class AdminCreateAdminRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    # Sprint 7.1: admin passwords are long (12+ characters by default).
    password: str = Field(min_length=settings.ADMIN_MIN_PASSWORD_LENGTH, max_length=128)


class AdminLoginResponse(BaseModel):
    """Either a session (access_token) or the 2FA enrollment step."""

    access_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = None
    requires_2fa_setup: bool = False
    enrollment_token: str | None = None


class AdminTwoFactorSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str
    qr_svg: str


class AdminTwoFactorCode(BaseModel):
    code: str = Field(min_length=6, max_length=8)
# ============================================================
# Sécurité admin
# ============================================================

async def require_admin(
    admin: User = Depends(get_current_admin),
) -> User:
    """
    Guard of every admin route (Sprint 7.1): admin-audience token only,
    active admin with 2FA enabled. User tokens from /auth/login are refused.
    Sensitive actions use ``require_confirmation`` (fresh TOTP code) instead.
    """
    return admin


# ============================================================
# Helpers email verification admin
# ============================================================

def hash_email_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_email_verification_token() -> str:
    return secrets.token_urlsafe(32)


def set_email_verification_token(user: User) -> str:
    token = create_email_verification_token()

    user.email_verification_token_hash = hash_email_verification_token(token)
    user.email_verification_expires_at = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
    )

    return token


def queue_verification_email(
    background_tasks: BackgroundTasks,
    email: str,
    token: str,
) -> None:
    verification_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    background_tasks.add_task(
        send_verification_email,
        email,
        verification_link,
    )



# ============================================================
# Helpers serialization
# ============================================================

def role_to_str(role: Any) -> str:
    return role.value if hasattr(role, "value") else str(role)


def serialize_user(user: User, project_count: int | None = None) -> dict:
    data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": role_to_str(user.role),
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "is_two_factor_enabled": user.is_two_factor_enabled,
        "created_at": user.created_at,
    }

    if project_count is not None:
        data["project_count"] = project_count

    return data


def serialize_project(
    project: Project,
    owner_email: str | None = None,
    owner_name: str | None = None,
) -> dict:
    return {
        "id": project.id,
        "title": project.title,
        "description": project.description,
        "industry": project.industry,
        "market_region": project.market_region,
        "status": project.status,
        "startup_score": project.startup_score,
        "analysis_status": project.analysis_status,
        "analysis_step": project.analysis_step,
        "analysis_progress": project.analysis_progress,
        "analysis_error": project.analysis_error,
        "analysis_started_at": project.analysis_started_at,
        "analysis_completed_at": project.analysis_completed_at,
        "user_id": project.user_id,
        "owner_email": owner_email,
        "owner_name": owner_name,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
    }


def setting_is_configured(*names: str) -> bool:
    for name in names:
        value = getattr(settings, name, None)
        if value:
            return True
    return False


def get_setting_value(*names: str) -> str | None:
    for name in names:
        value = getattr(settings, name, None)
        if value:
            return str(value)
    return None


# ============================================================
# 1. Login admin séparé
# ============================================================

def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _session(user: User) -> dict:
    return {
        "access_token": issue_admin_access_token(user.email),
        "token_type": "bearer",
        "expires_in": settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "requires_2fa_setup": False,
    }


@router.post("/login", response_model=AdminLoginResponse, response_model_exclude_none=True)
async def admin_login(
    request: Request,
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Admin login, 2FA mandatory (Sprint 7.1).

    - password + valid TOTP -> 15-minute admin token, no refresh cookie;
    - admin without 2FA -> enrollment token only (2FA setup, nothing else);
    - failed password / TOTP attempts are limited per account and per IP.
    """
    keys = throttle_keys(user_in.email, _client_ip(request))
    wait = await login_throttle.retry_after(keys)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez plus tard.",
            headers={"Retry-After": str(wait)},
        )

    user = (await db.execute(select(User).where(User.email == user_in.email))).scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(user_in.password, user.hashed_password):
        await login_throttle.record_failure(keys)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect.")

    if user.role != UserRole.ADMIN or not user.is_active or not user.is_email_verified:
        # Same answer for every refusal: never reveal which accounts are admins.
        await login_throttle.record_failure(keys)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs.")

    if not user.is_two_factor_enabled:
        # First admin login (or 2FA reset): enrol before any access.
        return {
            "requires_2fa_setup": True,
            "enrollment_token": issue_enrollment_token(user.email),
        }

    if not user_in.two_factor_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"reason": "totp_required", "message": "Code de double authentification requis."},
        )
    if not verify_totp(user, user_in.two_factor_code):
        await login_throttle.record_failure(keys)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"reason": "totp_invalid", "message": "Code de double authentification invalide."},
        )

    await login_throttle.reset(keys)
    return _session(user)


@router.post("/2fa/setup", response_model=AdminTwoFactorSetupResponse)
async def admin_two_factor_setup(
    admin: User = Depends(get_enrolling_admin),
    db: AsyncSession = Depends(get_db),
):
    """New TOTP secret + QR code for the authenticator app (enrollment token)."""
    secret = pyotp.random_base32()
    uri = pyotp.TOTP(secret).provisioning_uri(name=admin.email, issuer_name=f"{settings.APP_NAME} Admin")
    admin.two_factor_secret = protect_totp_secret(secret)
    await db.commit()
    return {"secret": secret, "provisioning_uri": uri, "qr_svg": qr_svg(uri)}


@router.post("/2fa/enable", response_model=AdminLoginResponse, response_model_exclude_none=True)
async def admin_two_factor_enable(
    request: Request,
    payload: AdminTwoFactorCode,
    admin: User = Depends(get_enrolling_admin),
    db: AsyncSession = Depends(get_db),
):
    """Turn 2FA on with a first valid code, then open the admin session."""
    keys = throttle_keys(admin.email, _client_ip(request))
    wait = await login_throttle.retry_after(keys)
    if wait:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Trop de tentatives. Réessayez plus tard.", headers={"Retry-After": str(wait)})
    if not admin.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lancez d'abord la configuration 2FA.")
    if not verify_totp(admin, payload.code):
        await login_throttle.record_failure(keys)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"reason": "totp_invalid", "message": "Code invalide. Vérifiez l'heure de votre téléphone."})
    admin.is_two_factor_enabled = True
    await db.commit()
    await login_throttle.reset(keys)
    return _session(admin)


@router.get("/me")
async def get_current_admin_profile(
    admin: User = Depends(require_admin),
):
    """The signed-in admin (the console must not call the public /auth/me)."""
    return serialize_user(admin)


# ============================================================
# 2. Dashboard stats
# ============================================================

@router.get("/stats")
async def get_admin_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True)
    )
    verified_users = await db.scalar(
        select(func.count(User.id)).where(User.is_email_verified == True)
    )
    unverified_users = await db.scalar(
        select(func.count(User.id)).where(User.is_email_verified == False)
    )
    admin_users = await db.scalar(
        select(func.count(User.id)).where(User.role == UserRole.ADMIN)
    )

    total_projects = await db.scalar(select(func.count(Project.id)))

    completed_analyses = await db.scalar(
        select(func.count(Project.id)).where(Project.analysis_status == "completed")
    )
    running_analyses = await db.scalar(
        select(func.count(Project.id)).where(Project.analysis_status == "running")
    )
    failed_analyses = await db.scalar(
        select(func.count(Project.id)).where(Project.analysis_status == "failed")
    )

    projects_with_errors = await db.scalar(
        select(func.count(Project.id)).where(Project.analysis_error.is_not(None))
    )

    average_score = await db.scalar(
        select(func.avg(Project.startup_score)).where(Project.startup_score.is_not(None))
    )

    top_sectors_result = await db.execute(
        select(Project.industry, func.count(Project.id))
        .where(Project.industry.is_not(None))
        .group_by(Project.industry)
        .order_by(func.count(Project.id).desc())
        .limit(5)
    )

    top_regions_result = await db.execute(
        select(Project.market_region, func.count(Project.id))
        .group_by(Project.market_region)
        .order_by(func.count(Project.id).desc())
        .limit(5)
    )

    return {
        "users": {
            "total": total_users or 0,
            "active": active_users or 0,
            "verified": verified_users or 0,
            "unverified": unverified_users or 0,
            "admins": admin_users or 0,
        },
        "projects": {
            "total": total_projects or 0,
        },
        "analyses": {
            "completed": completed_analyses or 0,
            "running": running_analyses or 0,
            "failed": failed_analyses or 0,
            "with_errors": projects_with_errors or 0,
            "average_score": round(float(average_score), 2) if average_score is not None else None,
        },
        "top_sectors": [
            {"industry": industry or "Non spécifié", "count": count}
            for industry, count in top_sectors_result.all()
        ],
        "top_regions": [
            {"region": region or "Non spécifiée", "count": count}
            for region, count in top_regions_result.all()
        ],
    }


# ============================================================
# 3. Gestion utilisateurs
# ============================================================

@router.get("/users")
async def list_admin_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User, func.count(Project.id))
        .outerjoin(Project, Project.user_id == User.id)
        .group_by(User.id)
        .order_by(User.created_at.desc())
    )

    rows = result.all()

    return [
        serialize_user(user, project_count=project_count)
        for user, project_count in rows
    ]
async def _ensure_another_active_admin(db: AsyncSession, target: User) -> None:
    """
    Refuse any change that would leave the platform without an active admin
    (demotion, deactivation or deletion of the last one).
    """
    if target.role != UserRole.ADMIN or not target.is_active:
        return
    others = await db.scalar(
        select(func.count(User.id)).where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
            User.id != target.id,
        )
    )
    if not others:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action impossible : ce compte est le dernier administrateur actif.",
        )


@router.post("/users/create-admin", status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    payload: AdminCreateAdminRequest,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_confirmation),
    db: AsyncSession = Depends(get_db),
):
    """
    Crée un nouveau compte administrateur depuis l'espace admin.

    Sécurité :
    - Aucun signup admin public.
    - Seul un admin connecté peut créer un autre admin.
    - Le nouvel admin doit vérifier son email avant de se connecter.
    """

    query = select(User).where(User.email == payload.email)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte existe déjà avec cet email.",
        )

    new_admin = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role=UserRole.ADMIN,
        is_active=True,
        is_email_verified=False,
    )

    verification_token = set_email_verification_token(new_admin)

    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)

    queue_verification_email(
        background_tasks,
        new_admin.email,
        verification_token,
    )

    return {
        "message": "Compte admin créé avec succès. Un email de vérification a été envoyé.",
        "user": serialize_user(new_admin, project_count=0),
    }

@router.get("/users/{user_id}")
async def get_admin_user_detail(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    target_user = await db.get(User, user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable.",
        )

    total_projects = await db.scalar(
        select(func.count(Project.id)).where(Project.user_id == user_id)
    )

    completed_analyses = await db.scalar(
        select(func.count(Project.id)).where(
            Project.user_id == user_id,
            Project.analysis_status == "completed",
        )
    )

    failed_analyses = await db.scalar(
        select(func.count(Project.id)).where(
            Project.user_id == user_id,
            Project.analysis_status == "failed",
        )
    )

    average_score = await db.scalar(
        select(func.avg(Project.startup_score)).where(
            Project.user_id == user_id,
            Project.startup_score.is_not(None),
        )
    )

    last_project_result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
        .limit(1)
    )
    last_project = last_project_result.scalar_one_or_none()

    return {
        "user": serialize_user(target_user, project_count=total_projects or 0),
        "stats": {
            "total_projects": total_projects or 0,
            "completed_analyses": completed_analyses or 0,
            "failed_analyses": failed_analyses or 0,
            "average_score": round(float(average_score), 2) if average_score is not None else None,
        },
        "last_project": serialize_project(last_project) if last_project else None,
    }


@router.get("/users/{user_id}/projects")
async def get_admin_user_projects(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    target_user = await db.get(User, user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable.",
        )

    result = await db.execute(
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
    )

    projects = result.scalars().all()

    return [
        serialize_project(
            project,
            owner_email=target_user.email,
            owner_name=target_user.full_name,
        )
        for project in projects
    ]


@router.post("/users/{user_id}/resend-verification")
async def admin_resend_user_verification(
    user_id: int,
    background_tasks: BackgroundTasks,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    target_user = await db.get(User, user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable.",
        )

    if target_user.is_email_verified:
        return {
            "message": "Cet utilisateur a déjà vérifié son email.",
            "user": serialize_user(target_user),
        }

    if not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'envoyer un email à un compte désactivé.",
        )

    verification_token = set_email_verification_token(target_user)

    await db.commit()
    await db.refresh(target_user)

    queue_verification_email(
        background_tasks,
        target_user.email,
        verification_token,
    )

    return {
        "message": "Email de vérification renvoyé avec succès.",
        "user": serialize_user(target_user),
    }


@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    payload: AdminUserRoleUpdate,
    admin: User = Depends(require_confirmation),
    db: AsyncSession = Depends(get_db),
):
    target_user = await db.get(User, user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable.",
        )

    if payload.role != UserRole.ADMIN:
        await _ensure_another_active_admin(db, target_user)

    if target_user.id == admin.id and payload.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un admin ne peut pas retirer son propre rôle admin.",
        )

    target_user.role = payload.role

    await db.commit()
    await db.refresh(target_user)

    return serialize_user(target_user)


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    payload: AdminUserStatusUpdate,
    admin: User = Depends(require_confirmation),
    db: AsyncSession = Depends(get_db),
):
    target_user = await db.get(User, user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable.",
        )

    if payload.is_active is False:
        await _ensure_another_active_admin(db, target_user)

    if target_user.id == admin.id and payload.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un admin ne peut pas désactiver son propre compte.",
        )

    target_user.is_active = payload.is_active

    await db.commit()
    await db.refresh(target_user)

    return serialize_user(target_user)
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    user_id: int,
    admin: User = Depends(require_confirmation),
    db: AsyncSession = Depends(get_db),
):
    """
    Supprime un utilisateur depuis l'espace admin.

    Sécurité :
    - Un admin ne peut pas se supprimer lui-même.
    - On ne supprime pas un utilisateur qui possède des projets.
    - On ne supprime pas le dernier admin.
    """

    target_user = await db.get(User, user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable.",
        )

    await _ensure_another_active_admin(db, target_user)

    if target_user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un admin ne peut pas supprimer son propre compte.",
        )

    project_count = await db.scalar(
        select(func.count(Project.id)).where(Project.user_id == user_id)
    )

    if project_count and project_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Impossible de supprimer cet utilisateur car il possède des projets. "
                "Désactivez le compte à la place."
            ),
        )

    await db.delete(target_user)
    await db.commit()

    return None


# ============================================================
# 4. Gestion projets
# ============================================================

@router.get("/projects")
async def list_admin_projects(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project, User.email, User.full_name)
        .join(User, Project.user_id == User.id)
        .order_by(Project.created_at.desc())
    )

    rows = result.all()

    return [
        serialize_project(project, owner_email=email, owner_name=full_name)
        for project, email, full_name in rows
    ]


@router.get("/projects/{project_id}")
async def get_admin_project_detail(
    project_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project, User.email, User.full_name)
        .join(User, Project.user_id == User.id)
        .where(Project.id == project_id)
    )

    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable.",
        )

    project, owner_email, owner_name = row

    return serialize_project(
        project,
        owner_email=owner_email,
        owner_name=owner_name,
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_project(
    project_id: int,
    admin: User = Depends(require_confirmation),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable.",
        )

    await db.delete(project)
    await db.commit()

    return None


# ============================================================
# 5. Suivi analyses IA
# ============================================================

@router.get("/analyses")
async def list_admin_analyses(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project, User.email, User.full_name)
        .join(User, Project.user_id == User.id)
        .where(Project.analysis_status != "not_started")
        .order_by(Project.analysis_completed_at.desc().nullslast())
    )

    rows = result.all()

    return [
        {
            "project_id": project.id,
            "title": project.title,
            "industry": project.industry,
            "market_region": project.market_region,
            "startup_score": project.startup_score,
            "analysis_status": project.analysis_status,
            "analysis_step": project.analysis_step,
            "analysis_progress": project.analysis_progress,
            "analysis_error": project.analysis_error,
            "analysis_started_at": project.analysis_started_at,
            "analysis_completed_at": project.analysis_completed_at,
            "owner_email": email,
            "owner_name": full_name,
        }
        for project, email, full_name in rows
    ]
# ============================================================
# 5.1 Détail diagnostic brut d'une analyse IA
# ============================================================

def collect_nested_values(value: Any, target_keys: set[str]) -> list[Any]:
    """
    Parcourt récursivement un JSON et récupère toutes les valeurs
    dont la clé fait partie de target_keys.

    Utilisé côté admin seulement.
    """

    collected: list[Any] = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key in target_keys:
                collected.append(item)

            collected.extend(collect_nested_values(item, target_keys))

    elif isinstance(value, list):
        for item in value:
            collected.extend(collect_nested_values(item, target_keys))

    return collected


def flatten_admin_list(values: list[Any]) -> list[str]:
    """
    Transforme une liste mixte en liste de strings lisibles.
    """

    flattened: list[str] = []

    for value in values:
        if value is None:
            continue

        if isinstance(value, list):
            for item in value:
                if item is not None:
                    flattened.append(str(item))

        elif isinstance(value, dict):
            flattened.append(str(value))

        else:
            flattened.append(str(value))

    return flattened


def build_admin_analysis_diagnostics(project: Project) -> dict:
    """
    Construit un résumé technique réservé à l'admin.
    """

    analysis_data = project.analysis_data or {}

    forgecrawler = {}
    startup_meta = {}
    debate_room = {}
    debate_meta = {}

    if isinstance(analysis_data, dict):
        forgecrawler = analysis_data.get("forgecrawler") or {}
        startup_meta = analysis_data.get("startup_evaluator_meta") or {}
        debate_room = analysis_data.get("debate_room") or {}

        if isinstance(debate_room, dict):
            debate_meta = debate_room.get("meta") or {}

    technical_errors = flatten_admin_list(
        collect_nested_values(
            analysis_data,
            {
                "errors",
                "error",
                "raw_errors",
                "ddgs_errors",
                "scraping_errors",
                "provider_errors",
                "llm_errors",
                "model_errors",
                "fallback_errors",
            },
        )
    )

    technical_queries = flatten_admin_list(
        collect_nested_values(
            analysis_data,
            {
                "queries",
                "query",
                "search_query",
            },
        )
    )

    return {
        "project_id": project.id,
        "analysis_status": project.analysis_status,
        "analysis_step": project.analysis_step,
        "analysis_progress": project.analysis_progress,
        "analysis_error": project.analysis_error,
        "analysis_started_at": project.analysis_started_at,
        "analysis_completed_at": project.analysis_completed_at,

        "startup_evaluator": {
            "completed_steps": startup_meta.get("completed_steps", [])
            if isinstance(startup_meta, dict)
            else [],
            "failed_steps": startup_meta.get("failed_steps", [])
            if isinstance(startup_meta, dict)
            else [],
            "current_step": startup_meta.get("current_step")
            if isinstance(startup_meta, dict)
            else None,
            "progress": startup_meta.get("progress")
            if isinstance(startup_meta, dict)
            else None,
            "error": startup_meta.get("error")
            if isinstance(startup_meta, dict)
            else None,
        },

        "debate_room": {
            "completed": debate_meta.get("completed")
            if isinstance(debate_meta, dict)
            else None,
            "completed_steps": debate_meta.get("completed_steps", [])
            if isinstance(debate_meta, dict)
            else [],
            "failed_steps": debate_meta.get("failed_steps", [])
            if isinstance(debate_meta, dict)
            else [],
            "current_step": debate_meta.get("current_step")
            if isinstance(debate_meta, dict)
            else None,
            "progress": debate_meta.get("progress")
            if isinstance(debate_meta, dict)
            else None,
            "error": debate_meta.get("error")
            if isinstance(debate_meta, dict)
            else None,
        },

        "forgecrawler": {
            "status": forgecrawler.get("status")
            if isinstance(forgecrawler, dict)
            else None,
            "confidence_level": forgecrawler.get("confidence_level")
            if isinstance(forgecrawler, dict)
            else None,
            "sources_count": len(forgecrawler.get("sources", []))
            if isinstance(forgecrawler, dict)
            else 0,
            "local_competitors_count": forgecrawler.get("local_competitors_count")
            if isinstance(forgecrawler, dict)
            else None,
            "market_sources_count": forgecrawler.get("market_sources_count")
            if isinstance(forgecrawler, dict)
            else None,
        },

        "technical": {
            "errors_count": len(technical_errors),
            "queries_count": len(technical_queries),
            "errors": technical_errors[:100],
            "queries": technical_queries[:100],
        },
    }


@router.get("/analyses/{project_id}")
async def get_admin_analysis_detail(
    project_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne le détail brut d'une analyse IA pour l'admin.
    """

    result = await db.execute(
        select(Project, User.email, User.full_name)
        .join(User, Project.user_id == User.id)
        .where(Project.id == project_id)
    )

    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analyse ou projet introuvable.",
        )

    project, owner_email, owner_name = row

    return {
        "project": serialize_project(
            project,
            owner_email=owner_email,
            owner_name=owner_name,
        ),
        "diagnostics": build_admin_analysis_diagnostics(project),
        "analysis_data": project.analysis_data,
    }


# ============================================================
# 6. Health admin
# ============================================================

@router.get("/health")
async def get_admin_health(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Health admin léger.

    Important :
    - Ne consomme pas les quotas Gemini/Groq.
    - Vérifie surtout configuration + disponibilité Postgres.
    - Les vrais tests LLM pourront être ajoutés avec un bouton "Tester maintenant".
    """

    services = []

    services.append({
        "name": "Backend API",
        "type": "backend",
        "status": "healthy",
        "configured": True,
        "message": "Backend FastAPI opérationnel.",
    })

    try:
        await db.execute(text("SELECT 1"))
        services.append({
            "name": "PostgreSQL",
            "type": "database",
            "status": "healthy",
            "configured": True,
            "message": "Connexion PostgreSQL réussie.",
        })
    except Exception as exc:
        services.append({
            "name": "PostgreSQL",
            "type": "database",
            "status": "down",
            "configured": True,
            "message": str(exc),
        })

    smtp_configured = setting_is_configured("SMTP_USERNAME") and setting_is_configured("SMTP_PASSWORD")
    services.append({
        "name": "SMTP Email",
        "type": "email",
        "status": "configured" if smtp_configured else "warning",
        "configured": smtp_configured,
        "message": "SMTP configuré." if smtp_configured else "SMTP_USERNAME ou SMTP_PASSWORD manquant.",
    })

    google_configured = setting_is_configured("GOOGLE_CLIENT_ID") and setting_is_configured("GOOGLE_CLIENT_SECRET")
    services.append({
        "name": "Google OAuth",
        "type": "oauth",
        "status": "configured" if google_configured else "warning",
        "configured": google_configured,
        "message": "Google OAuth configuré." if google_configured else "GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET manquant.",
    })

    gemini_configured = setting_is_configured("GEMINI_API_KEY", "GOOGLE_API_KEY")
    gemini_model = get_setting_value("GEMINI_MODEL", "GEMINI_PRIMARY_MODEL")
    gemini_fallback = get_setting_value("GEMINI_FALLBACK_MODEL")

    services.append({
        "name": "Gemini Primary",
        "type": "llm",
        "status": "configured" if gemini_configured else "warning",
        "configured": gemini_configured,
        "model": gemini_model,
        "message": "Gemini configuré. Test réel non lancé pour éviter quota." if gemini_configured else "Clé Gemini manquante.",
    })

    services.append({
        "name": "Gemini Fallback",
        "type": "llm",
        "status": "configured" if gemini_configured and gemini_fallback else "warning",
        "configured": bool(gemini_configured and gemini_fallback),
        "model": gemini_fallback,
        "message": "Gemini fallback configuré." if gemini_fallback else "Modèle fallback Gemini non défini.",
    })

    groq_configured = setting_is_configured("GROQ_API_KEY")
    groq_model = get_setting_value("GROQ_MODEL", "GROQ_PRIMARY_MODEL")

    services.append({
        "name": "Groq",
        "type": "llm",
        "status": "configured" if groq_configured else "warning",
        "configured": groq_configured,
        "model": groq_model,
        "message": "Groq configuré. Test réel non lancé pour éviter quota." if groq_configured else "Clé Groq manquante.",
    })

    chroma_configured = setting_is_configured("CHROMA_HOST", "CHROMA_URL", "CHROMADB_HOST", "CHROMA_SERVER_HOST")
    services.append({
        "name": "ChromaDB",
        "type": "vector_db",
        "status": "configured" if chroma_configured else "warning",
        "configured": chroma_configured,
        "message": "ChromaDB configuré." if chroma_configured else "Configuration ChromaDB non détectée dans settings.",
    })

    redis_configured = setting_is_configured("REDIS_URL", "REDIS_HOST")
    services.append({
        "name": "Redis",
        "type": "cache",
        "status": "configured" if redis_configured else "warning",
        "configured": redis_configured,
        "message": "Redis configuré." if redis_configured else "Configuration Redis non détectée dans settings.",
    })

    status_priority = {"down": 3, "warning": 2, "configured": 1, "healthy": 0}
    worst = max(services, key=lambda item: status_priority.get(item["status"], 0))

    overall_status = "healthy"
    if worst["status"] == "down":
        overall_status = "down"
    elif worst["status"] == "warning":
        overall_status = "warning"
    elif worst["status"] == "configured":
        overall_status = "configured"

    return {
        "overall_status": overall_status,
        "checked_at": datetime.datetime.now(datetime.timezone.utc),
        "services": services,
    }


# ============================================================
# 7. Suivi erreurs
# ============================================================

@router.get("/errors")
async def get_admin_errors(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Version MVP du suivi erreurs.

    Pour maintenant :
    - On remonte les projets avec analysis_status='failed'
    - Ou ceux qui ont analysis_error non null

    Plus tard :
    - Créer une vraie table system_error_logs.
    """

    result = await db.execute(
        select(Project, User.email, User.full_name)
        .join(User, Project.user_id == User.id)
        .where(
            (Project.analysis_status == "failed")
            | (Project.analysis_error.is_not(None))
        )
        .order_by(Project.updated_at.desc())
    )

    rows = result.all()

    errors = []

    for project, owner_email, owner_name in rows:
        errors.append({
            "id": f"analysis_project_{project.id}",
            "source": "analysis",
            "level": "error",
            "status": "open",
            "message": project.analysis_error or "Analyse marquée comme échouée.",
            "project_id": project.id,
            "project_title": project.title,
            "owner_email": owner_email,
            "owner_name": owner_name,
            "analysis_status": project.analysis_status,
            "created_at": project.updated_at,
        })

    return errors
