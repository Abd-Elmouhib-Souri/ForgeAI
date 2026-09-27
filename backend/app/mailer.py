import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings


def send_email(
    to_email: str,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> None:
    """
    Envoie un email via SMTP.
    """

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        raise RuntimeError("SMTP_USERNAME ou SMTP_PASSWORD manquant dans .env")

    from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{from_email}>"
    message["To"] = to_email

    message.set_content(text_body)

    if html_body:
        message.add_alternative(html_body, subtype="html")

    if settings.SMTP_PORT == 465:
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            context=context,
        ) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)

    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
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