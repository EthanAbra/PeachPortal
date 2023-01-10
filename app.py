from project import create_app, socketio
from project.database import queryAthlete, addUnsplit
from flask_login import current_user
from project.sockfns import stsock, st_wr_chunk, mimewrap, st_valid_athletes
from project.xlsxMethods import xlsxRead, xlsxReadUnsplit
import os

#-----------------------------------------------------------------------
""" File upload method"""
#-----------------------------------------------------------------------


@socketio.on('start-transfer')
def start_transfer(filename, size):
    print("receivd start transfer")
    return stsock(filename, size)
   

@socketio.on('write-chunk')
def write_chunk(filename, offset, data):
    return st_wr_chunk(filename, offset, data)


@socketio.on('write-complete')
def write_complete(data):
    print("wrcomp")
    write_comp_process(data, 'peach processed')


@socketio.on('valid-athletes')
def valid_athletes(addedId, teamId, athleteMap):
    return st_valid_athletes(addedId, teamId, athleteMap)
    
@socketio.on('write-complete-unsplit')
def write_complete_unsplit(data):
    print("wrcompunsplit")
    write_comp_process(data, 'unsplit processed')
   
def write_comp_process(data, emitName):
    user = current_user
    athleteId = user._id
    athlete = queryAthlete(athleteId)
    teamId = athlete['teamId']
    
    if not mimewrap(data['serverfilename']):
        os.remove(data['serverfilename'])
        socketio.emit(emitName,{'ack':False, 'serverfilename': data['serverfilename'], 'clientfilename': data['clientfilename']})
        return

    if emitName == 'peach processed':
        success, workout = xlsxRead(data['serverfilename'], teamId)
    else:
        success, workout = xlsxReadUnsplit(data['serverfilename'], teamId)

    if not success:
        os.remove(data['serverfilename'])
        socketio.emit(emitName,{'ack':False, 'serverfilename': data['serverfilename'], 'clientfilename': data['clientfilename']})
        return

    addedId = addUnsplit(workout, teamId, data['serverfilename'])
    if not addedId:
        os.remove(data['serverfilename'])
        socketio.emit(emitName,{'ack':False, 'serverfilename': data['serverfilename'], 'clientfilename': data['clientfilename']})
        return
    else:
        print(f'Sheet uploaded by {athlete["first"]} {athlete["last"]}. WorkoutId: {addedId}')
    socketio.emit(emitName,{'ack':True, 'serverfilename': data['serverfilename'], 'clientfilename': data['clientfilename'], 'addedId': addedId, 'teamId' :teamId, 'athleteList':workout['athlete_list']})


app = create_app(debug=True)
