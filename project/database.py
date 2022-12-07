from flask_pymongo import PyMongo
import datetime
from pprint import pprint
import os 
import bcrypt
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

db = LocalProxy(get_db)


# ------------------------------------------------------------------- #
# general athlete collection methods 

def addAthlete(athleteDict):
    print(f'addAthlete called with {athleteDict}')
    try:
        result = db.athletes.insert_one(athleteDict)
        return result.inserted_id
    except Exception as e:
        print(str(e))
        return None

def editAthlete(athleteId, field, newVal):
    print(f'editAthlete called with {athleteId}, {field}, {newVal}')
    try:
        result = db.athletes.update_one({'_id' : athleteId}, {'$set' : {field : newVal}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None

def queryAthlete(athleteId):
    print(f'queryAthlete called with {athleteId}')
    try:
        athleteId = int(athleteId)
        return db.athletes.find_one({'_id' : athleteId})
    except Exception as e:
        print(str(e))
        return None

def queryAthleteByName(first, last, team):
    print(f'queryAthleteByName called with {first} {last} {team}')
    try:
        return db.athletes.find_one({'first' : first, 'last' : last, 'teamId': team})
    except Exception as e:
        print(str(e))
        return None

def getAllAthletes(teamId, sort_by='name', active_only=False):
    try:
        if active_only:
            return db.athletes.find({'active': True, 'teamId' : teamId}, sort=[(sort_by, pymongo.ASCENDING)])
        else:
            return db.athletes.find({'teamId' : teamId}, sort=[(sort_by, pymongo.ASCENDING)])
    except Exception as e:
        print(str(e))
        return None

def addWorkoutToAthlete(athleteId, workoutId):
    try:
        result = db.athletes.update_one({'_id' : int(athleteId)}, {'$push' : {"workouts" : workoutId}})
        return result
    except Exception as e:
        print(str(e))
        return None

def removeWorkoutFromAthlete(athleteId, workoutId):
    try:
        result = db.athletes.update_one({'_id' : athleteId}, {'$unset' : {f'workouts.{workoutId}' : ''}})
        return result
    except Exception as e:
        print(str(e))
        return None
# ------------------------------------------------------------------- #
# general workout collection methods 

def addWorkout(workoutDict, teamId):
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

def editWorkout(workoutId, field, newVal):
    print(f'editWorkout called with {workoutId}, {field}, {newVal}')
    try:
        result = db.workoutsmeta.update_one({'_id' : workoutId}, {'$set' : {field : newVal}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None

def queryWorkoutMeta(workoutId):
    print(f'queryWorkoutMeta called with {workoutId}')
    try:
        workoutId = int(workoutId)
        res = db.workoutsmeta.find_one({'_id' : workoutId})
        return res
    except Exception as e:
        print(str(e))
        return None

def queryWorkoutData(workoutId):
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

def deleteWorkout(workoutId):
    print(f'deleteWorkout called with {workoutId}')
    try:
        result = db.workoutsmeta.delete_one({'_id' : workoutId})
        result = db.workoutsdata.delete_one({'_id' : workoutId})
        return result.deleted_count
    except Exception as e:
        print(str(e))
        return None

def getAllWorkouts(teamId, sort_by='date'):
    print(f'getAllWorkouts called with {teamId}')
    try:
        return db.workoutsmeta.find({'teamId' : teamId}, sort=[(sort_by, pymongo.DESCENDING)])
    except Exception as e:
        print(str(e))
        return None

# ------------------------------------------------------------------ # 
# general team db methods
def queryTeam(teamId):
    print(f'queryTeam called with {teamId}')
    try:
        teamId = int(teamId)
        res = db.teams.find_one({'_id' : teamId})
        return res
    except Exception as e:
        print(str(e))
        return None

def addTeam(name):
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
def attributeWorkout(workoutId):
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
def addCredentials(athleteId, email, pwHash, salt):
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
def addCredentialsJson(json):
    db.credentials.insert_one(json)


def getCredentials(email):
    print(f'getCredentialsbyemail called with {email}')
    # print(db)
    try:
        result = db.credentials.find_one({'email' : email})
        return result
    
    except Exception as e:
        print(str(e))
        return None


def getCredentialsbyId(id):
    print(f'getCredentialsbyId called with {id}')
    # print(type(id))
    try:
        result = db.credentials.find_one({'_id' : id})
        return result
    except Exception as e:
        print(str(e))
        return None


def editCredentials(athleteId, field, value):
    print(f'editCredentials called with {athleteId}')
    try:
        result = db.credentials.update_one( {'_id' : athleteId}, {'$set' : {field : value}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None

def editCredentialsBatch(athleteId, field1, value1, field2, value2, field3, value3):
    print(f'editCredentialsBatch called with {athleteId}')
    try:
        result = db.credentials.update_one({'_id' : athleteId}, {'$set' : {field1 : value1, field2 : value2, field3 : value3}})
        return result.modified_count
    except Exception as e:
        print(str(e))
        return None



# ------------------------------------------------------------------- #
# Test code

if __name__ == "__main__":
    # athlete1 = {
    #     "_id" : 69,
    #     "first" : "Henry",
    #     "last" : "Vecchione",
    #     "permissions" : ["admin"],
    #     "prs" : {
    #         "2000m" : "6:24",
    #         "6000m" : "20:32"
    #     },
    #     "workouts" : [],
    #     "side" : ["port"],
    #     "class" : 2022,
    #     "active" : True,
    #     "awards" : {
    #         "earc" : [],
    #         "ira" : [],
    #         "shirts" : ['g','de','n','da','t','p']
    #     },
    #     "teamId" : 1
    # }
    # athlete2 = {
    #     "_id" : 1,
    #     "first" : "Cal",
    #     "last" : "Gorvy",
    #     "permissions" : [],
    #     "prs" : {
    #         "2000m" : "5:59",
    #         "6000m" : "17:24"
    #     },
    #     "workouts" : [],
    #     "side" : ["starboard"],
    #     "class" : 2025,
    #     "active" : True,
    #     "awards" : {
    #         "earc" : ['4V'],
    #         "ira" : ['1V'],
    #         "shirts" : ['g','de','n','h','y','t','p']
    #     },
    #     "teamId" : 1
    # }
    # athlete3 = {
    #     "_id" : 2,
    #     "first" : "Peter",
    #     "last" : "Skinner",
    #     "permissions" : [],
    #     "prs" : {
    #         "2000m" : "5:59",
    #         "6000m" : "17:24"
    #     },
    #     "workouts" : [],
    #     "side" : ["port"],
    #     "class" : 2023,
    #     "active" : True,
    #     "awards" : {
    #         "earc" : ['4V'],
    #         "ira" : ['1V'],
    #         "shirts" : ['g','de','n','h','y','t','p']
    #     },
    #     "teamId" : 1
    # }
    # athlete4 = {
    #     "_id" : 3,
    #     "first" : "Will",
    #     "last" : "Olson",
    #     "permissions" : [],
    #     "prs" : {
    #         "2000m" : "5:59",
    #         "6000m" : "17:24"
    #     },
    #     "workouts" : [],
    #     "side" : ["port"],
    #     "class" : 2023,
    #     "active" : True,
    #     "awards" : {
    #         "earc" : ['4V'],
    #         "ira" : ['1V'],
    #         "shirts" : ['g','de','n','h','y','t','p']
    #     },
    #     "teamId" : 1
    # }
    # workout1 = {
    #     '_id' : 1,
    #     'title' : '2x4000m, 3000m',
    #     'date' : datetime.datetime(2021, 11, 8),
    #     'pieces' : ['4000m', '4000m', '3000m'],
    #     'scores' : {
    #         '69' : ['15:12', '15:25' , '12:00'],
    #         '1' : ['13:14', '14:20', '13:15']
    #     },
    #     'notes' : 'open rate',
    #     'test' : False
    # }
    # workout2 = {
    #     '_id' : 2,
    #     'title' : '6x2000m',
    #     'date' : datetime.datetime(2021, 10, 31),
    #     'pieces' : ['2000m','2000m','2000m','2000m','2000m','2000m'],
    #     'scores' : {
    #         '69' : ['15:12', '15:25' , '12:00','15:12', '15:25' , '12:00'],
    #         '1' : ['13:14', '14:20', '13:15','13:14', '14:20', '13:15']
    #     },
    #     'notes' : 'wowwwee',
    #     'test' : False
    # }

    # pwPlain = b"sugmaLigma"
    # salt = bcrypt.gensalt()
    # hashed = bcrypt.hashpw(pwPlain, salt)
    # addCredentials(69,"hjv@princeton.edu", hashed, salt)

    # pwPlain = b'admin'
    # salt = bcrypt.gensalt()
    # hashed = bcrypt.hashpw(pwPlain, salt)
    # addCredentials(420, 'a@x.com', hashed, salt)

    pass