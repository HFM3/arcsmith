"""Packaging metadata consistency checks.

These tests guard metadata that is easy to forget: the version printed in the README citation.
The BibTeX block in README.md hardcodes a ``version = {...}`` so users can cite
an exact release.
"""

import re
import sys
from pathlib import Path

import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover - project requires-python is >=3.11
    import tomli as tomllib

# tests/ lives directly under the package root, alongside pyproject.toml and
# README.md (see conftest.py, which resolves src/ the same way).
PKG_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = PKG_ROOT / "pyproject.toml"
README = PKG_ROOT / "README.md"

# Docs live in the sibling arcsmith-docs/ tree, which is NOT part of the sdist.
# These paths exist only in the source repo, so the cite-page checks below skip
# when the suite runs from a packaged install.
REPO_ROOT = PKG_ROOT.parent
# GitHub landing copy of the README. Not part of the sdist, so the check skips
# from a packaged install.
ROOT_README = REPO_ROOT / "README.md"
CITE_PAGE = REPO_ROOT / "arcsmith-docs" / "docs" / "cite.md"
HOOK = REPO_ROOT / "arcsmith-docs" / "hooks" / "copy_homepage.py"

# The cite page keeps version/year as build-time tokens (filled by the hook on
# ``mkdocs build``) instead of hardcoding them, so it never drifts from the
# release. These checks make sure that mechanism stays intact.
CITE_TOKENS = ("__ARCSMITH_VERSION__", "__ARCSMITH_YEAR__")


def _pyproject_version():
    with PYPROJECT.open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _bibtex_version(path):
    match = re.search(r"version\s*=\s*\{([^}]+)\}", path.read_text(encoding="utf-8"))
    assert match is not None, f"no BibTeX 'version = {{...}}' found in {path.name}"
    return match.group(1).strip()


def test_readme_citation_version_matches_pyproject():
    expected = _pyproject_version()
    found = _bibtex_version(README)
    assert found == expected, (
        f"PyPI README citation version {found!r} does not match pyproject "
        f"version {expected!r}. Update the BibTeX block in README.md when "
        f"bumping the release."
    )


def test_root_readme_citation_version_matches_pyproject():
    """The repo-root GitHub README carries the same version-pinned BibTeX as the
    PyPI README; keep both in sync with pyproject. Skips from a packaged install
    where the root README is not present."""
    if not ROOT_README.exists():
        pytest.skip("repo-root README not present (packaged install); repo-only check")
    expected = _pyproject_version()
    found = _bibtex_version(ROOT_README)
    assert found == expected, (
        f"root README citation version {found!r} does not match pyproject "
        f"version {expected!r}. Update the BibTeX block in the repo-root "
        f"README.md when bumping the release."
    )


def test_cite_page_stays_templated():
    """The docs cite page must keep its build-time tokens rather than hardcode a
    version, so the hook can fill it on every build and it never drifts."""
    if not CITE_PAGE.exists():
        pytest.skip("arcsmith-docs not present (packaged install); repo-only check")
    text = CITE_PAGE.read_text(encoding="utf-8")
    for token in CITE_TOKENS:
        assert token in text, (
            f"cite page is missing {token!r}. Keep version/year as build-time "
            f"tokens so the docs hook fills them; do not hardcode a version."
        )


def test_cite_tokens_are_filled_by_hook():
    """Every token the cite page relies on must be substituted by the build
    hook, or the published page would render the literal ``__ARCSMITH_*__``."""
    if not (CITE_PAGE.exists() and HOOK.exists()):
        pytest.skip("arcsmith-docs not present (packaged install); repo-only check")
    page = CITE_PAGE.read_text(encoding="utf-8")
    hook = HOOK.read_text(encoding="utf-8")
    for token in CITE_TOKENS:
        if token in page:
            assert token in hook, (
                f"cite page uses {token!r} but the build hook never replaces "
                f"it; the published page would show the literal token."
            )
