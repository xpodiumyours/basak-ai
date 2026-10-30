"""Logical GitHub identifiers cannot redirect the authenticated HTTP adapter."""
from urllib.parse import quote

import httpx
import pytest

from chat.platform_github_paths import (
    GithubPathError, validate_branch, validate_file_path, validate_repository,
)


@pytest.mark.parametrize("value", [
    "xpodiumyours/basak-ai", "owner/repo.name", "org-name/repo_2",
])
def test_repository_accepts_owner_and_repository(value):
    assert validate_repository(value) == value


@pytest.mark.parametrize("value", [
    "owner/..", "owner/.", "../repo", "/owner/repo", "owner/repo/extra",
    "owner\\repo", "owner/repo?x=1", "owner/repo#fragment", "owner/%2e%2e",
    "https://github.com/owner/repo", "owner/rep\no", "owner/repo\x00", " owner/repo",
])
def test_repository_rejects_path_or_url_manipulation(value):
    with pytest.raises(GithubPathError):
        validate_repository(value)


@pytest.mark.parametrize("value", [
    "../collaborators/example-user", "../../repo2/contents/demo.txt",
    "../../../../user/starred/owner/repo", "/etc/passwd", "C:/secrets.txt",
    "folder\\file.txt", "./README.md", "folder/../file.txt", "folder//file.txt",
    "folder/./file.txt", "folder/%2e%2e/file.txt", "%252E%252E/file.txt",
    "%25252fsecret", "folder%2Fsecret", "folder%5csecret", "a%0d%0Ab",
    "a\x00b", "a\nb", "a\u202eb", "folder/",
])
def test_file_path_rejects_escape_and_ambiguous_components(value):
    with pytest.raises(GithubPathError):
        validate_file_path(value)


@pytest.mark.parametrize("value", [
    ".git/config", "folder/.GIT/config", ".aws/credentials", ".ssh/config",
    ".env", ".ENV.local", "config/production.env", "config/basak.env.local",
    "config/secret.pem", "config/SECRET.KEY", "config/cert.p12", "ayarlar.json",
    "config/AYARLAR.JSON", "config/id_rsa", "config/id_rsa.pub",
])
@pytest.mark.parametrize("write", [False, True])
def test_credentials_cannot_be_read_or_written(value, write):
    with pytest.raises(GithubPathError):
        validate_file_path(value, write=write)


@pytest.mark.parametrize("value", [
    ".env.example", ".env.ornek", "config/basak.env.ornek", "README.md",
    "src/çalışma/Örnek dosya.py", "src/environment.py", "src/file#name?.txt",
    "src/discount%20off.txt",
])
def test_regular_files_and_environment_examples_remain_available(value):
    assert validate_file_path(value, write=True) == value


def test_only_read_can_list_repository_root():
    assert validate_file_path("") == ""
    with pytest.raises(GithubPathError):
        validate_file_path("", write=True)


@pytest.mark.parametrize("value", [
    ".github/workflows/test.yml", ".GITHUB/CODEOWNERS", "AGENTS.md", "security.MD",
    "Resmidokumanuyum.md", "deploy/oracle/setup.sh", "chat/platform_connectors.py",
    "chat/platform_accounts_api.py", "chat/platform_connections.py",
    "chat/platform_github_app.py", "chat/platform_github_paths.py",
])
def test_security_and_release_sources_can_be_read_but_not_changed(value):
    assert validate_file_path(value) == value
    with pytest.raises(GithubPathError):
        validate_file_path(value, write=True)


def test_operator_protected_paths_extend_mandatory_defaults(monkeypatch):
    monkeypatch.setenv("BASAK_GITHUB_PROTECTED_PATHS", "internal/,config/policy.json")
    for path in ("internal/settings.py", "INTERNAL/settings.py", "config/policy.json", "AGENTS.md"):
        with pytest.raises(GithubPathError):
            validate_file_path(path, write=True)
    assert validate_file_path("internality/settings.py", write=True)
    assert validate_file_path("config/policy.json.example", write=True)


def test_invalid_protected_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("BASAK_GITHUB_PROTECTED_PATHS", "../policy")
    with pytest.raises(GithubPathError):
        validate_file_path("README.md", write=True)


@pytest.mark.parametrize("value", [
    "fix/github-example", "basak/connection-1/iş-20261030", "feature-1", "main",
])
def test_branch_name_validation_preserves_ownership_decision_for_caller(value):
    assert validate_branch(value) == value


@pytest.mark.parametrize("value", [
    "", "../main", "feature/../main", "refs/heads/main", "REFS/heads/main",
    "/main", "feature//name", "feature\\name", "feature/.hidden", "feature.lock",
    "feature/name.LOCK", "feature..main", "feature@{1}", "feature.", "feature/",
    "feature?query", "feature#name\n", "feature name", "feature:name", "-main", "HEAD",
    "@", "feature%2Fmain", "feature%252fmain", "feature*", "feature[1]",
])
def test_branch_rejects_qualified_refs_and_invalid_git_ref_names(value):
    with pytest.raises(GithubPathError):
        validate_branch(value)


def test_outgoing_contents_url_keeps_turkish_filename_inside_selected_repository():
    repo = validate_repository("xpodiumyours/basak-ai")
    path = validate_file_path("src/çalışma/Örnek dosya#1?.py", write=True)
    request = httpx.Request("PUT", "https://api.github.com/repos/" + repo + "/contents/" + quote(path, safe="/"))
    assert request.url.host == "api.github.com"
    assert request.url.raw_path == (
        b"/repos/xpodiumyours/basak-ai/contents/src/%C3%A7al%C4%B1%C5%9Fma/"
        b"%C3%96rnek%20dosya%231%3F.py")
    assert not request.url.query


def test_reported_traversal_cannot_construct_collaborator_or_cross_repository_request():
    requests = []
    for path in ("../collaborators/example-user", "../../repo2/contents/demo.txt"):
        with pytest.raises(GithubPathError):
            safe_path = validate_file_path(path, write=True)
            requests.append(httpx.Request("PUT", "https://api.github.com/repos/owner/repo/contents/" + quote(safe_path, safe="/")))
    assert requests == []
