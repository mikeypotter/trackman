"""
trackman — Python client for the Trackman Golf API.

Quick start:
    from trackman import TrackmanClient

    client = TrackmanClient.login("you@email.com", "yourpassword")

    profile = client.get_profile()
    print(profile["fullName"], "HCP:", profile["playerData"]["hcp"]["currentHcp"])

    rounds = client.export_rounds_to_dicts(take=10)
    for r in rounds:
        print(r["date"], r["course"], r["gross"], r["fir_pct"])
"""

from .client import TrackmanClient, TrackmanError
from .auth import TokenSet

__all__ = ["TrackmanClient", "TrackmanError", "TokenSet"]
__version__ = "0.1.0"
