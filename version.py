"""The one place the version number lives.

Build scripts read this file so the installer, the bundle and the update
check can never disagree about what version they are.
"""

__version__ = "1.2.1"

GITHUB_OWNER = "payrghfgh"
GITHUB_REPO = "Circle"
GITHUB_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
RELEASES_API = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def version_tuple(text: str) -> tuple:
    """'v1.2.0' -> (1, 2, 0). Anything unparseable sorts lowest."""
    cleaned = (text or "").strip().lstrip("vV")
    parts = []
    for chunk in cleaned.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    # Always four components: comparing a 3-tuple against a 4-tuple would
    # make (1, 2, 0) sort below (1, 2, 0, 0) and mis-rank releases.
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])
