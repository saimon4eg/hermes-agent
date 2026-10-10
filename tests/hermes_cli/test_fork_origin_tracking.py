"""Fork guard: this checkout must keep updating from saimon4eg/hermes-agent.

Why this exists
---------------
``hermes update`` decides whether a checkout is a fork by comparing its
``origin`` URL against ``OFFICIAL_REPO_URLS`` (``hermes_cli.update_cmd_git``).
A checkout is a "fork" — i.e. it gets the upstream-comparison machinery and the
"⚠ Updating from fork" banner — only when its origin is NOT in that set.

This fork points every install/update path at ``saimon4eg/hermes-agent`` and
lists those URLs as authoritative, so ``_is_fork()`` returns False and the
updater simply tracks ``origin``. That is the intended behaviour and it must
survive an upgrade: the patch that establishes it is part of the fork's ``main``,
so every pulled revision re-applies it.

If this test fails after an upstream merge, the merge has reset one of those
constants back to the upstream repository — re-apply the fork URLs before
pushing ``main``, or the installed checkout will start offering to sync with
(and eventually fast-forward towards) NousResearch instead of this fork.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hermes_cli.update_cmd_git import OFFICIAL_REPO_URL, OFFICIAL_REPO_URLS, _is_fork

FORK_OWNER = "saimon4eg"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "origin",
    [
        "https://github.com/saimon4eg/hermes-agent.git",
        "git@github.com:saimon4eg/hermes-agent.git",
        "https://github.com/saimon4eg/hermes-agent",
        "git@github.com:saimon4eg/hermes-agent",
    ],
)
def test_this_forks_origin_is_treated_as_authoritative(origin):
    """``_is_fork()`` False → the updater tracks origin and never offers upstream."""
    assert _is_fork(origin) is False


@pytest.mark.parametrize(
    "origin",
    [
        "https://github.com/NousResearch/hermes-agent.git",
        "git@github.com:NousResearch/hermes-agent.git",
    ],
)
def test_upstream_origin_is_seen_as_a_foreign_fork(origin):
    """NousResearch is not in this fork's authoritative set, so it reads as a fork."""
    assert _is_fork(origin) is True


def test_official_url_constants_point_at_this_fork():
    assert FORK_OWNER in OFFICIAL_REPO_URL
    assert all(FORK_OWNER in url for url in OFFICIAL_REPO_URLS)
    assert not any("NousResearch" in url for url in OFFICIAL_REPO_URLS)


def test_zip_update_fallback_targets_this_fork():
    """The Windows ZIP fallback downloads an archive by ``owner/repo``."""
    source = (_PROJECT_ROOT / "hermes_cli" / "update_cmd_zip.py").read_text(encoding="utf-8")
    assert f'saimon4eg/hermes-agent' in source, "ZIP fallback must download this fork's archive"
    assert 'target_repository or "NousResearch/hermes-agent"' not in source


@pytest.mark.parametrize(
    "relative, pattern",
    [
        ("scripts/install.sh", r'REPO_URL="\$\{HERMES_REPO_URL:-([^}"]+)\}"'),
        # The ps1 default sits in an ``if (...) { ... } else { "<url>" }`` expression, so
        # take the first quoted URL on the assignment line rather than balancing braces.
        ("scripts/install.ps1", r'\$RepoUrl\b[^\r\n]*"(https://github\.com/[^"]+)"'),
    ],
)
def test_installer_default_repo_url_points_at_this_fork(relative, pattern):
    """A fresh install (no ``HERMES_REPO_URL`` override) clones this fork."""
    text = (_PROJECT_ROOT / relative).read_text(encoding="utf-8")
    match = re.search(pattern, text)
    assert match is not None, f"could not locate the default repo URL in {relative}"
    assert FORK_OWNER in match.group(1), match.group(1)


def test_bootstrap_installer_downloads_scripts_from_this_fork():
    """The desktop bootstrap installer fetches install scripts by raw URL."""
    source = (_PROJECT_ROOT / "apps" / "bootstrap-installer" / "src-tauri" / "src" / "install_script.rs").read_text(encoding="utf-8")
    assert f"raw.githubusercontent.com/{FORK_OWNER}/hermes-agent" in source
