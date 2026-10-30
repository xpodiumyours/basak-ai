"""GitHub App user OAuth limited by user-selected installation repositories.

Provider access intersects App permissions with the authenticated user's rights.
No installation JWT or private key can elevate repository access.
"""
import os
import re
import time
import math
from urllib.parse import quote

import httpx

PERMISSIONS = {"contents": "write", "pull_requests": "write", "metadata": "read"}
API = "https://api.github.com"
AUTH_TYPE = "github_app_user"


class GitHubAppError(RuntimeError):
    pass


def _positive_id(value):
    if isinstance(value, bool):
        raise GitHubAppError("GitHub App kimligi gecersiz")
    try:
        result = int(value)
    except (ValueError, TypeError):
        raise GitHubAppError("GitHub App kimligi gecersiz") from None
    if result <= 0 or str(result) != str(value):
        raise GitHubAppError("GitHub App kimligi gecersiz")
    return result


def _settings():
    app_id = _positive_id(os.environ.get("BASAK_GITHUB_APP_ID", ""))
    slug = os.environ.get("BASAK_GITHUB_APP_SLUG", "").strip()
    if not re.fullmatch(r"[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*", slug):
        raise GitHubAppError("GitHub App adi yapilandirilmadi")
    return app_id, slug


def configured():
    try:
        _settings()
        return True
    except GitHubAppError:
        return False


def _request(client, path, token, *, params=None):
    try:
        response = client.get(API + path, params=params, headers={
            "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"})
    except httpx.HTTPError:
        raise GitHubAppError("GitHub App baglantisi kurulamadi") from None
    if not 200 <= response.status_code < 300:
        raise GitHubAppError("GitHub App islemi basarisiz (HTTP %s)" % response.status_code)
    try:
        data = response.json()
    except ValueError:
        raise GitHubAppError("GitHub App yaniti gecersiz") from None
    if not isinstance(data, dict):
        raise GitHubAppError("GitHub App yaniti gecersiz")
    return data, 'rel="next"' in response.headers.get("link", "")


def _list(client, path, token, field):
    rows, page = [], 1
    while True:
        data, more = _request(client, path, token, params={"per_page": 100, "page": page})
        values = data.get(field)
        if not isinstance(values, list) or any(not isinstance(x, dict) for x in values):
            raise GitHubAppError("GitHub App liste yaniti gecersiz")
        rows.extend(values)
        if not more:
            return rows
        if not values:
            raise GitHubAppError("GitHub App sayfalama yaniti gecersiz")
        page += 1


def _permissions(value):
    if not isinstance(value, dict) or {k: v for k, v in value.items() if v != "none"} != PERMISSIONS:
        raise GitHubAppError("GitHub App izinleri secilmis kod ve PR kapsamiyla uyusmuyor")


def _installation(value, app_id):
    account = value.get("account") or {}
    if (not isinstance(account, dict) or _positive_id(value.get("app_id")) != app_id
            or account.get("type") not in ("User", "Organization")
            or value.get("repository_selection") != "selected"
            or value.get("suspended_at") is not None):
        raise GitHubAppError("GitHub App yalniz secilmis depo kurulumlarini kullanabilir")
    _positive_id(account.get("id"))
    _permissions(value.get("permissions"))
    return _positive_id(value.get("id"))


def _repository_name(value):
    from chat.platform_github_paths import validate_repository
    try:
        return validate_repository(value)
    except ValueError:
        raise GitHubAppError("GitHub App depo kimligi gecersiz") from None


def _token_dict(value):
    token = dict(value) if isinstance(value, dict) else {"access_token": value}
    if (not isinstance(token.get("access_token"), str)
            or not token["access_token"].startswith("ghu_") or len(token["access_token"]) <= 4
            or token.get("error")):
        raise GitHubAppError("GitHub kullanici yetkilendirmesi eksik veya gecersiz")
    if token.get("expires_at") is not None:
        try:
            expiry = float(token["expires_at"])
            if not math.isfinite(expiry) or expiry <= time.time():
                raise ValueError()
        except (ValueError, TypeError):
            raise GitHubAppError("GitHub kullanici anahtari suresi gecersiz") from None
    return token


def discover_connection(user_token, profile, transport=None):
    """Return encrypted-store-ready user credentials and selected repo metadata.

    Dict credentials preserve refresh/expiry; string credentials support a
    non-expiring user token. Read-only repositories remain readable, while
    writable_repositories reflects GET /repos permissions.push for this user.
    """
    app_id, _ = _settings()
    owner_id = _positive_id(profile.get("id"))
    token = _token_dict(user_token)
    access = token["access_token"]
    names, repo_ids, writable, installations = [], [], [], []
    seen = {}
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False, transport=transport) as client:
        available = _list(client, "/user/installations", access, "installations")
        matches = [x for x in available if x.get("app_id") == app_id]
        if not matches:
            raise GitHubAppError("GitHub App secilen depolara kullanici tarafindan kurulmali")
        for value in matches:
            iid = _installation(value, app_id)
            if iid in installations:
                raise GitHubAppError("GitHub App kurulum listesi yinelenemez")
            installations.append(iid)
            rows = _list(client, "/user/installations/%s/repositories" % iid, access, "repositories")
            for row in rows:
                name, rid = _repository_name(row.get("full_name")), _positive_id(row.get("id"))
                if name.casefold() in seen:
                    if seen[name.casefold()] != rid:
                        raise GitHubAppError("GitHub App depo kimligi uyusmuyor")
                    continue
                if rid in repo_ids:
                    raise GitHubAppError("GitHub App depo kimligi yinelenemez")
                info, _ = _request(client, "/repos/" + "/".join(quote(p, safe="") for p in name.split("/")), access)
                if _positive_id(info.get("id")) != rid or str(info.get("full_name", "")).casefold() != name.casefold():
                    raise GitHubAppError("GitHub App depo kimligi uyusmuyor")
                if not isinstance(info.get("permissions"), dict) or info["permissions"].get("pull") is not True:
                    raise GitHubAppError("GitHub App secilmis depoya kullanici okuma erisimi yok")
                names.append(name)
                repo_ids.append(rid)
                seen[name.casefold()] = rid
                if info["permissions"].get("push") is True:
                    writable.append(name)
    if not names:
        raise GitHubAppError("GitHub App kurulumunda kullanicinin erisebildigi secilmis depo yok")
    token["auth_type"] = AUTH_TYPE
    meta = {"auth_type": AUTH_TYPE, "github_app_id": app_id, "account_id": str(owner_id),
            "installations": installations, "repositories": names, "repository_ids": repo_ids,
            "writable_repositories": writable, "permissions": dict(PERMISSIONS)}
    return token, meta


def validate_connection(connection):
    """Reject stale App identity or malformed stored repository/user scope."""
    app_id, _ = _settings()
    meta = connection.get("metadata") or {}
    if connection.get("provider") != "github" or meta.get("auth_type") != AUTH_TYPE:
        raise GitHubAppError("GitHub App kullanici baglantisi gerekli")
    if _positive_id(meta.get("github_app_id")) != app_id:
        raise GitHubAppError("GitHub App baglantisi bu uygulamaya ait degil")
    _positive_id(meta.get("account_id"))
    _permissions(meta.get("permissions"))
    installations = meta.get("installations")
    if not isinstance(installations, list) or not installations:
        raise GitHubAppError("GitHub App kurulum secimi eksik")
    ids = [_positive_id(i) for i in installations]
    if len(set(ids)) != len(ids):
        raise GitHubAppError("GitHub App kurulum listesi yinelenemez")
    names, repo_ids = meta.get("repositories"), meta.get("repository_ids")
    writable = meta.get("writable_repositories")
    if (not isinstance(names, list) or not names or not isinstance(repo_ids, list)
            or not isinstance(writable, list) or len(names) != len(repo_ids)):
        raise GitHubAppError("GitHub App depo secimi eksik")
    names = [_repository_name(n).casefold() for n in names]
    repo_ids = [_positive_id(i) for i in repo_ids]
    write_names = [_repository_name(n).casefold() for n in writable]
    if (len(names) != len(set(names)) or len(repo_ids) != len(set(repo_ids))
            or not set(write_names).issubset(names) or len(write_names) != len(set(write_names))):
        raise GitHubAppError("GitHub App depo secimi gecersiz")


def refresh_connection(connection, token, transport=None):
    """Refresh user OAuth and rediscover current selection and user permissions."""
    validate_connection(connection)
    if (token.get("auth_type") != AUTH_TYPE or not token.get("refresh_token")
            or not isinstance(token.get("access_token"), str)
            or not token["access_token"].startswith("ghu_")):
        raise GitHubAppError("GitHub kullanici yenileme yetkisi eksik")
    cid = os.environ.get("BASAK_GITHUB_CLIENT_ID", "").strip()
    secret = os.environ.get("BASAK_GITHUB_CLIENT_SECRET", "").strip()
    if not cid or not secret:
        raise GitHubAppError("GitHub kullanici yenileme yapilandirmasi eksik")
    with httpx.Client(timeout=60, follow_redirects=False, trust_env=False, transport=transport) as client:
        try:
            response = client.post("https://github.com/login/oauth/access_token", headers={"Accept": "application/json"},
                                   data={"grant_type": "refresh_token", "refresh_token": token["refresh_token"],
                                         "client_id": cid, "client_secret": secret})
        except httpx.HTTPError:
            raise GitHubAppError("GitHub kullanici anahtari yenilenemedi") from None
        if response.status_code != 200:
            raise GitHubAppError("GitHub kullanici anahtari yenilenemedi")
        try:
            new = response.json()
        except ValueError:
            raise GitHubAppError("GitHub yenileme yaniti gecersiz") from None
        if not isinstance(new, dict) or new.get("error") or not new.get("access_token"):
            raise GitHubAppError("GitHub kullanici anahtari yenilenemedi")
        merged = {**token, **new}
        if new.get("expires_in") is not None:
            try:
                duration = float(new["expires_in"])
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError()
                merged["expires_at"] = time.time() + duration
            except (ValueError, TypeError):
                raise GitHubAppError("GitHub yenileme suresi gecersiz") from None
        elif "expires_at" not in new:
            merged.pop("expires_at", None)
        merged = _token_dict(merged)
        profile, _ = _request(client, "/user", merged["access_token"])
        if str(_positive_id(profile.get("id"))) != str(connection["metadata"]["account_id"]):
            raise GitHubAppError("GitHub kullanici yenilemesi baska hesaba ait")
    return discover_connection(merged, profile, transport)
