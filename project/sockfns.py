import os 
import uuid
from polyfile.magic import MagicMatcher
from flask import current_app
import random
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from concurrent.futures import ThreadPoolExecutor
from .database import addWorkoutToAthlete, deleteWorkout, getCredentialsbyId, addCredentials, addAthlete, getAllAthletes, addUnsplit
from dotenv import load_dotenv
import pymongo


load_dotenv()
if 'database_url' not in os.environ:
    CONNECTION_STRING = os.environ.get('database_url')
else:
    CONNECTION_STRING = os.environ['database_url']
sockdb = pymongo.MongoClient(CONNECTION_STRING).peach

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

def st_valid_athletes(addedId, teamId, athleteMap, bokehdb = None):
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
            with ThreadPoolExecutor() as executor:
                athlete_futures = [executor.submit(process_athlete,addedId, teamId, bokehdb, athlete, athleteTuple) for athlete, athleteTuple in athDict.items()]
            [future.result() for future in athlete_futures]
            return True
        else:
            if bokehdb is not None:
                deleteWorkout(addedId, bokehdb)
            else:
                deleteWorkout(addedId, sockdb)
            return False

def process_athlete(addedId, teamId, bokehdb, athlete, athleteTuple):
        athlete_piece_list, side = athleteTuple
        if len(athlete.split())==1:
            first, last = athlete[0], athlete[0]
        else:
            first, last = athlete.split() 
            # print()
        if bokehdb is not None:
            allAthletes = getAllAthletes(teamId, 'name', False, bokehdb)
        else:
            allAthletes = getAllAthletes(teamId, 'name', False, sockdb)

        if allAthletes is None:
            allAthletes = []

        athlete_query = None
        for existingAthlete in allAthletes:
            if fuzz.token_sort_ratio(existingAthlete['namestring'], athlete) >= 85:
                athlete_query = existingAthlete
                break

        if athlete_query:
            athleteId = athlete_query['_id']
            print(f'attributed to {athlete}', end='\r')
            if bokehdb is not None:
                edited = addWorkoutToAthlete(athleteId, addedId, athlete_piece_list, bokehdb)
            else:
                edited = addWorkoutToAthlete(athleteId, addedId, athlete_piece_list, sockdb)
        else: # we need to create a new athlete account for this individual
            error = ''
            newId = random.randint(10, 100000)
            if bokehdb is not None:
                already_id = getCredentialsbyId(newId, bokehdb)
            else:
                already_id = getCredentialsbyId(newId, sockdb)
            while already_id:
                newId = random.randint(10, 100000)
                if bokehdb is not None:
                    already_id = getCredentialsbyId(newId, bokehdb)
                else:
                    already_id = getCredentialsbyId(newId, sockdb)
     
                # add temporary login credentials to credentials DB
            if bokehdb is not None:
                add = addCredentials(newId, athlete, "pwhash", "salt", bokehdb)
            else:
                add = addCredentials(newId, athlete, "pwhash", "salt", sockdb)
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
                    "renders":['slip', 'wash', 'power', 'percentage'],
                    "workouts" : [addedId],
                    "piecelist": {str(addedId): athlete_piece_list},
                    "class": 1000,
                    "side" : side,
                    "active" : True,
                    "teamId" : int(teamId)
                }
                # add athlete document to athlete db
            if bokehdb is not None:
                add = addAthlete(athleteJson, bokehdb)
            else:
                add = addAthlete(athleteJson, sockdb)
            if not add:
                error += "failed to add athlete"
                
            if len(error):
                False

            print(f'attributed to {athlete}', end='\r')