import os 
import uuid
from polyfile.magic import MagicMatcher
import random
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

from .database import addWorkoutToAthlete, deleteWorkout, getCredentialsbyId, addCredentials, addAthlete, getAllAthletes, addUnsplit


def stsock(filename, size):
    _, ext = os.path.splitext(filename)
    if ext in ['.exe', '.bin', '.js', '.sh', '.py', '.php']:
        return False  # reject the upload

    id = uuid.uuid4().hex  # server-side filename
    with open( 'unsplituploads/' + id + ext, 'wb') as f:
        pass
    return 'unsplituploads/' + id + ext  # allow the upload

def st_wr_chunk(filename, offset, data):
    if not os.path.exists(filename):
        return False
    try:
        with open( filename, 'r+b') as f:
            f.seek(offset)
            f.write(data)
    except IOError:
        return False
    return True

def mimewrap(serverfilename):
    for match in MagicMatcher.DEFAULT_INSTANCE.match(serverfilename):
        print(f"Match string: {match!s}")
        if str(match).startswith("Microsoft Excel 2007"):
            return True
    return False

def st_valid_athletes(addedId, teamId, athleteMap):
    athDict = {}
    for pieceIdx in range(len(athleteMap)):
        for paidx, piece_athlete in enumerate(athleteMap[pieceIdx]):
            in_dict = athDict.get(piece_athlete,None)
            if in_dict is not None:
                pl, side = in_dict
                pl.append(pieceIdx)
                athDict[piece_athlete] = (pl,side)
            else:
                side = 'port' if paidx%2 != 0 else 'starboard'
                athDict[piece_athlete] = ([pieceIdx], side)
                
    if len(athDict) :
        for athlete, athleteTuple in athDict.items():
            print(athlete)
            athlete_piece_list, side = athleteTuple
            if len(athlete.split())==1:
                first, last = athlete[0], athlete[0]
            else:
                first, last = athlete.split() 
            # print()

            allAthletes = getAllAthletes(teamId)

            athlete_query = None
            for existingAthlete in allAthletes:
                if fuzz.token_sort_ratio(existingAthlete['namestring'], athlete) >= 85:
                    athlete_query = existingAthlete
                    break

            if athlete_query:
                athleteId = athlete_query['_id']
                print(f'attributed to {athlete}', end='\r')
                edited = addWorkoutToAthlete(athleteId, addedId, athlete_piece_list)
            else: # we need to create a new athlete account for this individual

                error = ''
                newId = random.randint(10, 100000)
                already_id = getCredentialsbyId(newId)
                while already_id:
                    newId = random.randint(10, 100000)
                    already_id = getCredentialsbyId(newId)
     
                # add temporary login credentials to credentials DB
                add = addCredentials(newId, athlete, "pwhash", "salt")
                if not add:
                    error += 'failed to add user cred'

                # create athlete document from entered info
                permissions = []

                athleteJson = {
                    "_id" : newId,
                    "first" : first,
                    "last" : last,
                    "namestring": athlete,
                    "permissions" : permissions,
                    "workouts" : [addedId],
                    "piecelist": {str(addedId): athlete_piece_list},
                    "side" : side,
                    "active" : True,
                    "teamId" : teamId
                }
                print(athleteJson)
                # add athlete document to athlete db
                add = addAthlete(athleteJson)
                if not add:
                    error += "failed to add athlete"
                
                if len(error):
                    False

                print(f'attributed to {athlete}', end='\r')
        return True
    else:
        deleteWorkout(addedId)
        return False