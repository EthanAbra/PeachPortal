from io import StringIO
from openpyxl import load_workbook
from xlsx2csv import Xlsx2csv
from .database import getAllWorkouts
import datetime
from bson.binary import Binary
import pickle
import random
from .peach import PeachData
from .database import getAllWorkouts
import pandas as pd


def xlsxRead(filename, teamId):

    try:
        buffer = StringIO()
        Xlsx2csv(filename, outputencoding="utf-8").convert(buffer)
        buffer.seek(0)
        df = pd.read_csv(buffer, low_memory=False, header=None)
    except Exception as e:
        return False, "Powerline File is formatted incorrectly"


    data = PeachData(df)

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
