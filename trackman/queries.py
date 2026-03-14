"""
GraphQL query strings extracted from Proxyman traffic capture.
Each query mirrors exactly what the Trackman iOS app sends.
"""

PROFILE_SHORT = """
query ProfileShort {
  me {
    __typename
    profile {
      __typename
      id
      dbId
      fullName
      playerName
      email
      emailConfirmed
      gender
      category
      outdoorHandicap
      picture
      playerData {
        __typename
        hcp {
          __typename
          currentHcp
        }
      }
    }
  }
}
"""

ACTIVITY_LIST = """
query ActivityList($take: Int, $skip: Int, $activityKinds: [ActivityKind!], $includeHidden: Boolean) {
  me {
    __typename
    activities(take: $take, skip: $skip, kinds: $activityKinds, includeHidden: $includeHidden) {
      __typename
      items {
        __typename
        kind
        ... on CoursePlayActivity {
          id
          time
          state
          toPar
          grossScore
          stablefordPoints
          course {
            __typename
            displayName
            id
            image { __typename url }
          }
          scorecard {
            __typename
            id
            kind
          }
          gameSettings {
            __typename
            gamePlay
            gameScore
          }
          isInTournament
          tournament { __typename ... on BullsEyeTournament { id } }
        }
        ... on VirtualRangeSessionActivity {
          id
          time
          strokeCount
        }
      }
      totalCount
      pageInfo {
        hasNextPage
      }
    }
  }
}
"""

REPORT_COURSE = """
query ReportCourse($nodeId: ID!) {
  node(id: $nodeId) {
    __typename
    ... on CoursePlayActivity {
      id
      kind
      state
      toPar
      netToPar
      grossScore
      gameType
      time
      course {
        __typename
        displayName
        courseIdentifier
        image { __typename url }
        holes {
          __typename
          tee {
            __typename
            position {
              __typename
              imageTransformation {
                __typename
                x
                y
              }
            }
          }
        }
      }
      scorecard {
        __typename
        id
        kind
        holes {
          __typename
          id
          holeNumber
          par
          shots {
            __typename
            id
            shotNumber
            clubType
            lie
            result
          }
          score
          netScore
          putts
          fairwayHit
          greenInRegulation
        }
        stats {
          __typename
          driveTotal
          driveCount
          driveAverage
          driveMax
          fairwayHitFairway
          fairwayHitLeft
          fairwayHitRight
          greenInRegulation
          scrambles
          averagePuttsPerHoleDecimal
        }
      }
    }
  }
}
"""

COURSE_REPORT_MEASUREMENT = """
query CourseReportMeasurementIndoor($shotId: ID!, $shotMeasurementKind: ShotMeasurementKind) {
  node(id: $shotId) {
    __typename
    ... on ScorecardShot {
      id
      measurement(kind: $shotMeasurementKind) {
        __typename
        attackAngle
        backswingTime
        ballSpeed
        carry
        carrySide
        clubPath
        clubSpeed
        curve
        dynamicLoft
        faceAngle
        faceToPath
        hangTime
        landingAngle
        landingAngleActual
        launchAngle
        launchDirection
        maxHeight
        smashFactor
        spinAxis
        spinAxisActual
        spinLoft
        spinRate
        swingDirection
        swingPlane
        swingRadius
        totalSide
        lowPointDistance
        lowPointHeight
        lowPointSide
        dPlaneTilt
        dynamicLie
        impactHeight
        impactOffset
      }
    }
  }
}
"""

REPORT_VIRTUAL_RANGE = """
query ReportVirtualRange($nodeId: ID!) {
  node(id: $nodeId) {
    __typename
    ... on VirtualRangeSessionActivity {
      id
      time
      kind
      strokeCount
      strokes {
        __typename
        club
        targetDistance
        target {
          __typename
          type
          distance
          ... on StrokeCircleTarget {
            radius
            hcp
            tourRadius
          }
        }
        measurement {
          __typename
          id
          time
          kind
          carryActual
          totalActual
          clubSpeed
          ballSpeed
          smashFactor
          spinRate
          spinAxis
          curve
          attackAngle
          faceToPath
          clubPath
          faceAngle
          launchAngle
          launchDirection
          maxHeight
          carrySideActual
          totalSideActual
          dynamicLoft
          dynamicLie
          impactHeight
          spinLoft
          swingPlane
          swingDirection
          impactOffset
          landingAngle
        }
      }
    }
  }
}
"""

PROFILE_STATS_SCORECARDS = """
query ProfileStatsScorecards {
  me {
    __typename
    stat: scorecards(take: 20, completed: true, numberOfHolesToPlay: 18) {
      __typename
      id
      createdAt
      numberOfHolesPlayed
      stat {
        __typename
        driveTotal
        driveCount
        driveAverage
        driveMax
        fairwayHitFairway
        fairwayHitLeft
        fairwayHitRight
        greenInRegulation
        scrambles
        averagePuttsPerHoleDecimal
      }
    }
  }
}
"""

HCP_RECORD = None  # REST endpoint: GET /api/hcp/record

MY_BAG = """
query MyBag($includeRetired: Boolean, $weatherConditionsInput: WeatherConditionsInputType) {
  me {
    __typename
    equipment {
      __typename
      clubs(includeRetired: $includeRetired) {
        __typename
        dbId
        id
        displayName
        isRetired
        brand {
          __typename
          id
          name
        }
        clubHead {
          __typename
          clubHeadType
          clubHeadKind
        }
        findMyDistance(weatherConditions: $weatherConditionsInput) {
          __typename
          numberOfShots
          clubStats {
            __typename
            carry
            standardDeviationCarry
            standardDeviationTotal
            total
          }
          shots {
            __typename
            id
            time
            carryActual
            totalActual
            ballSpeed
            clubSpeed
            smashFactor
            spinRate
            launchAngle
          }
        }
      }
    }
  }
}
"""

PROFILE_STATS = """
query ProfileStats {
  me {
    __typename
    scorecards(take: 20, completed: true, numberOfHolesToPlay: 18) {
      __typename
      grossScore
      id
    }
    hcp {
      __typename
      playerHistory(take: 20) {
        __typename
        items {
          __typename
          adjustedGrossScore
          id
        }
      }
    }
    stat: scorecards(take: 20, completed: true, numberOfHolesToPlay: 18) {
      __typename
      par3GrossScore: grossScore(holeTypes: PAR3_HOLES)
      par3Count: numberOfHolesPlayed(holeTypes: PAR3_HOLES)
      par4GrossScore: grossScore(holeTypes: PAR4_HOLES)
      par4Count: numberOfHolesPlayed(holeTypes: PAR4_HOLES)
      par5GrossScore: grossScore(holeTypes: PAR5_HOLES)
      par5Count: numberOfHolesPlayed(holeTypes: PAR5_HOLES)
    }
  }
}
"""
