"""Fail-closed, managed Neon Auth email proof for the existing Başak session ledger.

Neon owns password verification. Başak never stores or logs passwords or
Neon access tokens. A short-lived upstream sign-in is explicitly signed out
before a local, revocable Başak account session is created.

This is intentionally opt-in and requires a branch-specific Neon Auth URL.
"""
import base64
import os
import re
from urllib.parse import urlsplit

import httpx

from chat.kosu_deposu import _dsn


class LoginUnavailable(RuntimeError):
    pass


def auth_base(env=None):
    env = os.environ if env is None else env
    if env.get("BASAK_NEON_EMAIL_ENABLED", "").strip().lower() != "true":
        return ""
    target = "BASAK_PREVIEW_NEON_AUTH_BASE_URL" if (
        env.get("VERCEL_ENV", "").strip().lower() == "preview"
    ) else "BASAK_PRODUCTION_NEON_AUTH_BASE_URL"
    raw = (env.get(target) or "").strip().rstrip("/")
    try:
        parsed = urlsplit(raw)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname is not None
            and re.fullmatch(r"ep-[a-z0-9-]+\.neonauth\.[a-z0-9.-]+\.neon\.tech", parsed.hostname) is not None
            and re.fullmatch(r"/[a-zA-Z0-9_-]+/auth", parsed.path) is not None
            and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
            and parsed.port is None
        )
        if not valid:
            return ""
    except ValueError:
        return ""

    if len(env.get("BASAK_OTURUM_ANAHTARI", "").encode()) < 32:
        return ""
    try:
        key = base64.urlsafe_b64decode((env.get("BASAK_CONNECTION_KEY") or "").strip())
        if len(key) != 32:
            return ""
    except (ValueError, TypeError):
        return ""

    try:
        if not _dsn(env):
            return ""
    except RuntimeError:
        return ""
    return raw


async def verify_email_password(email, password, *, transport=None):
    """Prove an existing, email-verified Neon user and close the upstream session.

    Never return the password, access token or Neon session cookie. Fail closed
    if provider response or sign-out cannot be confirmed.
    """
    url = auth_base()
    if not url:
        raise LoginUnavailable("E-posta girisi yapilandirilmadi")
    if not isinstance(email, str) or not isinstance(password, str):
        raise ValueError("Gecersiz kimlik bilgisi")
    email = email.strip()
    if not 3 <= len(email) <= 254 or "@" not in email or not 1 <= len(password) <= 1024:
        raise ValueError("Gecersiz kimlik bilgisi")

    async with httpx.AsyncClient(timeout=15, follow_redirects=False,
                                 trust_env=False, transport=transport) as client:
        response = await client.post(url + "/sign-in/email",
                                     json={"email": email, "password": password},
                                     headers={"Accept": "application/json"})
        if response.status_code == 429:
            raise LoginUnavailable("Cok sayida giris denemesi")
        if response.status_code != 200:
            raise PermissionError("E-posta veya parola gecersiz")
        try:
            payload = response.json()
            user = payload["user"]
            if (not isinstance(user, dict) or
                    not isinstance(user.get("id"), str) or
                    not 1 <= len(user["id"]) <= 128 or
                    not isinstance(user.get("email"), str) or
                    user["email"].casefold() != email.casefold() or
                    user.get("emailVerified") is not True):
                raise PermissionError("Hesap dogrulamasi gerekli")
            # A successful Neon sign-in creates a session at Neon. We do not
            # adopt/copy its token; revoke the temporary session immediately.
            if not any(c.name.endswith("session_token") for c in client.cookies.jar):
                raise LoginUnavailable("Neon oturum kaniti alinmadi")
            signed_out = await client.post(url + "/sign-out",
                                           headers={"Accept": "application/json"})
            if signed_out.status_code not in (200, 204):
                raise LoginUnavailable("Gecici Neon oturumu kapatilamadi")
            return {
                "subject": user["id"],
                "name": str(user.get("name") or "Kullanici")[:160],
                "email": user["email"],
            }
        except (ValueError, KeyError, TypeError) as exc:
            raise LoginUnavailable("Neon dogrulama cevabi gecersiz") from exc
