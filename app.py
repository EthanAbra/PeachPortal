from project import create_app, socketio


from flask import Flask, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from flask_login import LoginManager, current_user
import uuid
from polyfile.magic import MagicMatcher
from project import database as db
import random
import bcrypt
from project import peachhelp
from project.xlsxMethods import xlsxRead
import os

#-----------------------------------------------------------------------
""" File upload method"""
#-----------------------------------------------------------------------



    
@socketio.on('my-event')
def my_event(msg):
    print("connected!!!!!!!!" + str(msg))
    socketio.emit('connect')


# print('capp called')
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
def write_complete(filename):
    print("revced wr comp")
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = current_user
    # print(user)
    athleteId = user.id
    athlete = db.queryAthlete(athleteId)
    teamId = athlete['teamId']

    def mimewrap(filename):
        for match in MagicMatcher.DEFAULT_INSTANCE.match(filename):
            print(f"Match string: {match!s}")
            if str(match).startswith("Microsoft Excel"):
                return True


    
    if not mimewrap(filename):
        os.remove(filename)
        return False
    # file = open(filename, 'r')
    success, workout = xlsxRead(filename, teamId)

    if not success:
        os.remove(filename)
        return False

    addedId = db.addWorkout(workout, teamId)
    os.remove(filename)
    if not addedId:
        return False
    else:
        print(f'Sheet uploaded by {athlete["first"]} {athlete["last"]}. WorkoutId: {addedId}')
    return True, addedId, teamId, workout['athlete_list']


    

@socketio.on('valid-athletes')
def valid_athletes(addedId, teamId, athleteList):
    if len(athleteList) :
        for ath_idx, athlete in enumerate(athleteList):
            if len(athlete.split())==1:
                first, last = athlete[0], athlete[0]
            else:
                first, last = athlete.split() # TODO: this is dangerous!!!!!!
            # print()
            athlete_query = db.queryAthleteByName(first, last, teamId) # TODO: introduce fuzzy matching
            if athlete_query:
                athleteId = athlete_query['_id']
                print(f'attributed to {athlete}', end='\r')

                edited = db.addWorkoutToAthlete(athleteId, addedId)
            else: # we need to create a new athlete for this individual

                error = ''
                newId = random.randint(10, 100000)
                # add the login credentials to credentials DB
                add = db.addCredentials(newId, athlete, "pwhash", "salt")
                if not add:
                    error += 'failed to add user cred'

                # create athlete document from entered info
                permissions = ['']
                # if 'admin' in request.form.keys():
                #     permissions.append('admin')
                side = 'starboard'
                if ath_idx % 2:
                    side = 'port'

                athlete = {
                    "_id" : newId,
                    "first" : first,
                    "last" : last,
                    "permissions" : permissions,
                    "workouts" : [addedId],
                    "side" : side,
                    "active" : True,
                    "teamId" : teamId
                }
                # add athlete document to athlete db
                add = db.addAthlete(athlete)
                if not add:
                    error += "failed to add athlete"
                
                if len(error):
                    return redirect(f'/home?e=1&em={error}')

                print(f'attributed to {athlete}', end='\r')
                # edited = db.addWorkoutToAthlete(add, addedId)
        return True
    else:
        db.deleteWorkout(addedId)
        return False

app = create_app()


if __name__ == "main":
    socketio.run(app)