from flask_pymongo import PyMongo
import pickle
import random
import certifi
import collections
from flask import current_app, g
from werkzeug.local import LocalProxy
import pymongo
ca = certifi.where()
from . import peach
from .peach import PeachData
# print(os.environ)
# print(CONNECTION_STRING)


def get_db():
    """
    Configuration method to return db instance
    """
    db = getattr(g, "_database", None)

    if db is None:

        db = g._database = PyMongo(current_app).db
       
    return db

flaskdb = LocalProxy(get_db)


# ------------------------------------------------------------------- #
# general athlete collection methods 

def addAthlete(athleteDict, db = flaskdb):
    print(f'addAthlete called with {athleteDict}')
    try:
        result = db.athletes.insert_one(athleteDict)
        return result.inserted_id
    except Exception as e:
        print(str(e))
        return None

def editAthlete(athleteId, field, newVal, db = flaskdb):
    print(f'editAthlete called with {athleteId}, {field}, {newVal}')
    try:
        result = db.athletes.update_one({'_id' : athleteId}, {'$set' : {field : newVal}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None

def queryAthlete(athleteId, db = flaskdb):
    print(f'queryAthlete called with {athleteId}')
    try:
        athleteId = int(athleteId)
        return db.athletes.find_one({'_id' : athleteId})
    except Exception as e:
        print(str(e))
        return None

def queryAthleteByName(first, last, team, db = flaskdb):
    print(f'queryAthleteByName called with {first} {last} {team}')
    try:
        return db.athletes.find_one({'first' : first, 'last' : last, 'teamId': team})
    except Exception as e:
        print(str(e))
        return None

def getAllAthletes(teamId, sort_by='name', active_only=False, db = flaskdb):
    print(f'getAllAthletes called with teamId: {teamId}')
    try:
        if active_only:
            return db.athletes.find({'active': True, 'teamId' : teamId}, sort=[(sort_by, pymongo.ASCENDING)])
        else:
            return db.athletes.find({'teamId' : teamId}, sort=[(sort_by, pymongo.ASCENDING)])
    except Exception as e:
        print(str(e))
        return None

def addWorkoutToAthlete(athleteId, workoutId, piece_list, db = flaskdb):
    print(f"addWorkouttoAthlete called for {athleteId}")
    try:
        result = db.athletes.update_one({'_id' : int(athleteId)}, {'$push' : {"workouts" : workoutId}, '$set': {"piecelist." + str(workoutId): piece_list}})
        return result
    except Exception as e:
        print(str(e))
        return None

def removeWorkoutFromAthlete(athleteId, workoutId, db = flaskdb):
    try:
        result = db.athletes.update_one({'_id' : athleteId}, {'$unset' : {f'workouts.{workoutId}' : ''}})
        return result
    except Exception as e:
        print(str(e))
        return None
# ------------------------------------------------------------------- #
# general workout collection methods 

def addWorkout(workoutDict, teamId, db = flaskdb):
    title = workoutDict['title']
    print(f'addworkout called with {title}, {teamId}')
    dataDict = collections.defaultdict()
    try:
        workoutDict['teamId'] = teamId
        dataDict['peach_data'] = workoutDict.pop('peach_data')
        dataDict['teamId'] = teamId
        result = db.workoutsmeta.insert_one(workoutDict)
        dataDict['_id'] = result.inserted_id
        result = db.workoutsdata.insert_one(dataDict)
        return result.inserted_id
    except Exception as e:
        print(str(e))
        return None
    
def addUnsplit(workoutDict, teamId, serverfilename, db = flaskdb):
    print(f'addunsplit called with {teamId}')
    dataDict = collections.defaultdict()
    try:
        workoutDict['teamId'] = teamId
        workoutDict['serverfilename'] = serverfilename
        dataDict['peach_data'] = workoutDict.pop('peach_data')
        dataDict['teamId'] = teamId
        result = db.unsplitsmeta.insert_one(workoutDict)
        dataDict['_id'] = result.inserted_id
        result = db.unsplitsdata.insert_one(dataDict)
        return result.inserted_id
    except Exception as e:
        print(str(e))
        return None


def editWorkout(workoutId, field, newVal, db = flaskdb):
    print(f'editWorkout called with {workoutId}, {field}, {newVal}')
    try:
        result = db.workoutsmeta.update_one({'_id' : workoutId}, {'$set' : {field : newVal}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None

def queryWorkoutMeta(workoutId, db = flaskdb):
    print(f'queryWorkoutMeta called with {workoutId}')
    try:
        workoutId = int(workoutId)
        res = db.workoutsmeta.find_one({'_id' : workoutId})
        return res
    except Exception as e:
        print(str(e))
        return None

def queryWorkoutData(workoutId, db = flaskdb):
    print(f'queryWorkoutData called with {workoutId}')
    try:
        workoutId = int(workoutId)
        res = db.workoutsdata.find_one({'_id' : workoutId})
        temp = pickle.loads(res['peach_data'])
        res['peach_data'] = temp
        return res
    except Exception as e:
        print(str(e))
        return None
    
def queryUnsplitMeta(workoutId, db = flaskdb):
    print(f'queryUnsplittMeta called with {workoutId}')
    try:
        workoutId = int(workoutId)
        res = db.unsplitsmeta.find_one({'_id' : workoutId})
        return res
    except Exception as e:
        print(str(e))
        return None

def queryUnsplitData(workoutId, db = flaskdb):
    print(f'queryUnsplitData called with {workoutId}')
    try:
        workoutId = int(workoutId)
        res = db.unsplitsdata.find_one({'_id' : workoutId})
        temp = pickle.loads(res['peach_data'])
        res['peach_data'] = temp
        return res
    except Exception as e:
        print(str(e))
        return None

def deleteWorkout(workoutId, db = flaskdb):
    print(f'deleteWorkout called with {workoutId}')
    try:
        result = db.workoutsmeta.delete_one({'_id' : workoutId})
        result = db.workoutsdata.delete_one({'_id' : workoutId})
        return result.deleted_count
    except Exception as e:
        print(str(e))
        return None
    
def deleteUnsplit(workoutId, db = flaskdb):
    print(f'deleteUnsplit called with {workoutId}')
    try:
        result = db.unsplitsmeta.delete_one({'_id' : workoutId})
        result = db.unsplitsdata.delete_one({'_id' : workoutId})
        return result.deleted_count
    except Exception as e:
        print(str(e))
        return None


def getAllWorkouts(teamId, sort_by='date', db = flaskdb):
    print(f'getAllWorkouts called with {teamId}')
    try:
        return db.workoutsmeta.find({'teamId' : teamId}, sort=[(sort_by, pymongo.DESCENDING)])
    except Exception as e:
        print(str(e))
        return None
    
def getAllUnsplits(teamId, sort_by='date', db = flaskdb):
    print(f'getAllUnsplits called with {teamId}')
    try:
        return db.unsplitsmeta.find({'teamId' : teamId}, sort=[(sort_by, pymongo.DESCENDING)])
    except Exception as e:
        print(str(e))
        return None


# ------------------------------------------------------------------ # 
# general team db methods
def queryTeam(teamId, db = flaskdb):
    print(f'queryTeam called with {teamId}')
    try:
        teamId = int(teamId)
        res = db.teams.find_one({'_id' : teamId})
        return res
    except Exception as e:
        print(str(e))
        return None

def addTeam(name, db = flaskdb):
    print(f'addTeam called with {name}')
    try:
        teamId = random.randint(10, 999999)
        # ensure no id collision
        while queryTeam(teamId):
            teamId = random.randint(10, 999999) 

        res = db.teams.insert_one({'_id' : teamId, 'name' : name})
        return res.inserted_id
    except Exception as e:
        print(str(e))
        return None

# ------------------------------------------------------------------- #
# takes a workout ID, gets all participating athletes, and adds that 
# workout to each athlete's 'workouts' array
def attributeWorkout(workoutId, db = flaskdb):
    try:
        workout = db.workoutsmeta.find_one({'_id' : workoutId})
        # athletes who completeted the workout
        participating = [int(k) for k in workout['scores'].keys()]
        result = db.athletes.update_many({'_id' : {'$in' : participating}}, {'$addToSet' : {'workouts' : workoutId}})
        return result.modified_count

    except Exception as e:
        print(str(e))
        return None



# ------------------------------------------------------------------- #
# add an athlete to the credentials database
def addCredentials(athleteId, email, pwHash, salt, db = flaskdb):
    print(f'addCredentials called with {athleteId}, {email}')
    try:
        newCreds = {
            "_id" : athleteId,
            "email" : email,
            "pwHash" : pwHash,
            "salt" : salt
            }
        result = db.credentials.insert_one(newCreds)
        return result.inserted_id
    except Exception as e:
        print(str(e))
        return None

# add an athlete to the credentials database
def addCredentialsJson(json, db = flaskdb):
    db.credentials.insert_one(json)


def getCredentials(email, db = flaskdb):
    print(f'getCredentialsbyemail called with {email}')
    # print(db)
    try:
        result = db.credentials.find_one({'email' : email})
        return result
    
    except Exception as e:
        print(str(e))
        return None


def getCredentialsbyId(id, db = flaskdb):
    print(f'getCredentialsbyId called with {id}')
    # print(type(id))
    try:
        result = db.credentials.find_one({'_id' : id})
        return result
    except Exception as e:
        print(str(e))
        return None


def editCredentials(athleteId, field, value, db = flaskdb):
    print(f'editCredentials called with {athleteId}')
    try:
        result = db.credentials.update_one( {'_id' : athleteId}, {'$set' : {field : value}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None

def editCredentialsBatch(athleteId, field1, value1, field2, value2, field3, value3, db = flaskdb):
    print(f'editCredentialsBatch called with {athleteId}')
    try:
        result = db.credentials.update_one({'_id' : athleteId}, {'$set' : {field1 : value1, field2 : value2, field3 : value3}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None

def editCredentialsPassword(athleteId, field1, value1, field2, value2, db = flaskdb):
    print(f'editCredentialsPassword called with {athleteId}')
    try:
        result = db.credentials.update_one({'_id' : athleteId}, {'$set' : {field1 : value1, field2 : value2}})
        print(result.modified_count)
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None



# ------------------------------------------------------------------- #
# Test code

if __name__ == "__main__":
    print(getAllAthletes(346502))