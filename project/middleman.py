from .database import queryTeam, queryWorkoutMeta, queryAthleteByName, queryAthlete
from . import cache


@cache.memoize(1000)
def getTeamInfo(teamId):
    return queryTeam(teamId)

@cache.memoize(1000)
def getWorkoutMeta(workoutId):
    return queryWorkoutMeta(workoutId)

@cache.memoize(1000)
def getAthleteByName(namestring, teamId):
    return queryAthleteByName(namestring, teamId)

@cache.memoize(1000)
def getAthleteById(_id):
    return queryAthlete(_id)