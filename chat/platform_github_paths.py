"""Validate logical GitHub identifiers before constructing authenticated URLs.

These checks constrain credential use, never select a task or model. Helpers
return the original string and raise GithubPathError before any HTTP request.
"""
import os
import re
import unicodedata


class GithubPathError(ValueError):
    pass


_OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
# Encoded separators/dot components remain forbidden even when nested in %25.
_UNSAFE_ESCAPE = re.compile(
    r"%(?:25)*(?:2e|2f|5c|0[0-9a-f]|1[0-9a-f]|7f|8[0-9a-f]|9[0-9a-f])",
    re.IGNORECASE,
)
_CREDENTIAL_DIRECTORIES = frozenset((".git", ".ssh", ".aws", ".gnupg"))
_CREDENTIAL_EXTENSIONS = (".pem", ".key", ".p12", ".pfx")
_DEFAULT_PROTECTED_PATHS = (
    ".github/", "AGENTS.md", "SECURITY.md", "Resmidokumanuyum.md", "deploy/",
    "chat/platform_connectors.py", "chat/platform_accounts_api.py",
    "chat/platform_connections.py", "chat/platform_github_app.py",
    "chat/platform_github_paths.py",
)


def _text(value):
    if not isinstance(value, str) or any(
            unicodedata.category(char) in ("Cc", "Cf", "Cs") for char in value):
        raise GithubPathError("GitHub yolu veya adi gecersiz")
    if "\\" in value or _UNSAFE_ESCAPE.search(value):
        raise GithubPathError("GitHub yolu kodlanmis ayirici veya denetim karakteri iceremez")
    return value


def validate_repository(value):
    """Return an exact owner/repository identifier; URLs and relative paths fail."""
    value = _text(value)
    parts = value.split("/")
    if (len(parts) != 2 or not _OWNER.fullmatch(parts[0])
            or not _REPOSITORY.fullmatch(parts[1]) or parts[1] in (".", "..")):
        raise GithubPathError("GitHub deposu owner/repository biciminde olmali")
    return value


def _relative_path(value, *, allow_root=False):
    value = _text(value)
    if not value and allow_root:
        return value
    if (not value or value.startswith("/") or re.match(r"^[A-Za-z]:", value)
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise GithubPathError("GitHub dosya yolu depo icinde goreli olmali")
    return value


def _credential_name(name):
    if name in _CREDENTIAL_DIRECTORIES or name == "ayarlar.json":
        return True
    if name.endswith(_CREDENTIAL_EXTENSIONS) or name.startswith("id_rsa"):
        return True
    # Published templates remain usable; actual environment files do not.
    if re.fullmatch(r".*\.env\.(?:example|ornek)", name):
        return False
    return bool(re.search(r"(?:^|\.)env(?:\.|$)", name))


def _protected_write_paths():
    # Operator-configured additions cannot remove the built-in security paths.
    additions = os.environ.get("BASAK_GITHUB_PROTECTED_PATHS", "").split(",")
    for path in (*_DEFAULT_PROTECTED_PATHS, *additions):
        path = path.strip()
        if path:
            directory = path.endswith("/")
            path = _relative_path(path.rstrip("/"))
            yield path.casefold(), directory


def validate_file_path(value, *, write=False):
    """Validate a repository path; empty means root listing only for a read.

    Credentials are unreadable and unwritable. Writes additionally protect
    security/deployment paths and comma-separated BASAK_GITHUB_PROTECTED_PATHS.
    Directory additions end in '/'; other additions match one exact file.
    """
    value = _relative_path(value, allow_root=not write)
    folded = value.casefold()
    if any(_credential_name(part) for part in folded.split("/")):
        raise GithubPathError("GitHub kimlik bilgisi veya gizli dosya yolu kullanilamaz")
    if write:
        for path, directory in _protected_write_paths():
            if folded == path or (directory and folded.startswith(path + "/")):
                raise GithubPathError("GitHub guvenlik veya yayin dosyasi bu baglantiyla degistirilemez")
    return value


def validate_branch(value):
    """Validate an unqualified branch name; ownership/protection is checked by caller."""
    value = _relative_path(value)
    if (value.casefold().startswith("refs/") or value == "@"
            or value.casefold() == "head" or value.startswith("-")
            or ".." in value or "@{" in value or value.endswith(".")
            or any(char.isspace() or char in "~^:?*[" for char in value)
            or any(part.startswith(".") or part.casefold().endswith(".lock")
                   for part in value.split("/"))):
        raise GithubPathError("GitHub dal adi gecersiz veya nitelikli ref")
    return value
