import xlsxwriter
import openpyxl
from .database import getAllWorkouts
import datetime
from bson.binary import Binary
import pickle
import random
from .peach import PeachData
from .database import getAllWorkouts


def xlsxRead(filename, teamId):
    data = PeachData(filename)

    if isinstance(data, Exception):
        return False, "Powerline File is formatted incorrectly"


    try:
        nextId = int(getAllWorkouts(teamId, sort_by='_id')[0]['_id']) + 1 # increment _id
    except IndexError:
        nextId = random.randint(1, 1000)

    

    peach_bytes = pickle.dumps(data)


    workoutDict = {
        '_id' : nextId,
        'title' : str(filename),
        'date' : data.get_date(),
        'peach_data' : Binary(peach_bytes),
        'notes' : list(data.get_notes()),
        'athlete_list': list(data.get_athletes()),
    }

    print('read xlsx file')
    return True, workoutDict



# --------------------------------------------------------------------------------------#
