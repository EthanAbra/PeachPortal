from io import StringIO
from openpyxl import load_workbook
from xlsx2csv import Xlsx2csv
from .database import getAllWorkouts, getAllUnsplits, queryWorkoutMeta, queryUnsplitMeta
import datetime
from bson.binary import Binary
import pickle
import random
from .peach import PeachData
from .slimpeach import SlimPeach
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


def xlsxRead(filename):

    print("xlsxread called")

    idDict = get_sheet_ids(filename)
    

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


    try:
        data = [PeachData(df) for df in peach_frames]
    except Exception as e:
        print(e)
        return False, "Powerline File is formatted incorrectly"

    # TODO: double upload dont want conflict

    peach_bytes = pickle.dumps(data)


    nextId = random.randint(1, 2**24)
    already_id = queryWorkoutMeta(nextId)
    while already_id:
        nextId = random.randint(1, 2**24)
        already_id = queryWorkoutMeta(nextId)
     


    athlete_map = [list(data[0].get_athletes())]
    for datum in data[1:]:
        if len(list(datum.get_athletes()))<len(athlete_map[-1]):
            athlete_map.append(athlete_map[-1])
        else:
            athlete_map.append(list(datum.get_athletes()))
            
    workoutDict = {
        '_id' : nextId,
        'title' : f"workout on {data[0].date.strftime('%d/%m/%Y')}",
        'date' : data[0].date,
        'peach_data' : Binary(peach_bytes),
        'notes' : list(data[0].get_notes()),
        'athlete_list': athlete_map,
        'piece_list': piece_list
    }

    print('read xlsx file')
    return True, workoutDict

def xlsxReadUnsplit(filename):

    print("xlsxreadunsplit called")

    parsed = read_excel(filename, 1)

    try:
        data = SlimPeach(parsed)
    except Exception as e:
        print(e)
        return False, "Powerline File is formatted incorrectly"


    peach_bytes = pickle.dumps(data)


    nextId = random.randint(1, 2**24)
    already_id = queryWorkoutMeta(nextId)
    while already_id:
        nextId = random.randint(1, 2**24)
        already_id = queryWorkoutMeta(nextId)
     

    workoutDict = {
        '_id' : nextId,
        'title' : f"workout on {data.date.strftime('%d/%m/%Y')}",
        'date': data.date,
        'notes': list(data.misc_info),
        'peach_data' : Binary(peach_bytes),
        'athlete_list': list(data.athlete_map),
    }

    print('read usnplit file')
    return True, workoutDict



# --------------------------------------------------------------------------------------#



# --------------------------------------------------------------------------------------#
