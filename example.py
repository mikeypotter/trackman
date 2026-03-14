"""
example.py — demonstrates common use cases for the Trackman client.
Run: python example.py
"""

import json
from trackman import TrackmanClient


def main():
    # ----------------------------------------------------------------
    # 1. Login
    # ----------------------------------------------------------------
    client = TrackmanClient.login("you@email.com", "yourpassword")
    print(f"Logged in. Access token: {client.access_token[:30]}...")

    # ----------------------------------------------------------------
    # 2. Profile
    # ----------------------------------------------------------------
    profile = client.get_profile()
    print(f"\nPlayer: {profile['fullName']}")
    print(f"Handicap: {profile['playerData']['hcp']['currentHcp']}")

    hcp = client.get_handicap()
    print(f"HCP movement: {hcp['hcpOld']} → {hcp['hcpNew']}")
    print(f"Last score: {hcp['adjustedGrossScore']} at {hcp['scorecard']['name']}")

    # ----------------------------------------------------------------
    # 3. Recent rounds summary
    # ----------------------------------------------------------------
    print("\n--- Recent rounds ---")
    rows = client.export_rounds_to_dicts(take=10)
    for r in rows:
        fir = f"{r['fir_pct']}%" if r["fir_pct"] is not None else "—"
        print(
            f"{r['date']}  {r['course']:25s}  "
            f"gross={r['gross'] or '—':>3}  "
            f"FIR={fir:>5}  GIR={r['gir'] or '—':>2}  "
            f"drive={r['drive_avg_yards'] or '—'}y"
        )

    # ----------------------------------------------------------------
    # 4. Full round detail (most recent completed)
    # ----------------------------------------------------------------
    completed = [r for r in rows if r["gross"]]
    if completed:
        activity_id = completed[0]["activity_id"]
        print(f"\n--- Round detail: {completed[0]['date']} {completed[0]['course']} ---")
        round_data = client.get_round(activity_id)
        for hole in round_data.get("scorecard", {}).get("holes", []):
            score = hole.get("score", "?")
            par = hole.get("par", "?")
            delta = (score - par) if isinstance(score, int) and isinstance(par, int) else "?"
            sign = "+" if isinstance(delta, int) and delta > 0 else ""
            print(
                f"  Hole {hole['holeNumber']:>2}  par {par}  score {score}  ({sign}{delta})"
                f"  FIR={'Y' if hole.get('fairwayHit') else 'N'}  GIR={'Y' if hole.get('greenInRegulation') else 'N'}"
            )

    # ----------------------------------------------------------------
    # 5. Practice session
    # ----------------------------------------------------------------
    range_activities = client.get_activities(take=10, kinds=["VIRTUAL_RANGE"])
    if range_activities:
        print(f"\n--- Practice session: {range_activities[0]['time'][:10]} ({range_activities[0]['strokeCount']} shots) ---")
        shots = client.export_practice_to_dicts(range_activities[0]["id"])

        # Group by club
        clubs = {}
        for s in shots:
            club = s["club"]
            if club not in clubs:
                clubs[club] = []
            if s["carry_yards"] is not None:
                clubs[club].append(s)

        for club, club_shots in clubs.items():
            if not club_shots:
                continue
            avg_carry = sum(s["carry_yards"] for s in club_shots) / len(club_shots)
            avg_spin = sum(s["spin_rate_rpm"] for s in club_shots if s["spin_rate_rpm"]) / max(1, sum(1 for s in club_shots if s["spin_rate_rpm"]))
            print(f"  {club:20s}  n={len(club_shots):>2}  avg carry={avg_carry:.0f}y  avg spin={avg_spin:.0f}rpm")

    # ----------------------------------------------------------------
    # 6. Bag
    # ----------------------------------------------------------------
    print("\n--- Bag ---")
    bag = client.get_bag()
    for club in bag:
        fmd = club["findMyDistance"]
        n = fmd["numberOfShots"]
        if n > 0:
            print(f"  {club['displayName']:15s}  shots={n:>3}  carry={fmd['clubStats']['carry']:.0f}y")
        else:
            print(f"  {club['displayName']:15s}  (no data)")


if __name__ == "__main__":
    main()
