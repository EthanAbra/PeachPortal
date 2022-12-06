from io import StringIO
from openpyxl import load_workbook
from xlsx2csv import Xlsx2csv
from .database import getAllWorkouts
import datetime
from bson.binary import Binary
import pickle
import random
from .peach import PeachData
from .database import getAllWorkouts, queryWorkoutMeta
import pandas as pd
import json
import xmltodict
import zipfile


def get_sheet_ids(file_path):
    sheet_names = []
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        xml = zip_ref.open(r'xl/workbook.xml').read()
        dictionary = xmltodict.parse(xml)

        if not isinstance(dictionary['workbook']['sheets']['sheet'], list):
            sheet_names.append({'id': dictionary['workbook']['sheets']['sheet']['@sheetId'], 'name': dictionary['workbook']['sheets']['sheet']['@name']})
        else:
            for sheet in dictionary['workbook']['sheets']['sheet']:
                sheet_names.append( {'id': sheet['@sheetId'], 'name': sheet['@name']})
    return sheet_names


def read_excel(path: str, sheetid:int) -> pd.DataFrame:     
    buffer = StringIO()            
    Xlsx2csv(path, outputencoding="utf-8").convert(buffer, sheetid = sheetid)         
    buffer.seek(0)     
    df = pd.read_csv(buffer, low_memory=False, header=None) 
    return df


def xlsxRead(filename, teamId):

    print("xlsxread called")

    print()
    print()
    idDict = get_sheet_ids(filename)

    print(idDict)

    peach_frames = []
    piece_list = []


    for sheets in idDict:
        try:
            parsed = read_excel(filename, int(sheets['id']))
            # print(parsed)
            if parsed.columns[-1]>130:
                peach_frames += [parsed]
                piece_list += [json.dumps(sheets['name'])]
        except Exception as e:
            return False, "Powerline File is formatted incorrectly"

    print("peach data time")
    try:
        data = [PeachData(df) for df in peach_frames]
    except Exception as e:
        print(e)
        return False, "Powerline File is formatted incorrectly"

    # TODO: remove file if false?? might already handle that

    try:
        nextId = int(getAllWorkouts(teamId, sort_by='_id')[0]['_id']) + 1 
    except IndexError:
        nextId = random.randint(1, 1000)
    already_id = queryWorkoutMeta(nextId)
    while already_id:
        nextId = random.randint(10, 100000)
        already_id = queryWorkoutMeta(nextId)
     



    print(piece_list)
    

    peach_bytes = pickle.dumps(data)

    #TODO: NOTES & ATHLETE LIST MULTI-DIMENSIONAL

    workoutDict = {
        '_id' : nextId,
        'title' : str(filename),
        'date' : data[0].get_date(),
        'peach_data' : Binary(peach_bytes),
        'notes' : list(data[0].get_notes()),
        'athlete_list': list(data[0].get_athletes()),
        'piece_list': piece_list
    }

    print('read xlsx file')
    return True, workoutDict



# --------------------------------------------------------------------------------------#
