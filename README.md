# trackman

Python client for the Trackman Golf API, reverse-engineered from iOS app traffic.

## Install

```bash
pip install -e .
```

## Usage

### Authentication

```python
from trackman import TrackmanClient

client = TrackmanClient.login("you@email.com", "yourpassword")

# Save tokens for later (avoid re-logging in)
access_token = client.access_token
refresh_token = client.refresh_token

# Restore from saved tokens
client = TrackmanClient.from_tokens(access_token, refresh_token)
client.refresh_tokens()  # get a fresh access token
```

### Profile & handicap

```python
profile = client.get_profile()
print(profile["fullName"])
print(profile["playerData"]["hcp"]["currentHcp"])

hcp = client.get_handicap()
print(f"HCP: {hcp['hcpOld']} → {hcp['hcpNew']}")
print(f"Based on rounds: {[r['name'] for r in hcp['avgBasedOn']]}")
```

### Rounds

```python
# List recent activities
activities = client.get_activities(take=20, kinds=["COURSE_PLAY"])
for a in activities:
    print(a["time"][:10], a["course"]["displayName"], a["grossScore"])

# Full round with hole-by-hole data
round_data = client.get_round(activities[0]["id"])
for hole in round_data["scorecard"]["holes"]:
    print(f"Hole {hole['holeNumber']}: par {hole['par']}, score {hole['score']}")

# Round + shot measurements (slower — one API call per shot)
round_full = client.get_round_with_measurements(activities[0]["id"])

# Shot measurement for a specific shot
shot = client.get_shot_measurement("U2NvcmVjYXJkU2hvd...")
print(f"Ball speed: {shot['ballSpeed']} mph")
print(f"Carry: {shot['carry']} yards")
print(f"Spin: {shot['spinRate']} rpm")
```

### Practice sessions

```python
activities = client.get_activities(take=20, kinds=["VIRTUAL_RANGE"])
session = client.get_practice_session(activities[0]["id"])

for i, stroke in enumerate(session["strokes"], 1):
    m = stroke["measurement"]
    print(f"{i:3d} {stroke['club']:20s} carry={m['carryActual']:.1f}y  spin={m['spinRate']:.0f}")
```

### Stats & export

```python
# Per-round stats (drive distance, FIR, GIR, scrambles)
stats = client.get_scorecard_stats(take=20)

# Flat dicts ready for pandas
rows = client.export_rounds_to_dicts(take=20)
import pandas as pd
df = pd.DataFrame(rows)
print(df[["date", "course", "gross", "fir_pct", "gir", "drive_avg_yards"]])

# Practice session as flat dicts
shots = client.export_practice_to_dicts("VmlydHVhbFJhbmdlU2Vzc2lvbkFjdGl2aXR5Cm...")
df = pd.DataFrame(shots)
print(df[["club", "carry_yards", "ball_speed_mph", "spin_rate_rpm", "face_angle_deg"]].describe())
```

### Equipment / bag

```python
bag = client.get_bag()
for club in bag:
    fmd = club["findMyDistance"]
    if fmd["numberOfShots"] > 0:
        print(f"{club['displayName']:15s} avg carry: {fmd['clubStats']['carry']:.0f}y")
```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `api.trackmangolf.com/graphql` | All GraphQL queries |
| GET | `api.trackmangolf.com/api/hcp/record` | Handicap calculation detail |
| GET | `api.trackmangolf.com/api/system/version` | App version info |
| GET | `login.trackmangolf.com/api/account/profile` | Account profile |

All requests use Bearer token auth obtained via OAuth2 PKCE flow.

## Notes

- The iOS app uses GraphQL for almost everything — a single `/graphql` endpoint
- Auth is standard OAuth2 PKCE via `login.trackmangolf.com`
- Shot measurement data varies by sensor type — indoor simulators capture more
  fields (clubSpeed, attackAngle, clubPath) than outdoor GPS-only tracking
- Be respectful with request rates; add `time.sleep()` between bulk calls
