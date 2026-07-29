import datetime
import hashlib
import secrets

import jwt
import pyotp
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.database import get_db
from app.mailer import send_verification_email, send_password_reset_email
from app.models import User, UserRole
from app.schemas.auth import (
    EmailVerificationResponse,
    ForgotPasswordRequest,
    PasswordResetResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    Token,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


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

    print("\n" + "=" * 80, flush=True)
    print(f"EMAIL_VERIFICATION_SENT_TO={email}", flush=True)
    print(verification_link, flush=True)
    print("=" * 80 + "\n", flush=True)


def create_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def set_password_reset_token(user: User) -> str:
    token = create_password_reset_token()

    user.password_reset_token_hash = hash_password_reset_token(token)
    user.password_reset_expires_at = (
        datetime.datetime.now(datetime.timezone.utc)
        + datetime.timedelta(hours=settings.PASSWORD_RESET_EXPIRE_HOURS)
    )

    return token


def queue_password_reset_email(
    background_tasks: BackgroundTasks,
    email: str,
    token: str,
) -> None:
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    background_tasks.add_task(
        send_password_reset_email,
        email,
        reset_link,
    )

    print("\n" + "=" * 80, flush=True)
    print(f"PASSWORD_RESET_SENT_TO={email}", flush=True)
    print(reset_link, flush=True)
    print("=" * 80 + "\n", flush=True)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    query = select(User).where(User.email == user_in.email)
    result = await db.execute(query)

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet email est déjà enregistré.",
        )

    if user_in.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La création publique d'un compte admin est interdite.",
        )

    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        is_email_verified=False,
    )

    verification_token = set_email_verification_token(new_user)

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    queue_verification_email(background_tasks, new_user.email, verification_token)

    return new_user


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Demande de réinitialisation mot de passe.

    Sécurité :
    - Réponse générique même si l'email n'existe pas.
    - Évite l'énumération des comptes.
    """

    generic_message = (
        "Si un compte existe avec cet email, "
        "un lien de réinitialisation a été envoyé."
    )

    query = select(User).where(User.email == payload.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return {"message": generic_message}

    if not user.is_active:
        return {"message": generic_message}

    if not user.hashed_password:
        return {"message": generic_message}

    reset_token = set_password_reset_token(user)

    await db.commit()

    queue_password_reset_email(background_tasks, user.email, reset_token)

    return {"message": generic_message}


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Réinitialise le mot de passe à partir du token reçu par email.
    """

    token_hash = hash_password_reset_token(payload.token)

    query = select(User).where(User.password_reset_token_hash == token_hash)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de réinitialisation invalide.",
        )

    if not user.password_reset_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de réinitialisation invalide.",
        )

    now = datetime.datetime.now(datetime.timezone.utc)

    if user.password_reset_expires_at < now:
        user.password_reset_token_hash = None
        user.password_reset_expires_at = None
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de réinitialisation expiré.",
        )

    user.hashed_password = get_password_hash(payload.new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None
    user.is_email_verified = True

    await db.commit()

    return {
        "message": "Mot de passe réinitialisé avec succès. Vous pouvez maintenant vous connecter."
    }


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    user_in: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    query = select(User).where(User.email == user_in.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé.",
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez vérifier votre adresse email avant de vous connecter.",
        )

    if user.is_two_factor_enabled:
        if not user.two_factor_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configuration 2FA invalide. Veuillez contacter l'administrateur.",
            )

        if not user_in.two_factor_code:
            return {
                "access_token": "",
                "token_type": "bearer",
                "requires_2fa": True,
            }

        totp = pyotp.TOTP(user.two_factor_secret)

        if not totp.verify(user_in.two_factor_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Code de double authentification invalide.",
            )

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    refresh_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=refresh_max_age,
        expires=refresh_max_age,
        samesite="lax",
        secure=False,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "requires_2fa": False,
    }


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_two_factor(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La double authentification est déjà activée.",
        )

    secret = pyotp.random_base32()

    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current_user.email,
        issuer_name=settings.APP_NAME,
    )

    current_user.two_factor_secret = secret

    await db.commit()
    await db.refresh(current_user)

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
    }


@router.post("/2fa/enable", response_model=UserResponse)
async def enable_two_factor(
    payload: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_two_factor_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La double authentification est déjà activée.",
        )

    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Veuillez initialiser la procédure via /2fa/setup au préalable.",
        )

    totp = pyotp.TOTP(current_user.two_factor_secret)

    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code de vérification erroné. Activation annulée.",
        )

    current_user.is_two_factor_enabled = True

    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    refresh_token_value = request.cookies.get("refresh_token")

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token manquant.",
        )

    try:
        payload = jwt.decode(
            refresh_token_value,
            settings.JWT_REFRESH_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        email: str = payload.get("sub")

        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide.",
            )

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expiré ou corrompu.",
        )

    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé.",
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez vérifier votre adresse email avant de continuer.",
        )

    new_access_token = create_access_token(data={"sub": user.email})

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "requires_2fa": False,
    }


@router.get("/google/login")
async def google_login(request: Request):
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        token = await oauth.google.authorize_access_token(request)

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Échec de l'authentification Google.",
        )

    user_info = token.get("userinfo")

    if not user_info or not user_info.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de récupérer les informations Google.",
        )

    google_id = user_info["sub"]
    email = user_info["email"]
    full_name = user_info.get("name", email)
    email_verified = bool(user_info.get("email_verified"))

    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google n'a pas confirmé la vérification de cet email.",
        )

    query = select(User).where(User.google_id == google_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        query = select(User).where(User.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if user:
            user.google_id = google_id
            user.is_email_verified = True
            user.email_verification_token_hash = None
            user.email_verification_expires_at = None

        else:
            user = User(
                email=email,
                full_name=full_name,
                hashed_password=None,
                google_id=google_id,
                role=UserRole.ENTREPRENEUR,
                is_email_verified=True,
            )

            db.add(user)

        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé.",
        )

    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})

    refresh_max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600

    frontend_redirect = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/oauth/callback?access_token={access_token}"
    )

    frontend_redirect.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        max_age=refresh_max_age,
        expires=refresh_max_age,
        samesite="lax",
        secure=False,
    )

    return frontend_redirect


@router.get("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_email_verification_token(token)

    query = select(User).where(User.email_verification_token_hash == token_hash)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de vérification invalide.",
        )

    if not user.email_verification_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de vérification invalide.",
        )

    now = datetime.datetime.now(datetime.timezone.utc)

    if user.email_verification_expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de vérification expiré.",
        )

    user.is_email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None

    await db.commit()

    return {
        "message": "Email vérifié avec succès. Vous pouvez maintenant vous connecter."
    }


@router.post("/resend-verification", response_model=EmailVerificationResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    query = select(User).where(User.email == payload.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    generic_message = (
        "Si un compte non vérifié existe avec cet email, "
        "un nouveau lien de vérification a été généré."
    )

    if not user:
        return {"message": generic_message}

    if user.is_email_verified:
        return {"message": "Cet email est déjà vérifié."}

    verification_token = set_email_verification_token(user)

    await db.commit()

    queue_verification_email(background_tasks, user.email, verification_token)

    return {"message": generic_message}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )

    return {"message": "Déconnexion réussie."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user