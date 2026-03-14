# trackman

Python client for the Trackman Golf API, reverse-engineered from iOS app traffic.

## Install

```bash
pip install -e .
```

## Authentication

The library uses OAuth2 PKCE flow against `login.trackmangolf.com`.

> **Note:** Trackman's login page may trigger a CAPTCHA for automated login attempts,
> causing `TrackmanClient.login()` to fail. If this happens, use `trackman_auth.py`
> (which handles token persistence) or capture tokens directly from the iOS app using
> a proxy like [Proxyman](https://proxyman.io) and load them with `from_tokens()`.

```python
from trackman import TrackmanClient

# Login (may fail if CAPTCHA is triggered)
client = TrackmanClient.login("you@email.com", "yourpassword")

# Or load tokens captured from the iOS app / saved previously
client = TrackmanClient.from_tokens(access_token, refresh_token)
client.refresh_tokens()  # exchange refresh token for a fresh access token

# Save tokens to avoid re-authenticating
access_token = client.access_token
refresh_token = client.refresh_token
```

### Token persistence helper

`trackman_auth.py` saves tokens to `~/.trackman_tokens.json` and auto-refreshes on
subsequent calls. Falls back to prompting for credentials only if refresh fails.

```python
from trackman_auth import get_client
client = get_client()  # handles everything automatically
```

## Activity kinds

Trackman tracks three kinds of activities. Pass one or more to `get_activities()`:

| Kind | Description |
|------|-------------|
| `COURSE_PLAY` | On-course rounds with scorecard |
| `VIRTUAL_RANGE` | Range/simulator sessions with target distances |
| `SHOT_ANALYSIS` | Indoor launch monitor sessions (no target distance) |

```python
# All activities (all kinds)
activities = client.get_activities(take=20)

# Just rounds
rounds = client.get_activities(take=20, kinds=["COURSE_PLAY"])

# Practice sessions (both range and shot analysis)
practice = client.get_activities(take=20, kinds=["VIRTUAL_RANGE", "SHOT_ANALYSIS"])
```

## Rounds

```python
activities = client.get_activities(take=20, kinds=["COURSE_PLAY"])
for a in activities:
    print(a["time"][:10], a["course"]["displayName"], a["grossScore"])

# Per-round stats (drive distance, FIR, GIR, putts, scrambles)
stats = client.get_scorecard_stats(take=20)

# Flat dicts ready for pandas
rows = client.export_rounds_to_dicts(take=20)
import pandas as pd
df = pd.DataFrame(rows)
print(df[["date", "course", "gross", "fir_pct", "gir", "drive_avg_yards"]])
```

### Shot measurements on-course

Individual shot measurements (launch angle, ball speed, spin, etc.) can be fetched
per shot ID. Note: the `kind` argument has been removed from the API.

```python
# Get shot IDs from a round
ROUND_SHOTS = """
query ReportCourse($nodeId: ID!) {
  node(id: $nodeId) {
    ... on CoursePlayActivity {
      scorecard { holes { holeNumber shots { id shotNumber } } }
    }
  }
}
"""
data = client._graphql(ROUND_SHOTS, variables={"nodeId": activity_id})
shots = [shot for hole in data["node"]["scorecard"]["holes"] for shot in hole["shots"]]

# Fetch measurement for each shot
SHOT_MEASUREMENT = """
query ShotMeasurement($shotId: ID!) {
  node(id: $shotId) {
    ... on ScorecardShot {
      measurement {
        launchAngle ballSpeed carry spinRate clubPath faceAngle attackAngle smashFactor
      }
    }
  }
}
"""
for shot in shots:
    m = client._graphql(SHOT_MEASUREMENT, variables={"shotId": shot["id"]})
    print(m["node"]["measurement"])
```

## Practice sessions

Both `VIRTUAL_RANGE` and `SHOT_ANALYSIS` sessions have the same stroke/measurement
structure. Use `export_practice_to_dicts()` for flat output or fetch raw strokes:

```python
activities = client.get_activities(take=5, kinds=["SHOT_ANALYSIS", "VIRTUAL_RANGE"])

# Flat dicts (one row per shot)
shots = client.export_practice_to_dicts(activities[0]["id"])
import pandas as pd
df = pd.DataFrame(shots)
print(df[["club", "carry_yards", "ball_speed_mph", "spin_rate_rpm",
          "launch_angle_deg", "face_angle_deg", "club_path_deg"]].describe())
```

> **Note:** `SHOT_ANALYSIS` sessions typically don't record `carryActual`/`totalActual`
> (no virtual range target), but do capture all ball flight metrics.

## Profile & handicap

```python
profile = client.get_profile()
print(profile["fullName"])
print(profile["playerData"]["hcp"]["currentHcp"])

hcp = client.get_handicap()
print(f"HCP: {hcp['hcpOld']} → {hcp['hcpNew']}")
```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `api.trackmangolf.com/graphql` | All GraphQL queries |
| GET | `api.trackmangolf.com/api/hcp/record` | Handicap calculation detail |
| GET | `login.trackmangolf.com/api/account/profile` | Account profile |

All requests use Bearer token auth obtained via OAuth2 PKCE flow.

## Known API limitations

The Trackman GraphQL API has changed since initial reverse engineering. The following
fields **no longer exist** and will return errors if queried:

- `ScorecardHole.score`, `ScorecardHole.fairwayHit`
- `ScorecardShot.clubType`, `ScorecardShot.lie`, `ScorecardShot.result`
- `ScorecardShot.measurement(kind:)` — the `kind` argument has been removed
- `FindMyDistanceShot.id`, `.time`, `.carryActual`, `.totalActual`, `.ballSpeed`
- `StrokeTargetInterface.distance`

Use `client._graphql()` directly with trimmed queries if the high-level methods fail.

## Notes

- Auth is standard OAuth2 PKCE via `login.trackmangolf.com`
- The iOS app uses a single `/graphql` endpoint for almost all data
- Shot measurement completeness varies by sensor — indoor simulators capture more
  fields (clubSpeed, attackAngle, clubPath) than outdoor GPS tracking
- Be respectful with request rates; add `time.sleep()` between bulk calls
