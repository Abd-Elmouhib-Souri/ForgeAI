import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from typing import Callable

from app.config import settings

logger = logging.getLogger(__name__)


def mask_email(email: str) -> str:
    """Address for the logs: "so***@gmail.com" (never the full address)."""
    local, _, domain = str(email or "").partition("@")
    if not local or not domain:
        return "***"
    return f"{local[:2]}***@{domain}"


class EmailLoggedInsteadOfSent(Exception):
    """Development without SMTP: the e-mail was written to the server log."""


def smtp_configured() -> bool:
    return bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD)


def deliver(kind: str, send: Callable[..., None], to_email: str, *args) -> None:
    """
    Background delivery of one e-mail: logs the outcome, never crashes the task.

    Before, a failure surfaced as a raw traceback (or not at all when the
    SMTP server did not answer, since there was no timeout).
    """
    masked = mask_email(to_email)
    try:
        send(to_email, *args)
    except EmailLoggedInsteadOfSent:
        # Never claim it was sent: the link is in the log just above.
        logger.info("E-mail « %s » pour %s non envoyé (SMTP non configuré) : voir le journal ci-dessus", kind, masked)
        return
    except Exception as exc:
        # The server's message may quote the recipient: mask it too.
        reason = str(exc).replace(to_email, masked)[:200]
        logger.error("Échec de l'envoi de l'e-mail « %s » à %s : %s: %s", kind, masked, type(exc).__name__, reason)
        return
    logger.info("E-mail « %s » envoyé à %s", kind, masked)


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """
    Envoie un email via SMTP.
    """

    if not smtp_configured():
        if settings.ENVIRONMENT == "development":
            # Local install without SMTP (e.g. a fresh clone): print the e-mail,
            # links included, in the server log so sign-up and password reset
            # can still be completed. Never in production.
            logger.warning(
                "SMTP non configuré (développement) : e-mail « %s » pour %s écrit ici au lieu d'être envoyé :\n%s",
                subject, mask_email(to_email), text_body,
            )
            raise EmailLoggedInsteadOfSent()
        raise RuntimeError("SMTP_USERNAME ou SMTP_PASSWORD manquant dans .env")

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

    message = EmailMessage()
    message["Subject"] = subject
    # formataddr: accented display names are encoded correctly.
    message["From"] = formataddr((settings.SMTP_FROM_NAME, from_email))
    message["To"] = to_email
    # Date and Message-ID: their absence is a classic spam signal
    # (RED 28 Sept 2026: the test mail landed in Gmail's spam folder).
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain=from_email.rpartition("@")[2] or None)

    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    if settings.SMTP_PORT == 465:
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            context=context,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS) as server:
            if settings.SMTP_USE_TLS:
                context = ssl.create_default_context()
                server.starttls(context=context)

            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)


def send_verification_email(to_email: str, verification_link: str) -> None:
    """
    Envoie l'email de vérification.
    """

    subject = "Vérifiez votre adresse email — ForgeAI"

    text_body = f"""Bonjour,

Merci de vous être inscrit sur ForgeAI.

Pour activer votre compte, ouvrez ce lien :

{verification_link}

Ce lien expire dans {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} heures.

Si vous n'avez pas créé de compte, ignorez cet email.

ForgeAI
"""

    html_body = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Vérification email</title>
  </head>

  <body style="margin:0; padding:0; background-color:#f4f7fb; font-family:Arial, Helvetica, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f7fb; padding:40px 0;">
      <tr>
        <td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:14px; padding:40px; box-shadow:0 10px 25px rgba(15,23,42,0.08);">
            <tr>
              <td>
                <h1 style="margin:0 0 24px 0; color:#111827; font-size:26px;">
                  Vérification de votre email
                </h1>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Bonjour,
                </p>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Merci de vous être inscrit sur <strong>ForgeAI</strong>.
                </p>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Pour activer votre compte, cliquez sur le bouton ci-dessous :
                </p>

                <table cellpadding="0" cellspacing="0" style="margin:30px 0;">
                  <tr>
                    <td align="center" bgcolor="#111827" style="border-radius:8px;">
                      <a
                        href="{verification_link}"
                        target="_blank"
                        style="display:inline-block; padding:16px 26px; color:#ffffff; background-color:#111827; text-decoration:none; border-radius:8px; font-size:16px; font-weight:bold;"
                      >
                        Vérifier mon email
                      </a>
                    </td>
                  </tr>
                </table>

                <p style="color:#374151; font-size:15px; line-height:1.6;">
                  Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :
                </p>

                <p style="word-break:break-all; font-size:14px; line-height:1.6;">
                  <a href="{verification_link}" target="_blank" style="color:#2563eb;">
                    {verification_link}
                  </a>
                </p>

                <p style="color:#6b7280; font-size:14px; line-height:1.6;">
                  Ce lien expire dans {settings.EMAIL_VERIFICATION_EXPIRE_HOURS} heures.
                </p>

                <p style="color:#6b7280; font-size:14px; line-height:1.6;">
                  Si vous n'avez pas créé de compte, ignorez cet email.
                </p>

                <p style="margin-top:30px; color:#9ca3af; font-size:14px;">
                  ForgeAI
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_password_reset_email(to_email: str, reset_link: str) -> None:
    """
    Envoie l'email de réinitialisation du mot de passe.
    """

    expire_hours = getattr(settings, "PASSWORD_RESET_EXPIRE_HOURS", 1)

    subject = "Réinitialisation de votre mot de passe — ForgeAI"

    text_body = f"""Bonjour,

Vous avez demandé la réinitialisation de votre mot de passe ForgeAI.

Pour choisir un nouveau mot de passe, ouvrez ce lien :

{reset_link}

Ce lien expire dans {expire_hours} heure(s).

Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.

ForgeAI
"""

    html_body = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Réinitialisation mot de passe</title>
  </head>

  <body style="margin:0; padding:0; background-color:#f4f7fb; font-family:Arial, Helvetica, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f7fb; padding:40px 0;">
      <tr>
        <td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:14px; padding:40px; box-shadow:0 10px 25px rgba(15,23,42,0.08);">
            <tr>
              <td>
                <h1 style="margin:0 0 24px 0; color:#111827; font-size:26px;">
                  Réinitialisation du mot de passe
                </h1>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Bonjour,
                </p>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Vous avez demandé la réinitialisation de votre mot de passe sur <strong>ForgeAI</strong>.
                </p>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Cliquez sur le bouton ci-dessous pour choisir un nouveau mot de passe :
                </p>

                <table cellpadding="0" cellspacing="0" style="margin:30px 0;">
                  <tr>
                    <td align="center" bgcolor="#111827" style="border-radius:8px;">
                      <a
                        href="{reset_link}"
                        target="_blank"
                        style="display:inline-block; padding:16px 26px; color:#ffffff; background-color:#111827; text-decoration:none; border-radius:8px; font-size:16px; font-weight:bold;"
                      >
                        Réinitialiser mon mot de passe
                      </a>
                    </td>
                  </tr>
                </table>

                <p style="color:#374151; font-size:15px; line-height:1.6;">
                  Si le bouton ne fonctionne pas, copiez ce lien dans votre navigateur :
                </p>

                <p style="word-break:break-all; font-size:14px; line-height:1.6;">
                  <a href="{reset_link}" target="_blank" style="color:#2563eb;">
                    {reset_link}
                  </a>
                </p>

                <p style="color:#6b7280; font-size:14px; line-height:1.6;">
                  Ce lien expire dans {expire_hours} heure(s).
                </p>

                <p style="color:#6b7280; font-size:14px; line-height:1.6;">
                  Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
                </p>

                <p style="margin-top:30px; color:#9ca3af; font-size:14px;">
                  ForgeAI
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_google_account_password_email(to_email: str, set_password_link: str, login_link: str) -> None:
    """
    "Mot de passe oublié" on an account created with Google: explain the
    Google sign-in and offer to set a password (same proof as a reset:
    access to this mailbox). Decision of 28 Sept 2026.
    """

    expire_hours = getattr(settings, "PASSWORD_RESET_EXPIRE_HOURS", 1)

    subject = "Votre compte ForgeAI utilise la connexion Google"

    text_body = f"""Bonjour,

Vous avez demandé à réinitialiser le mot de passe de votre compte ForgeAI.

Ce compte a été créé avec Google : il n'a pas encore de mot de passe.

Deux possibilités :

1. Continuer à vous connecter avec Google, sur la page de connexion :
{login_link}

2. Définir un mot de passe, pour vous connecter aussi avec votre e-mail :
{set_password_link}

Ce lien expire dans {expire_hours} heure(s). La connexion avec Google continuera de fonctionner.

Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail.

ForgeAI
"""

    html_body = f"""<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    <title>Connexion Google</title>
  </head>

  <body style="margin:0; padding:0; background-color:#f4f7fb; font-family:Arial, Helvetica, sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f7fb; padding:40px 0;">
      <tr>
        <td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff; border-radius:14px; padding:40px; box-shadow:0 10px 25px rgba(15,23,42,0.08);">
            <tr>
              <td>
                <h1 style="margin:0 0 24px 0; color:#111827; font-size:26px;">
                  Votre compte utilise la connexion Google
                </h1>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Vous avez demandé à réinitialiser le mot de passe de votre compte <strong>ForgeAI</strong>.
                  Ce compte a été créé avec Google : il n'a pas encore de mot de passe.
                </p>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Vous pouvez continuer à vous connecter avec Google :
                </p>

                <table cellpadding="0" cellspacing="0" style="margin:20px 0;">
                  <tr>
                    <td align="center" bgcolor="#111827" style="border-radius:8px;">
                      <a href="{login_link}" target="_blank"
                         style="display:inline-block; padding:14px 24px; color:#ffffff; background-color:#111827; text-decoration:none; border-radius:8px; font-size:16px; font-weight:bold;">
                        Aller à la page de connexion
                      </a>
                    </td>
                  </tr>
                </table>

                <p style="color:#374151; font-size:16px; line-height:1.6;">
                  Ou définir un mot de passe, pour vous connecter aussi avec votre e-mail :
                </p>

                <table cellpadding="0" cellspacing="0" style="margin:20px 0;">
                  <tr>
                    <td align="center" style="border-radius:8px; border:1px solid #111827;">
                      <a href="{set_password_link}" target="_blank"
                         style="display:inline-block; padding:14px 24px; color:#111827; text-decoration:none; border-radius:8px; font-size:16px; font-weight:bold;">
                        Définir un mot de passe
                      </a>
                    </td>
                  </tr>
                </table>

                <p style="word-break:break-all; font-size:14px; line-height:1.6;">
                  <a href="{set_password_link}" target="_blank" style="color:#2563eb;">{set_password_link}</a>
                </p>

                <p style="color:#6b7280; font-size:14px; line-height:1.6;">
                  Ce lien expire dans {expire_hours} heure(s). La connexion avec Google continuera de fonctionner.
                </p>

                <p style="color:#6b7280; font-size:14px; line-height:1.6;">
                  Si vous n'êtes pas à l'origine de cette demande, ignorez cet e-mail.
                </p>

                <p style="margin-top:30px; color:#9ca3af; font-size:14px;">
                  ForgeAI
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""

    send_email(
        to_email=to_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
