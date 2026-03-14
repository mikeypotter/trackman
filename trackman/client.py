"""
Trackman API client.

Usage:
    from trackman import TrackmanClient

    client = TrackmanClient.login("you@email.com", "password")

    # Get your profile
    profile = client.get_profile()

    # Get activity list (rounds + range sessions)
    activities = client.get_activities(take=20)

    # Get full round detail with shot data
    round_data = client.get_round("Q291cnNlUGxheUFjdGl2aXR5...")

    # Get shot-level ball-flight data for a specific shot
    shot = client.get_shot_measurement("U2NvcmVjYXJkU2hvd...")

    # Get practice session with all strokes
    practice = client.get_practice_session("VmlydHVhbFJhbmdlU2Vzc2lvbkFjdGl2aXR5...")

    # Get shot analysis session (Trackman Pro/Studio) with normalized + raw measurements
    analysis = client.get_shot_analysis_session("U2hvdEFuYWx5c2lzU2Vzc2lvbkFjdGl2aXR5...")

    # Get handicap record
    hcp = client.get_handicap()

    # Get your bag + find-my-distance data
    bag = client.get_bag()

    # Get scorecard stats across last 20 rounds
    stats = client.get_scorecard_stats()
"""

from __future__ import annotations

import time
from typing import Any, Optional

import requests

from .auth import login as _login, refresh as _refresh, TokenSet
from . import queries


API_BASE = "https://api.trackmangolf.com"
LOGIN_BASE = "https://login.trackmangolf.com"

DEFAULT_HEADERS = {
    "User-Agent": "TrackManGolf/1 CFNetwork/1494.0.7 Darwin/23.4.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


class TrackmanError(Exception):
    """Raised when the Trackman API returns an error."""


class TrackmanClient:
    """
    Authenticated Trackman API client.

    Wraps both the GraphQL endpoint (api.trackmangolf.com/graphql)
    and the REST endpoints (api.trackmangolf.com/api/*).
    """

    def __init__(self, tokens: TokenSet):
        self._tokens = tokens
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        self._set_auth_header()

    def _set_auth_header(self):
        self._session.headers["Authorization"] = f"Bearer {self._tokens.access_token}"

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    @classmethod
    def login(cls, email: str, password: str) -> "TrackmanClient":
        """Authenticate and return a ready-to-use client."""
        tokens = _login(email, password)
        return cls(tokens)

    @classmethod
    def from_tokens(cls, access_token: str, refresh_token: str = "") -> "TrackmanClient":
        """Instantiate from existing tokens (e.g. loaded from disk)."""
        tokens = TokenSet(
            access_token=access_token,
            refresh_token=refresh_token,
            id_token="",
            expires_in=3600,
        )
        return cls(tokens)

    def refresh_tokens(self):
        """Refresh the access token using the stored refresh token."""
        if not self._tokens.refresh_token:
            raise TrackmanError("No refresh token available — please log in again.")
        self._tokens = _refresh(self._tokens.refresh_token)
        self._set_auth_header()

    @property
    def access_token(self) -> str:
        return self._tokens.access_token

    @property
    def refresh_token(self) -> str:
        return self._tokens.refresh_token

    # ------------------------------------------------------------------
    # Low-level request helpers
    # ------------------------------------------------------------------

    def _graphql(
        self,
        query: str,
        variables: Optional[dict] = None,
        operation_name: Optional[str] = None,
    ) -> dict:
        """Execute a GraphQL query and return the data dict."""
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        if operation_name:
            payload["operationName"] = operation_name

        resp = self._session.post(f"{API_BASE}/graphql", json=payload)
        resp.raise_for_status()
        body = resp.json()

        if "errors" in body:
            raise TrackmanError(f"GraphQL errors: {body['errors']}")

        return body.get("data", {})

    def _rest_get(self, path: str, **params) -> Any:
        """Perform a REST GET against the API base."""
        resp = self._session.get(f"{API_BASE}{path}", params=params or None)
        resp.raise_for_status()
        return resp.json()

    def _login_get(self, path: str, **params) -> Any:
        """Perform a REST GET against the login base (profile etc.)."""
        resp = self._session.get(f"{LOGIN_BASE}{path}", params=params or None)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Profile
    # ------------------------------------------------------------------

    def get_profile(self) -> dict:
        """
        Returns your Trackman profile: name, email, handicap, gender, etc.

        Example response (trimmed):
            {
              "fullName": "Mike Potter",
              "email": "mike@example.com",
              "playerData": {"hcp": {"currentHcp": 8.9}}
            }
        """
        data = self._graphql(queries.PROFILE_SHORT, operation_name="ProfileShort")
        return data["me"]["profile"]

    def get_account_profile(self) -> dict:
        """
        Returns the login-server profile (email, name, marketing consent).
        Uses the REST endpoint on login.trackmangolf.com.
        """
        return self._login_get("/api/account/profile")

    # ------------------------------------------------------------------
    # Activities (rounds + range sessions)
    # ------------------------------------------------------------------

    def get_activities(
        self,
        take: int = 20,
        skip: int = 0,
        kinds: Optional[list[str]] = None,
        include_hidden: bool = False,
    ) -> list[dict]:
        """
        Returns a list of activities (course rounds and range sessions).

        Args:
            take:           Number of activities to return (max 100).
            skip:           Offset for pagination.
            kinds:          Filter by kind, e.g. ["COURSE_PLAY", "VIRTUAL_RANGE", "SHOT_ANALYSIS"].
                            Pass None for all.
            include_hidden: Include hidden activities.

        Returns:
            List of activity dicts. CoursePlayActivity items include:
                id, time, state, toPar, grossScore, course.displayName, scorecard.id
            VirtualRangeSessionActivity items include:
                id, time, strokeCount
            ShotAnalysisSessionActivity items include:
                id, time, strokeCount
        """
        variables = {
            "take": take,
            "skip": skip,
            "activityKinds": kinds,
            "includeHidden": include_hidden,
        }
        data = self._graphql(queries.ACTIVITY_LIST, variables=variables, operation_name="ActivityList")
        return data["me"]["activities"]["items"]

    def get_all_activities(self, kinds: Optional[list[str]] = None) -> list[dict]:
        """Paginate through all activities and return the full list."""
        results = []
        skip = 0
        take = 50
        while True:
            page = self.get_activities(take=take, skip=skip, kinds=kinds)
            results.extend(page)
            if len(page) < take:
                break
            skip += take
            time.sleep(0.2)  # be polite
        return results

    # ------------------------------------------------------------------
    # Round detail
    # ------------------------------------------------------------------

    def get_round(self, activity_id: str) -> dict:
        """
        Returns full round detail for a CoursePlayActivity.

        Top-level fields: id, kind, state, toPar, netToPar, grossScore, gameType, time,
            stablefordToPar, stablefordPoints, skinsScore, matchScore, course, scorecard.

        scorecard fields: numberOfHolesPlayed, numberOfHolesToPlay, fairwayFirmness,
            greenFirmness, greenStimp, windMode, bayKind, stat, gameSettings, player,
            holes, otherPlayers.

        Per-hole fields: holeNumber, par, distance, strokeIndex, hcpStrokes, grossScore,
            netScore, stablefordPoint, putts, mulligans, gimmeWasGiven, isPlayed,
            skinsScore, matchScore, image, pinPosition, shots.

        Per-shot fields: shotNumber, total, club, shotResult, shotsToAdd, finalLie,
            launchLie, launchPosition, finalPosition, dropPosition.

        Aggregate stat fields: driveAverage, driveMax, driveCount, fairwayHitFairway,
            fairwayHitLeft, fairwayHitRight, greenInRegulation, birdies, bogeys,
            doubleBogeys, eagles, eaglesOrBetter, pars, scrambles, tripleBogeysOrWorse,
            numberOfPutts, averagePuttsPerHoleDecimal.

        Args:
            activity_id: The GraphQL node ID of the CoursePlayActivity.
                         Looks like "Q291cnNlUGxheUFjdGl2aXR5Cm..."
        """
        data = self._graphql(
            queries.REPORT_COURSE,
            variables={"nodeId": activity_id},
            operation_name="ReportCourse",
        )
        return data["node"]

    def get_shot_measurement(
        self, shot_id: str, kind: Optional[str] = None
    ) -> dict:
        """
        Returns ball-flight measurement data for a single shot.

        Args:
            shot_id: The GraphQL node ID of the ScorecardShot.
                     Looks like "U2NvcmVjYXJkU2hvd..."
            kind:    Optional ShotMeasurementKind (e.g. "INDOOR").

        Returns:
            Dict with ballSpeed, carry, spinRate, launchAngle, faceAngle,
            clubPath, smashFactor, dynamicLoft, attackAngle, etc.
            Null fields are where the sensor didn't capture data.
        """
        data = self._graphql(
            queries.COURSE_REPORT_MEASUREMENT,
            variables={"shotId": shot_id, "shotMeasurementKind": kind},
            operation_name="CourseReportMeasurementIndoor",
        )
        return data["node"]["measurement"]

    def get_round_with_measurements(self, activity_id: str) -> dict:
        """
        Convenience: fetch a full round AND all shot measurements in one call.

        Makes one API call per shot, so may be slow for full 18-hole rounds.
        Rate limits requests to be polite.

        Returns the round dict with each shot's 'measurement' field populated.
        """
        round_data = self.get_round(activity_id)
        holes = round_data.get("scorecard", {}).get("holes", [])
        for hole in holes:
            for shot in hole.get("shots", []):
                try:
                    shot["measurement"] = self.get_shot_measurement(shot["id"])
                    time.sleep(0.1)
                except Exception as e:
                    shot["measurement"] = None
                    shot["_measurement_error"] = str(e)
        return round_data

    # ------------------------------------------------------------------
    # Practice / Range sessions
    # ------------------------------------------------------------------

    def get_practice_session(self, activity_id: str) -> dict:
        """
        Returns a full virtual range session with per-stroke ball data.

        Top-level fields: id, kind, time, strokeCount, strokes.

        Per-stroke fields: club, targetDistance, target (type, distance; for circle
            targets: radius, hcp, tourRadius; for rectangle targets: length, width),
            measurement.

        Per-stroke measurement fields: id, time, kind, carryActual, totalActual,
            clubSpeed, ballSpeed, smashFactor, spinRate, spinAxis, curve, attackAngle,
            faceToPath, clubPath, faceAngle, launchAngle, launchDirection, maxHeight,
            carrySideActual, totalSideActual, dynamicLoft, dynamicLie, impactHeight,
            spinLoft, swingPlane, swingDirection, impactOffset, landingAngle,
            ballTrajectory (kind, timeInterval, measuredTimeInterval, validTimeInterval,
            xFit, yFit, zFit, spinRateFit).

        Args:
            activity_id: The GraphQL node ID of the VirtualRangeSessionActivity.
                         Looks like "VmlydHVhbFJhbmdlU2Vzc2lvbkFjdGl2aXR5Cm..."
        """
        data = self._graphql(
            queries.REPORT_VIRTUAL_RANGE,
            variables={"nodeId": activity_id},
            operation_name="ReportVirtualRange",
        )
        return data["node"]

    def get_shot_analysis_session(self, activity_id: str) -> dict:
        """
        Returns a full shot analysis session with per-stroke data.

        Shot analysis sessions are created on Trackman Pro/Studio units and include
        both a raw measurement and a normalized measurement (corrected to standard
        conditions) per stroke.

        Top-level fields: id, kind, time, strokeCount, strokes.

        Per-stroke fields: ball, club, time, tags (origin, group, value),
            normalizedMeasurement, measurement.

        Per-stroke measurement fields (same structure for both normalizedMeasurement
        and measurement): id, kind, time, teePosition, attackAngle, faceToPath,
            clubPath, clubSpeed, ballSpeed, spinAxis, spinRate, smashFactor, carry,
            carrySide, total, totalSide, side, curve, landingAngle, launchAngle,
            launchDirection, maxHeight, smashIndex, spinIndex, ballSpeedDifference,
            spinRateDifference, ballTrajectory (kind, timeInterval,
            measuredTimeInterval, validTimeInterval, xFit, yFit, zFit, spinRateFit).

        Args:
            activity_id: The GraphQL node ID of the ShotAnalysisSessionActivity.
                         Looks like "U2hvdEFuYWx5c2lzU2Vzc2lvbkFjdGl2aXR5Cm..."
        """
        data = self._graphql(
            queries.REPORT_SHOT_ANALYSIS,
            variables={"nodeId": activity_id},
            operation_name="ReportShotAnalysis",
        )
        return data["node"]

    # ------------------------------------------------------------------
    # Stats & handicap
    # ------------------------------------------------------------------

    def get_handicap(self) -> dict:
        """
        Returns your current handicap record from the REST API.

        Includes: hcpOld, hcpNew, adjustedGrossScore, scoreDifferential,
        courseHcp, avgBasedOn (list of rounds used in calculation).
        """
        return self._rest_get("/api/hcp/record")

    def get_scorecard_stats(self, take: int = 20) -> list[dict]:
        """
        Returns per-round stats for your last N completed 18-hole rounds.

        Each item includes:
            id, createdAt, numberOfHolesPlayed,
            stat.driveAverage, stat.driveMax, stat.driveCount,
            stat.fairwayHitFairway, stat.fairwayHitLeft, stat.fairwayHitRight,
            stat.greenInRegulation, stat.scrambles, stat.averagePuttsPerHoleDecimal
        """
        data = self._graphql(queries.PROFILE_STATS_SCORECARDS, operation_name="ProfileStatsScorecards")
        return data["me"]["stat"]

    def get_profile_stats(self) -> dict:
        """
        Returns aggregate stats across last 20 rounds:
        gross scores, handicap history, par-3/4/5 breakdown.
        """
        data = self._graphql(queries.PROFILE_STATS, operation_name="ProfileStats")
        return data["me"]

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------

    def get_bag(self, include_retired: bool = False) -> list[dict]:
        """
        Returns your club bag with find-my-distance stats per club.

        Each club includes:
            displayName, clubHead.clubHeadType (DRIVER, IRON, WEDGE, etc.),
            findMyDistance.numberOfShots, findMyDistance.clubStats.carry,
            findMyDistance.shots (individual ball-speed/launch shots)

        Args:
            include_retired: Include retired clubs.
        """
        data = self._graphql(
            queries.MY_BAG,
            variables={"includeRetired": include_retired},
            operation_name="MyBag",
        )
        return data["me"]["equipment"]["clubs"]

    # ------------------------------------------------------------------
    # Convenience / export helpers
    # ------------------------------------------------------------------

    def export_rounds_to_dicts(self, take: int = 20) -> list[dict]:
        """
        Returns a flat list of round summary dicts ready for a DataFrame.

        Each dict: date, course, gross, toPar, driveAvg, driveMax,
                   firPct, gir, scrambles
        """
        activities = self.get_activities(
            take=take, kinds=["COURSE_PLAY"]
        )
        stats_by_id = {s["id"]: s["stat"] for s in self.get_scorecard_stats(take=take)}

        rows = []
        for a in activities:
            sc_id = a.get("scorecard", {}).get("id", "")
            stat = stats_by_id.get(sc_id, {})
            fir_total = (
                (stat.get("fairwayHitFairway") or 0)
                + (stat.get("fairwayHitLeft") or 0)
                + (stat.get("fairwayHitRight") or 0)
            )
            fir_pct = (
                round(100 * stat["fairwayHitFairway"] / fir_total, 1)
                if fir_total and stat.get("fairwayHitFairway") is not None
                else None
            )
            rows.append({
                "date": a.get("time", "")[:10],
                "course": a.get("course", {}).get("displayName", ""),
                "gross": a.get("grossScore"),
                "to_par": a.get("toPar"),
                "drive_avg_yards": round(stat["driveAverage"], 1) if stat.get("driveAverage") else None,
                "drive_max_yards": round(stat["driveMax"], 1) if stat.get("driveMax") else None,
                "drive_count": stat.get("driveCount"),
                "fir_hit": stat.get("fairwayHitFairway"),
                "fir_left": stat.get("fairwayHitLeft"),
                "fir_right": stat.get("fairwayHitRight"),
                "fir_pct": fir_pct,
                "gir": stat.get("greenInRegulation"),
                "scrambles": stat.get("scrambles"),
                "putts_per_hole": stat.get("averagePuttsPerHoleDecimal"),
                "activity_id": a.get("id"),
                "scorecard_id": sc_id,
            })
        return rows

    def export_practice_to_dicts(self, activity_id: str) -> list[dict]:
        """
        Returns a flat list of shot dicts from a practice session.

        Each dict: shot_number, club, target_yards, carry, total,
                   club_speed, ball_speed, smash_factor, spin_rate,
                   launch_angle, face_angle, club_path, attack_angle, face_to_path
        """
        session = self.get_practice_session(activity_id)
        rows = []
        for i, stroke in enumerate(session.get("strokes", []), 1):
            m = stroke.get("measurement") or {}
            rows.append({
                "shot_number": i,
                "club": stroke.get("club"),
                "target_yards": stroke.get("targetDistance"),
                "carry_yards": m.get("carryActual"),
                "total_yards": m.get("totalActual"),
                "club_speed_mph": m.get("clubSpeed"),
                "ball_speed_mph": m.get("ballSpeed"),
                "smash_factor": m.get("smashFactor"),
                "spin_rate_rpm": m.get("spinRate"),
                "launch_angle_deg": m.get("launchAngle"),
                "face_angle_deg": m.get("faceAngle"),
                "club_path_deg": m.get("clubPath"),
                "attack_angle_deg": m.get("attackAngle"),
                "face_to_path_deg": m.get("faceToPath"),
                "carry_side_yards": m.get("carrySideActual"),
                "max_height_yards": m.get("maxHeight"),
                "dynamic_loft_deg": m.get("dynamicLoft"),
            })
        return rows
