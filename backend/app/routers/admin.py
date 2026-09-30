# ============================================================
# backend/app/routers/admin.py
# ============================================================

import datetime
import hashlib
import secrets
from typing import Any, Literal

import pyotp
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from sqlalchemy import case, func, or_, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.mailer import deliver, send_verification_email
from app.models import Export, Project, User, UserRole
from app.email_identity import normalize_email, same_email
from app.services import admin_audit as audit
from app.services import analysis_diagnostics, analysis_queue, health_checks
from app.services.post_analysis_pipeline import effective_state
from app.services.admin_listing import (
    ANALYSIS_STATUS_LABELS,
    CSV_MAX_ROWS,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    ROLE_LABELS,
    contains,
    csv_response,
    page_body,
    paginate,
)
from app.services.export.storage import delete_project_files
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

    # deliver(): timeout + logged outcome (same path as the public e-mails).
    background_tasks.add_task(
        deliver,
        "vérification",
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
        await audit.add_and_commit(db, request, action="admin.login.blocked", result="denied",
                                   actor_email=user_in.email, detail="too_many_attempts")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez plus tard.",
            headers={"Retry-After": str(wait)},
        )

    user = (await db.execute(select(User).where(same_email(User.email, user_in.email)))).scalar_one_or_none()
    if not user or not user.hashed_password or not verify_password(user_in.password, user.hashed_password):
        await login_throttle.record_failure(keys)
        # Unknown account: actor stays null, the attempted e-mail is kept.
        await audit.add_and_commit(db, request, action="admin.login", result="failure",
                                   actor=user, actor_email=user_in.email, detail="bad_credentials")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect.")

    if user.role != UserRole.ADMIN or not user.is_active or not user.is_email_verified:
        # Same answer for every refusal: never reveal which accounts are admins.
        # The (admin-only) log keeps the real reason.
        await login_throttle.record_failure(keys)
        reason = ("not_admin" if user.role != UserRole.ADMIN
                  else "inactive" if not user.is_active else "email_unverified")
        await audit.add_and_commit(db, request, action="admin.login", result="denied", actor=user, detail=reason)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux administrateurs.")

    if not user.is_two_factor_enabled:
        # First admin login (or 2FA reset): enrol before any access.
        await audit.add_and_commit(db, request, action="admin.login", result="success",
                                   actor=user, detail="2fa_enrollment_required")
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
        await audit.add_and_commit(db, request, action="admin.login", result="failure",
                                   actor=user, detail="totp_invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"reason": "totp_invalid", "message": "Code de double authentification invalide."},
        )

    await login_throttle.reset(keys)
    await audit.add_and_commit(db, request, action="admin.login", result="success", actor=user)
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
        await audit.add_and_commit(db, request, action="admin.login.blocked", result="denied",
                                   actor=admin, detail="too_many_attempts")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Trop de tentatives. Réessayez plus tard.", headers={"Retry-After": str(wait)})
    if not admin.two_factor_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lancez d'abord la configuration 2FA.")
    if not verify_totp(admin, payload.code):
        await login_throttle.record_failure(keys)
        await audit.add_and_commit(db, request, action="admin.2fa.enable", result="failure",
                                   actor=admin, target_type="user", target_id=admin.id,
                                   target_label=admin.email, detail="totp_invalid")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail={"reason": "totp_invalid", "message": "Code invalide. Vérifiez l'heure de votre téléphone."})
    admin.is_two_factor_enabled = True
    audit.add(db, request, action="admin.2fa.enable", result="success", actor=admin,
              target_type="user", target_id=admin.id, target_label=admin.email,
              before={"is_two_factor_enabled": False}, after={"is_two_factor_enabled": True})
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
    """
    Dashboard counters in 3 SQL statements (Sprint 7.4, RED D3: was 13):
    every counter in one SELECT (two one-row aggregates side by side),
    then the top sectors and the top regions.
    """

    def flag(condition):
        # COUNT of the rows matching a condition, inside one aggregate.
        return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)

    users = select(
        func.count(User.id).label("u_total"),
        flag(User.is_active.is_(True)).label("u_active"),
        flag(User.is_email_verified.is_(True)).label("u_verified"),
        flag(User.role == UserRole.ADMIN).label("u_admins"),
    ).subquery()
    projects = select(
        func.count(Project.id).label("p_total"),
        flag(Project.analysis_status != "not_started").label("a_total"),
        flag(Project.analysis_status == "completed").label("a_completed"),
        flag(Project.analysis_status == "running").label("a_running"),
        flag(Project.analysis_status == "failed").label("a_failed"),
        flag(Project.analysis_error.is_not(None)).label("a_errors"),
        func.avg(Project.startup_score).label("a_score"),  # AVG ignores NULL scores
    ).subquery()
    counters = (
        await db.execute(select(users, projects).select_from(users.join(projects, true())))
    ).one()

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

    total_users = int(counters.u_total or 0)
    active_users = int(counters.u_active or 0)
    verified_users = int(counters.u_verified or 0)
    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "verified": verified_users,
            "unverified": total_users - verified_users,
            "admins": int(counters.u_admins or 0),
        },
        "projects": {
            "total": int(counters.p_total or 0),
        },
        "analyses": {
            "total": int(counters.a_total or 0),
            "completed": int(counters.a_completed or 0),
            "running": int(counters.a_running or 0),
            "failed": int(counters.a_failed or 0),
            "with_errors": int(counters.a_errors or 0),
            "average_score": round(float(counters.a_score), 2) if counters.a_score is not None else None,
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

# Sprint 7.4 (RED D1): search, filters, sort and pagination are done by the
# database. Sort keys are a whitelist: an unknown key answers 422.
UserSort = Literal["created_at", "email", "full_name", "role", "project_count"]
SortOrder = Literal["asc", "desc"]


def _project_count():
    # Correlated COUNT: one statement for the page, no GROUP BY on users.
    return (
        select(func.count(Project.id))
        .where(Project.user_id == User.id)
        .correlate(User)
        .scalar_subquery()
        .label("project_count")
    )


def _user_conditions(search, role, status_filter, verified) -> list:
    conditions = []
    if search:
        conditions.append(or_(contains(User.email, search), contains(User.full_name, search)))
    if role is not None:
        conditions.append(User.role == role)
    if status_filter is not None:
        conditions.append(User.is_active.is_(status_filter == "active"))
    if verified is not None:
        conditions.append(User.is_email_verified.is_(verified))
    return conditions


def _user_order(sort: str, order: str, project_count):
    column = {
        "created_at": User.created_at,
        "email": User.email,
        "full_name": User.full_name,
        "role": User.role,
        "project_count": project_count,
    }[sort]
    primary = column.asc() if order == "asc" else column.desc()
    return primary, User.id.desc()  # stable order between pages


@router.get("/users")
async def list_admin_users(
    search: str | None = Query(default=None, max_length=255),
    role: UserRole | None = Query(default=None),
    status_filter: Literal["active", "inactive"] | None = Query(default=None, alias="status"),
    verified: bool | None = Query(default=None),
    sort: UserSort = Query(default="created_at"),
    order: SortOrder = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    conditions = _user_conditions(search, role, status_filter, verified)
    project_count = _project_count()
    rows, total = await paginate(
        db,
        select(User, project_count).where(*conditions).order_by(*_user_order(sort, order, project_count)),
        select(func.count(User.id)).where(*conditions),
        page=page,
        page_size=page_size,
    )
    return page_body(
        [serialize_user(user, project_count=count) for user, count in rows], total, page, page_size
    )


@router.get("/users/export.csv")
async def export_admin_users_csv(
    search: str | None = Query(default=None, max_length=255),
    role: UserRole | None = Query(default=None),
    status_filter: Literal["active", "inactive"] | None = Query(default=None, alias="status"),
    verified: bool | None = Query(default=None),
    sort: UserSort = Query(default="created_at"),
    order: SortOrder = Query(default="desc"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Same filters as the screen; never the password hash or the 2FA secret."""
    project_count = _project_count()
    rows = (
        await db.execute(
            select(User, project_count)
            .where(*_user_conditions(search, role, status_filter, verified))
            .order_by(*_user_order(sort, order, project_count))
            .limit(CSV_MAX_ROWS)
        )
    ).all()
    return csv_response(
        "utilisateurs",
        ["E-mail", "Nom", "Rôle", "Statut", "E-mail vérifié", "2FA", "Projets", "Inscrit le"],
        (
            [
                user.email,
                user.full_name,
                ROLE_LABELS.get(role_to_str(user.role), role_to_str(user.role)),
                "Actif" if user.is_active else "Désactivé",
                bool(user.is_email_verified),
                bool(user.is_two_factor_enabled),
                count,
                user.created_at,
            ]
            for user, count in rows
        ),
    )


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


async def _record_refusal(
    db: AsyncSession, request: Request, admin: User, exc: HTTPException, *, action: str, target: User | None = None,
) -> None:
    """A business rule refused the action: keep the attempt in the audit log."""
    await audit.add_and_commit(
        db, request, action=action, result="denied", actor=admin, detail=exc.detail,
        target_type="user" if target is not None else None,
        target_id=target.id if target is not None else None,
        target_label=target.email if target is not None else None,
    )


@router.post("/users/create-admin", status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    request: Request,
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

    query = select(User).where(same_email(User.email, payload.email))
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        exc = HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte existe déjà avec cet email.",
        )
        await _record_refusal(db, request, admin, exc, action="admin.create", target=existing_user)
        raise exc

    new_admin = User(
        email=normalize_email(payload.email),  # stored lowercase
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        role=UserRole.ADMIN,
        is_active=True,
        is_email_verified=False,
    )

    verification_token = set_email_verification_token(new_admin)

    db.add(new_admin)
    await db.flush()  # new_admin.id for the audit entry, same transaction
    audit.add(db, request, action="admin.create", result="success", actor=admin,
              target_type="user", target_id=new_admin.id, target_label=new_admin.email,
              after=audit.user_snapshot(new_admin))  # never the password
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
    request: Request,
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
    audit.add(db, request, action="user.verification.resend", result="success", actor=admin,
              target_type="user", target_id=target_user.id, target_label=target_user.email)

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
    request: Request,
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

    try:
        if payload.role != UserRole.ADMIN:
            await _ensure_another_active_admin(db, target_user)

        if target_user.id == admin.id and payload.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un admin ne peut pas retirer son propre rôle admin.",
            )
    except HTTPException as exc:
        await _record_refusal(db, request, admin, exc, action="user.role.update", target=target_user)
        raise

    before = {"role": role_to_str(target_user.role)}
    target_user.role = payload.role
    audit.add(db, request, action="user.role.update", result="success", actor=admin,
              target_type="user", target_id=target_user.id, target_label=target_user.email,
              before=before, after={"role": role_to_str(payload.role)})

    await db.commit()
    await db.refresh(target_user)

    return serialize_user(target_user)


@router.patch("/users/{user_id}/status")
async def update_user_status(
    request: Request,
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

    try:
        if payload.is_active is False:
            await _ensure_another_active_admin(db, target_user)

        if target_user.id == admin.id and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un admin ne peut pas désactiver son propre compte.",
            )
    except HTTPException as exc:
        await _record_refusal(db, request, admin, exc, action="user.status.update", target=target_user)
        raise

    before = {"is_active": bool(target_user.is_active)}
    target_user.is_active = payload.is_active
    audit.add(db, request, action="user.status.update", result="success", actor=admin,
              target_type="user", target_id=target_user.id, target_label=target_user.email,
              before=before, after={"is_active": bool(payload.is_active)})

    await db.commit()
    await db.refresh(target_user)

    return serialize_user(target_user)
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_admin_user(
    request: Request,
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

    try:
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
    except HTTPException as exc:
        await _record_refusal(db, request, admin, exc, action="user.delete", target=target_user)
        raise

    # The account disappears; its public snapshot stays in the log.
    audit.add(db, request, action="user.delete", result="success", actor=admin,
              target_type="user", target_id=target_user.id, target_label=target_user.email,
              before=audit.user_snapshot(target_user))
    await db.delete(target_user)
    await db.commit()

    return None


# ============================================================
# 4. Gestion projets
# ============================================================

# Sprint 7.4 (RED D2): the lists select named columns only, never the
# heavy JSON (analysis_data, clarification_context) nor the description:
# those are read by the detail pages.
PROJECT_LIST_COLUMNS = (
    Project.id,
    Project.title,
    Project.industry,
    Project.market_region,
    Project.status,
    Project.startup_score,
    Project.analysis_status,
    Project.analysis_step,
    Project.analysis_progress,
    Project.analysis_error,
    Project.analysis_started_at,
    Project.analysis_completed_at,
    Project.analysis_heartbeat_at,
    Project.user_id,
    Project.created_at,
    Project.updated_at,
    # A short excerpt cut by the database, never the whole text.
    func.substr(Project.description, 1, 160).label("description_excerpt"),
    User.email.label("owner_email"),
    User.full_name.label("owner_name"),
)

ProjectSort = Literal["created_at", "updated_at", "title", "startup_score", "analysis_status"]
AnalysisSort = Literal["last_activity", "analysis_completed_at", "analysis_started_at", "startup_score", "analysis_progress"]
AnalysisStatus = Literal["not_started", "queued", "running", "needs_clarification", "completed", "failed"]


def _project_conditions(search, status_value) -> list:
    conditions = []
    if search:
        conditions.append(or_(
            contains(Project.title, search),
            contains(Project.industry, search),
            contains(Project.market_region, search),
            contains(User.email, search),
            contains(User.full_name, search),
        ))
    if status_value is not None:
        conditions.append(Project.analysis_status == status_value)
    return conditions


def _ordered(column, order: str):
    # NULLs (no score, never finished) always at the end of the page.
    return (column.asc() if order == "asc" else column.desc()).nulls_last()


async def _project_page(db, conditions, order_by, page, page_size):
    return await paginate(
        db,
        select(*PROJECT_LIST_COLUMNS).join(User, Project.user_id == User.id).where(*conditions)
        .order_by(*order_by, Project.id.desc()),
        select(func.count(Project.id)).join(User, Project.user_id == User.id).where(*conditions),
        page=page,
        page_size=page_size,
    )


def serialize_project_row(row) -> dict:
    """List item of a project (light row from PROJECT_LIST_COLUMNS)."""
    item = dict(row._mapping)
    # Sprint 7.6: queued/running without a sign of life = stuck (restart...).
    item["analysis_stalled"] = analysis_queue.is_stalled(item["analysis_status"], item["analysis_heartbeat_at"])
    return item


@router.get("/projects")
async def list_admin_projects(
    search: str | None = Query(default=None, max_length=255),
    status_value: AnalysisStatus | None = Query(default=None, alias="status"),
    sort: ProjectSort = Query(default="created_at"),
    order: SortOrder = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    column = {
        "created_at": Project.created_at,
        "updated_at": Project.updated_at,
        "title": Project.title,
        "startup_score": Project.startup_score,
        "analysis_status": Project.analysis_status,
    }[sort]
    rows, total = await _project_page(
        db, _project_conditions(search, status_value), [_ordered(column, order)], page, page_size
    )
    return page_body([serialize_project_row(row) for row in rows], total, page, page_size)


@router.get("/projects/export.csv")
async def export_admin_projects_csv(
    search: str | None = Query(default=None, max_length=255),
    status_value: AnalysisStatus | None = Query(default=None, alias="status"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = (
        await db.execute(
            select(*PROJECT_LIST_COLUMNS)
            .join(User, Project.user_id == User.id)
            .where(*_project_conditions(search, status_value))
            .order_by(Project.created_at.desc(), Project.id.desc())
            .limit(CSV_MAX_ROWS)
        )
    ).all()
    return csv_response(
        "projets",
        ["Projet", "Propriétaire", "Statut de l'analyse", "Secteur", "Région", "Score", "Erreur", "Créé le"],
        (
            [
                row.title,
                row.owner_email,
                ANALYSIS_STATUS_LABELS.get(row.analysis_status, row.analysis_status),
                row.industry,
                row.market_region,
                row.startup_score,
                row.analysis_error,
                row.created_at,
            ]
            for row in rows
        ),
    )


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
    request: Request,
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

    owner = await db.get(User, project.user_id)
    export_count = await db.scalar(select(func.count(Export.id)).where(Export.project_id == project_id))
    audit.add(db, request, action="project.delete", result="success", actor=admin,
              target_type="project", target_id=project.id, target_label=project.title,
              before={
                  "title": project.title,
                  "owner_email": owner.email if owner else None,
                  "analysis_status": project.analysis_status,
                  "exports": export_count or 0,
              })
    await db.delete(project)
    await db.commit()

    # Sprint 7.2 (RED B3): the export files (PDF, Word, PowerPoint) go too.
    delete_project_files(project_id)

    return None


# ============================================================
# 5. Suivi analyses IA
# ============================================================

@router.get("/analyses")
async def list_admin_analyses(
    search: str | None = Query(default=None, max_length=255),
    status_value: AnalysisStatus | None = Query(default=None, alias="status"),
    # Default = last activity: a relaunched (or live) run has no end date yet
    # and must come FIRST, not vanish at the end of the list.
    sort: AnalysisSort = Query(default="last_activity"),
    order: SortOrder = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Projects whose analysis was started at least once (light columns)."""
    conditions = [Project.analysis_status != "not_started", *_project_conditions(search, status_value)]
    column = {
        "last_activity": func.coalesce(Project.analysis_completed_at, Project.analysis_started_at),
        "analysis_completed_at": Project.analysis_completed_at,
        "analysis_started_at": Project.analysis_started_at,
        "startup_score": Project.startup_score,
        "analysis_progress": Project.analysis_progress,
    }[sort]
    rows, total = await _project_page(db, conditions, [_ordered(column, order)], page, page_size)
    items = []
    for row in rows:
        item = serialize_project_row(row)
        item["project_id"] = item.pop("id")  # key used by the analyses screen
        items.append(item)
    return page_body(items, total, page, page_size)


# ============================================================
# 5.1 Détail diagnostic d'une analyse IA
# ============================================================

def build_admin_analysis_diagnostics(project: Project) -> dict:
    """Readable diagnostic (Sprint 7.8): decided by analysis_diagnostics, displayed as is."""
    return analysis_diagnostics.build(project)


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
        # Sprint 7.6: is the run stuck, and where is the post-analysis pipeline?
        "analysis_stalled": analysis_queue.is_stalled(project.analysis_status, project.analysis_heartbeat_at),
        "pipeline": effective_state(
            project_id=project.id,
            analysis_status=project.analysis_status,
            analysis_data=project.analysis_data,
        ),
        "diagnostics": build_admin_analysis_diagnostics(project),
        "analysis_data": project.analysis_data,
    }


@router.post("/analyses/{project_id}/relaunch", status_code=status.HTTP_202_ACCEPTED)
async def relaunch_admin_analysis(
    request: Request,
    project_id: int,
    admin: User = Depends(require_confirmation),
    db: AsyncSession = Depends(get_db),
):
    """
    Queue a new run of a project's analysis (Sprint 7.6).

    The admin API never executes it: the public API worker picks it up
    (analysis_queue). Refused (409) while a run is alive, and for a project
    whose owner never started an analysis. Audited either way.
    """
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projet introuvable.")

    before = analysis_queue.audit_snapshot(project)
    target = {"target_type": "project", "target_id": project.id, "target_label": project.title}

    refusal = None
    if project.analysis_status == "not_started":
        refusal = ("never_started", "Le client n'a jamais lancé d'analyse sur ce projet.")
    elif analysis_queue.is_live(project):
        refusal = ("analysis_active", "Une analyse est en cours et donne encore des signes de vie.")
    if refusal:
        code, message = refusal
        await audit.add_and_commit(db, request, action="analysis.relaunch", result="denied",
                                   actor=admin, before=before, detail=code, **target)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"reason": code, "message": message})

    run_id = analysis_queue.enqueue(project)
    audit.add(db, request, action="analysis.relaunch", result="success", actor=admin, before=before,
              after={"analysis_status": project.analysis_status, "analysis_attempt": project.analysis_attempt,
                     "analysis_run_id": run_id},
              **target)
    await db.commit()
    return {
        "project_id": project.id,
        "analysis_status": project.analysis_status,
        "analysis_step": project.analysis_step,
        "message": "Relance en file d'attente : l'analyse démarrera dans quelques secondes.",
    }


# ============================================================
# 6. Health admin
# ============================================================

@router.get("/health")
async def get_admin_health(
    refresh: bool = Query(default=False, description="Ignorer le cache et tester maintenant"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Real health of every service (Sprint 7.7, app.services.health_checks):
    each one is really contacted, with a timeout and a latency. Cached a few
    seconds; ?refresh=true tests again now. No secret in the answer.
    """
    return await health_checks.run_all(db, refresh=refresh)


# ============================================================
# 7. Suivi erreurs
# ============================================================

@router.get("/errors")
async def get_admin_errors(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Failed analyses and analyses that reported an error, newest first
    (light columns, paginated). A dedicated error log table comes later.
    """
    conditions = [(Project.analysis_status == "failed") | (Project.analysis_error.is_not(None))]
    rows, total = await _project_page(db, conditions, [Project.updated_at.desc()], page, page_size)
    items = [
        {
            "id": f"analysis_project_{row.id}",
            "source": "analysis",
            "level": "error",
            "status": "open",
            "message": row.analysis_error or "Analyse marquée comme échouée.",
            "project_id": row.id,
            "project_title": row.title,
            "owner_email": row.owner_email,
            "owner_name": row.owner_name,
            "analysis_status": row.analysis_status,
            "created_at": row.updated_at,
        }
        for row in rows
    ]
    return page_body(items, total, page, page_size)
