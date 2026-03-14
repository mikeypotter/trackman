"""
Trackman OAuth2 PKCE authentication.

The app uses standard OAuth2 PKCE flow:
  1. GET /connect/authorize  (with code_challenge)
  2. POST /Account/Login     (email + password form post)
  3. GET callback            (returns auth code)
  4. POST /connect/token     (exchange code for tokens)
"""

import hashlib
import base64
import os
import re
import requests
from urllib.parse import urlencode, urlparse, parse_qs
from dataclasses import dataclass


AUTH_BASE = "https://login.trackmangolf.com"
CLIENT_ID = "old-golf-app.c686e909-5102-45ac-9860-8d0b789073ae"
REDIRECT_URI = "dk.trackman.range://oauth"
SCOPES = " ".join([
    "openid",
    "offline_access",
    "profile",
    "https://auth.trackman.com/dr/simulate",
    "https://auth.trackman.com/dr/cloud",
    "https://auth.trackman.com/login/autoconsent",
])


@dataclass
class TokenSet:
    access_token: str
    refresh_token: str
    id_token: str
    expires_in: int


def _pkce_pair() -> tuple[str, str]:
    """Generate a PKCE code_verifier and code_challenge (S256)."""
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _get_csrf_token(session: requests.Session, login_url: str) -> str:
    """Load the login page and extract the CSRF token."""
    resp = session.get(login_url, allow_redirects=True)
    resp.raise_for_status()
    match = re.search(r'name="__RequestVerificationToken"[^>]+value="([^"]+)"', resp.text)
    if not match:
        raise ValueError("Could not find CSRF token on login page")
    return match.group(1)


def login(email: str, password: str) -> TokenSet:
    """
    Authenticate with Trackman and return a TokenSet.

    Args:
        email:    Your Trackman account email.
        password: Your Trackman account password.

    Returns:
        TokenSet with access_token, refresh_token, id_token, expires_in.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "TrackManGolf/1 CFNetwork/1494.0.7 Darwin/23.4.0",
    })

    verifier, challenge = _pkce_pair()
    state = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode()

    # Step 1: Initiate authorization — follow redirects to land on the login page
    auth_params = {
        "response_type": "code",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "client_id": CLIENT_ID,
        "scope": SCOPES,
        "redirect_uri": REDIRECT_URI,
        "style": "RangeApp",
        "requiredProperties": "nickname",
        "display": "touch",
        "culture": "en-US",
    }
    auth_url = f"{AUTH_BASE}/connect/authorize?" + urlencode(auth_params)

    # Follow redirect chain to get the login page URL (with returnUrl baked in)
    resp = session.get(auth_url, allow_redirects=True)
    login_page_url = resp.url  # final URL after redirects

    # Step 2: Extract CSRF token from the login form
    csrf = _get_csrf_token(session, login_page_url)

    # Step 3: POST credentials
    # Build the login POST URL (same path as login page but as POST)
    post_url = login_page_url.replace("/Account/Login", "/Account/Login")
    # The returnUrl is in the query string — keep it
    login_resp = session.post(
        post_url,
        data={
            "Email": email,
            "Password": password,
            "Captcha": "",
            "__RequestVerificationToken": csrf,
        },
        allow_redirects=True,
    )

    # Step 4: Extract auth code from the final redirect URL
    # After login the server redirects to our redirect_uri with ?code=...
    # requests can't follow custom-scheme URIs, so we look for it in the history
    code = None
    for r in login_resp.history + [login_resp]:
        location = r.headers.get("Location", "")
        if location.startswith(REDIRECT_URI) or "code=" in location:
            parsed = urlparse(location)
            qs = parse_qs(parsed.query)
            if "code" in qs:
                code = qs["code"][0]
                break
        # Also check the final response URL
        if "code=" in r.url:
            qs = parse_qs(urlparse(r.url).query)
            if "code" in qs:
                code = qs["code"][0]
                break

    if not code:
        raise ValueError(
            "Login failed: could not extract authorization code. "
            "Check your credentials or whether Trackman requires a CAPTCHA."
        )

    # Step 5: Exchange code for tokens
    token_resp = session.post(
        f"{AUTH_BASE}/connect/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
            "client_id": CLIENT_ID,
        },
    )
    token_resp.raise_for_status()
    tokens = token_resp.json()

    return TokenSet(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token", ""),
        id_token=tokens.get("id_token", ""),
        expires_in=tokens.get("expires_in", 3600),
    )


def refresh(refresh_token: str) -> TokenSet:
    """Exchange a refresh token for a new TokenSet."""
    resp = requests.post(
        f"{AUTH_BASE}/connect/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
        },
    )
    resp.raise_for_status()
    tokens = resp.json()
    return TokenSet(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token", refresh_token),
        id_token=tokens.get("id_token", ""),
        expires_in=tokens.get("expires_in", 3600),
    )
