"""
Token persistence helper for TrackmanClient.

Usage:
    from trackman_auth import get_client
    client = get_client()   # auto-refreshes; prompts for login only if needed

Token file: ~/.trackman_tokens.json
"""

import json
import os
import sys
from pathlib import Path

TOKEN_FILE = Path.home() / ".trackman_tokens.json"

sys.path.insert(0, str(Path(__file__).parent))
from trackman import TrackmanClient, TrackmanError


def _save(client: TrackmanClient):
    TOKEN_FILE.write_text(json.dumps({
        "access_token": client.access_token,
        "refresh_token": client.refresh_token,
    }))
    TOKEN_FILE.chmod(0o600)


def get_client() -> TrackmanClient:
    if TOKEN_FILE.exists():
        tokens = json.loads(TOKEN_FILE.read_text())
        client = TrackmanClient.from_tokens(
            tokens["access_token"], tokens["refresh_token"]
        )
        try:
            client.refresh_tokens()
            _save(client)
            return client
        except Exception:
            pass  # fall through to re-login

    email = input("Trackman email: ").strip()
    password = input("Trackman password: ").strip()
    client = TrackmanClient.login(email, password)
    _save(client)
    return client


if __name__ == "__main__":
    client = get_client()
    profile = client.get_profile()
    print(f"Logged in as: {profile['fullName']}")
    print(f"Handicap: {profile['playerData']['hcp']['currentHcp']}")
