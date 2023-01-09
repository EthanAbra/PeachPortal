from project import create_app, socketio

from project.database import queryAthlete, addWorkout, deleteWorkout, queryAthleteByName, addWorkoutToAthlete
from project.database import getCredentialsbyId, addCredentials, addAthlete, getAllAthletes, addUnsplit
from flask import Flask, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from flask_login import LoginManager, current_user
import uuid
from polyfile.magic import MagicMatcher
# from project import database as db
import random
import bcrypt
from project import peachhelp
from project.xlsxMethods import xlsxRead, xlsxReadUnsplit
import os
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

#-----------------------------------------------------------------------
""" File upload method"""
#-----------------------------------------------------------------------


@socketio.on('start-transfer')
def start_transfer(filename, size):
    print("receivd start transfer")
    """Process an upload request from the client."""
    _, ext = os.path.splitext(filename)
    if ext in ['.exe', '.bin', '.js', '.sh', '.py', '.php']:
        return False  # reject the upload

    id = uuid.uuid4().hex  # server-side filename
    with open( id + ext, 'wb') as f:
        pass
    return id + ext  # allow the upload

@socketio.on('write-chunk')
def write_chunk(filename, offset, data):
    """Write a chunk of data sent by the client."""
    if not os.path.exists(filename):
        return False
    try:
        with open( filename, 'r+b') as f:
            f.seek(offset)
            f.write(data)
    except IOError:
        return False
    return True


@socketio.on('write-complete')
def write_complete(data):
    print("wrcomp")

    user = current_user
    # print(user)
    athleteId = user._id
    athlete = queryAthlete(athleteId)
    teamId = athlete['teamId']

    def mimewrap(serverfilename):
        for match in MagicMatcher.DEFAULT_INSTANCE.match(serverfilename):
            print(f"Match string: {match!s}")
            if str(match).startswith("Microsoft Excel 2007"):
                return True

    
    if not mimewrap(data['serverfilename']):
        os.remove(data['serverfilename'])
        return False, data['serverfilename']

    success, workout = xlsxRead(data['serverfilename'], teamId)
    os.remove(data['serverfilename'])

    if not success:
        return False, data['serverfilename']

    addedId = addWorkout(workout, teamId)
    if not addedId:
        return False, data['serverfilename']
    else:
        print(f'Sheet uploaded by {athlete["first"]} {athlete["last"]}. WorkoutId: {addedId}')
    socketio.emit('peach processed',{'ack':True, 'serverfilename': data['serverfilename'], 'clientfilename': data['clientfilename'], 'addedId': addedId, 'teamId' :teamId, 'athleteList':workout['athlete_list']})


    

@socketio.on('valid-athletes')
def valid_athletes(addedId, teamId, athleteMap):
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
    
@socketio.on('write-complete-unsplit')
def write_complete(data):
    print("wrcompunsplit")
    user = current_user
    # print(user)
    athleteId = user._id
    athlete = queryAthlete(athleteId)
    teamId = athlete['teamId']

    def mimewrap(serverfilename):
        for match in MagicMatcher.DEFAULT_INSTANCE.match(serverfilename):
            print(f"Match string: {match!s}")
            if str(match).startswith("Microsoft Excel 2007"):
                return True

    
    if not mimewrap(data['serverfilename']):
        os.remove(data['serverfilename'])
        return False, data['serverfilename']

    success, workout = xlsxReadUnsplit(data['serverfilename'], teamId)

    if not success:
        os.remove(data['serverfilename'])
        return False, data['serverfilename']

    addedId = addUnsplit(workout, teamId, data['serverfilename'])
    if not addedId:
        os.remove(data['serverfilename'])
        return False, data['serverfilename']
    else:
        print(f'Sheet uploaded by {athlete["first"]} {athlete["last"]}. WorkoutId: {addedId}')
    socketio.emit('unsplit processed',{'ack':True, 'serverfilename': data['serverfilename'], 'clientfilename': data['clientfilename'], 'addedId': addedId, 'teamId' :teamId, 'athleteList':workout['athlete_list']})


app = create_app(debug=True)



if __name__ == "main":
    socketio.run(app = app)