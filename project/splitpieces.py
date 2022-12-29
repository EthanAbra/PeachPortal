import numpy as np
from bokeh.plotting import figure
from bokeh.layouts import layout, row, column, Spacer, gridplot, grid
from bokeh.models import CustomJS, RangeSlider, BoxAnnotation, Button, Dropdown, TextInput, AutocompleteInput, OpenURL
from bokeh.models.sources import ColumnDataSource
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from .database import queryUnsplitData, addWorkout, getAllAthletes, queryUnsplitMeta, getAllWorkouts, queryWorkoutMeta
from .database import addWorkoutToAthlete, deleteWorkout, addCredentials, getCredentialsbyId, addAthlete
import os
from dotenv import load_dotenv
import pymongo
from bokeh.models import Tabs, TabPanel
from .peach import PeachData
from .xlsxMethods import read_excel
import random
import pickle
from bson.binary import Binary
from fuzzywuzzy import fuzz
from fuzzywuzzy import process



load_dotenv()
if 'database_url' not in os.environ:
    CONNECTION_STRING = os.environ.get('database_url')
else:
    CONNECTION_STRING = os.environ['database_url']
bokehdb = pymongo.MongoClient(CONNECTION_STRING).peach

def valid_athletes(addedId, teamId, athleteMap):
    print(athleteMap)
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
                
    print(athDict)
    
    if len(athDict) :
        for athlete, athleteTuple in athDict.items():
            print(athlete)
            athlete_piece_list, side = athleteTuple
            
            if len(athlete.split())==1:
                first, last = athlete[0], athlete[0]
            else:
                first, last = athlete.split() 
            # print()

            allAthletes = getAllAthletes(str(teamId), 'name', False, bokehdb)

            athlete_query = None
            for existingAthlete in allAthletes:
                if fuzz.token_sort_ratio(existingAthlete['namestring'], athlete) >= 85:
                    athlete_query = existingAthlete
                    break

            if athlete_query:
                athleteId = athlete_query['_id']
                print(f'attributed to {athlete}', end='\r')
                edited = addWorkoutToAthlete(athleteId, addedId, athlete_piece_list, bokehdb)
            else: # we need to create a new athlete account for this individual

                error = ''
                newId = random.randint(10, 100000)
                already_id = getCredentialsbyId(newId, bokehdb)
                while already_id:
                    newId = random.randint(10, 100000)
                    already_id = getCredentialsbyId(newId, bokehdb)
     
                # add temporary login credentials to credentials DB
                add = addCredentials(newId, athlete, "pwhash", "salt", bokehdb)
                if not add:
                    error += 'failed to add user cred'

                # create athlete document from entered info
                permissions = ['']

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
                add = addAthlete(athleteJson, bokehdb)
                if not add:
                    error += "failed to add athlete"
                
                if len(error):
                    False

                print(f'attributed to {athlete}', end='\r')
        return True
    else:
        deleteWorkout(addedId, bokehdb)
        return False
def processPieces(unsplitId, unsplitDicts, teamId):
    meta = queryUnsplitMeta(unsplitId, bokehdb)
    
    parsed = read_excel(meta['serverfilename'], 1)
    bigPeach = PeachData(parsed)
    

    big_start_times = bigPeach.start_times
    big_data = bigPeach.data
    big_aper_data = bigPeach.aper_data
    big_t0 = bigPeach.t0
    
    pieces = []
    athlete_map = []
    piece_list = []
    
    for unsplitdict in unsplitDicts:
        unsplitdata = {}
        unsplitdata['athlete_map'] = unsplitdict['athlete_map']
        unsplitdata['date'] = bigPeach.date
        unsplitdata['notes'] = bigPeach.misc_info
        unsplitdata['start_times'] = big_start_times[unsplitdict['start_stroke']-1:unsplitdict['end_stroke']+1]
        # print(unsplitdata['start_times'])
        unsplitdata['aper_headers'] = bigPeach.aper_headers
        unsplitdata['aper_data'] = big_aper_data[unsplitdict['start_stroke']-1:unsplitdict['end_stroke']]
        unsplitdata['headers'] = bigPeach.headers
        data_start = bigPeach.open_ind(unsplitdata['start_times'][0])
        data_stop = bigPeach.open_ind(unsplitdata['start_times'][-1])
        print(data_start)
        print(data_stop)
        unsplitdata['data'] = big_data[data_start:data_stop]
        print(unsplitdata['data'])
        unsplitdata['t0'] = int(unsplitdata['data'][0][0])
        unsplitdata['dt'] = bigPeach.dt
        pieces.append(PeachData.from_unsplit(unsplitdata))
        athlete_map.append(unsplitdata['athlete_map'])
        piece_list.append(unsplitdict['title'])
    
    peach_bytes = pickle.dumps(pieces)
    
    # TODO: better insertion, support double uploads
    try:
        nextId = int(getAllWorkouts(teamId, sort_by='_id', db = bokehdb)[0]['_id']) + 1 
    except IndexError:
        nextId = random.randint(1, 1000)
    already_id = queryWorkoutMeta(nextId, bokehdb)
    while already_id:
        nextId = random.randint(10, 100000)
        already_id = queryWorkoutMeta(nextId, bokehdb)
    athlete_map = [unsplitDicts[i]['athlete_map'] for i in range(len(unsplitDicts))]
     
    
     
        
    workoutDict = {
        '_id' : nextId,
        'title' : str(meta['serverfilename']),
        'date' : bigPeach.date,
        'peach_data' : Binary(peach_bytes),
        'notes' : list(bigPeach.misc_info),
        'athlete_list': athlete_map,
        'piece_list': piece_list
    }

        
    # create workout with this workoutdict, delete unsplit, return id of workout
    addedId = addWorkout(workoutDict, teamId, bokehdb)
    if addedId:
        print('successfull add')
        if valid_athletes(addedId, teamId, athlete_map): 
            print('sucessfully attributed')
            os.remove(meta['serverfilename'])
            return addedId
    




def my_insort_left(a, x, lo=0, hi=None):
    if lo < 0:
        raise ValueError('lo must be non-negative')
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if int(a[mid].name.split(',')[1]) < int(x.name.split(',')[1]): lo = mid+1
        else: hi = mid
    a.insert(lo, x)

def convertMillis(millis):
    seconds=(millis/1000)%60
    minutes=(millis/(1000*60))%60
    return seconds, int(minutes)


def my_gui(doc):
    args = doc.session_context.request.arguments
    unsplitId = int(args.get('id')[0])
    practice = queryUnsplitData(unsplitId, bokehdb)
    athlete_completes = [athlete['namestring'] for athlete in getAllAthletes(str(int(args.get('teamId')[0])), 'name', False, bokehdb)]
    print(athlete_completes)
    elite = practice['peach_data']
    athlete_map = elite.athlete_map
    if len(athlete_map)==0:
        athlete_map = ['seat ' + str(i) for i in range(1,9)]
    
    stroke_nums = np.arange(elite.numstrokes)
    boat_pow = elite.get_boat_power()
    tools = 'pan, box_zoom, wheel_zoom, reset, undo, redo, save'
    p1 = figure(sizing_mode = "stretch_width", tools=tools,
               x_range=(1, elite.numstrokes), name = 'seats,-3,0', height = 400, height_policy = "fixed")
    p1.toolbar.logo = None

    # Slider figure
    p2 = figure(toolbar_location=None, sizing_mode = "stretch_width",
               x_range=(1, elite.numstrokes), name = 'boat,-2,0', height = 400, height_policy = "fixed")
    p2.yaxis.major_label_text_color = None
    p2.yaxis.major_tick_line_color= None
    p2.yaxis.minor_tick_line_color= None
    p2.grid.grid_line_color=None
    p2.toolbar.active_drag = None
    p2.toolbar.active_scroll = None
    p2.toolbar.active_tap = None

    # Slider widget
    rslider = RangeSlider(start=1, end=elite.numstrokes, value=(1,elite.numstrokes), bar_color = "#0398fc",
                              title=None,show_value=False, height = 50, height_policy = "fixed", sizing_mode = "stretch_width", margin = (45,10,50,0))
    spacer_edit = Spacer(width=40)
    
    make_piece = Button(label="Make Piece", button_type="success",height = 100, width = 100, height_policy = "fixed", margin = (0,0,500,0), css_classes =['custom_button_bokeh'])
    
    plot = figure(
        width=600,
        height=600,
        visible = False        
    )

    source = ColumnDataSource({
    'x': [1, 2, 3],
    'y': [4, 5, 6],
    })
    cr = plot.circle(
        x='x', y='y',
        source=source, size=10, color="navy", alpha=0.5
    )

    callback = CustomJS(args=dict(source=source), code="""
        console.log('This code will be overwritten')
    """)
    cr.glyph.js_on_change('size', callback)
    
    
    
    
    def toggleRemoveCallback(attr):
        rootLayout = doc.get_model_by_name('rootLayout')
        listOfSubLayouts = rootLayout.children[-2].children.copy()
        listOfSubLayouts = [x[0] for x in listOfSubLayouts]
        tryname = doc.get_model_by_name('tabs,' + str(attr.model.name))
        trycbox = doc.get_model_by_name('cbox,' + str(attr.model.name))
        trymbox = doc.get_model_by_name('mbox,' + str(attr.model.name))
        listOfSubLayouts.remove(tryname)
        rootLayout.children[-2] = gridplot(children = listOfSubLayouts, ncols=2, toolbar_location = None)
        if len(listOfSubLayouts) == 0:
            tryconf = doc.get_model_by_name('confirm,' + str(elite.numstrokes*10))
            tryconf.visible = False
        rootLayout.children[1].center.remove(trycbox)
        rootLayout.children[0].center.remove(trymbox)


    def toggleConfirmCallback(attr):
        confirm_button.disabled=True
        rootLayout = doc.get_model_by_name('rootLayout')
        listOfSubLayouts = rootLayout.children[-2].children.copy()
        listOfSubLayouts = [x[0] for x in listOfSubLayouts]
        pieceArr = []
        for slitem in listOfSubLayouts:
            item = slitem._property_values['tabs'][1]._property_values['child']._property_values['children']
            retDict = {}
            retDict['start_stroke'], retDict['end_stroke'] = int(item[0].name.split(',')[0]), int(item[0].name.split(',')[1])
            retDict['title'] = item[1].value
            retDict['athlete_map'] =  [x[0].value for x in item[2]._property_values['children']]
            pieceArr.append(retDict)
        print(pieceArr)
        addedId = processPieces(unsplitId, pieceArr, str(int(args.get('teamId')[0])))
        
        js_code = f"""
                console.log('Hello!');
                window.location.replace("../workout?w={addedId}");
            """
        callback.code = js_code  # update js code
        cr.glyph.size += 1       # trigger the javascript code



    def toggleMakeCallback(attr):
        # Get the layout object added to the documents root
        crop_start = int(box.left)
        crop_end = int(box.right)
        if crop_end - crop_start <1:
            return
        rootLayout = doc.get_model_by_name('rootLayout')
        listOfSubLayouts = rootLayout.children[-2].children.copy()



        timesecs, timemins = convertMillis(elite.start_times[crop_end]-elite.start_times[crop_start])

        tryname = doc.get_model_by_name('tabs,' + str(crop_start) + "," + str(crop_end))

        if tryname is not None:
            return

        text_inputs = [AutocompleteInput(value=athlete, title="Seat " + str(athIdx+1) + ":", completions = athlete_completes,
                                 name = 'tinp,' + str(crop_start) + "," + str(crop_end)) for athIdx, athlete in enumerate(athlete_map)]
        title_input = TextInput(value = "Strokes " + str(crop_start)+'-'+str(crop_end), align="center",
                                title = "Piece Name:", name = 'tinp,' + str(crop_start) + "," + str(crop_end))
        rmv_piece = Button(label="Remove Piece", button_type="danger", name = str(crop_start) + "," + str(crop_end), width_policy='max', height = 60, height_policy = "fixed")
        rmv_piece.on_click(toggleRemoveCallback)

        p3 = figure(min_border = 0, title='^^CHANGE ABOVE^^ Strokes %d-%d, Duration %dm %.2fs' %
        (crop_start, crop_end, timemins, timesecs))
        p3.title.text_color="red"
        p3.title.text_font_style="bold"
        p3.line(stroke_nums[crop_start:crop_end+1],boat_pow[crop_start:crop_end+1])
        tab1 = TabPanel(child=p3, title="piece")

        p5 = column(rmv_piece, title_input, grid(text_inputs, ncols = 2))

        tab2 = TabPanel(child=p5, title="piece info")

        tabs = Tabs(tabs=[ tab1, tab2 ], name = 'tabs,' + str(crop_start)+','+str(crop_end), margin = (105,0,-105,0))

        listOfSubLayouts = [x[0] for x in listOfSubLayouts]

        my_insort_left(listOfSubLayouts, tabs) 

        rootLayout.children[-2] = gridplot(children = listOfSubLayouts, ncols=2, toolbar_location = None)

        cropbox = BoxAnnotation(fill_alpha=0.5, line_alpha=0.5, level='underlay', 
                                fill_color = 'green', left=crop_start, right=crop_end, name='cbox,' +  str(crop_start) + "," + str(crop_end))
        p2.add_layout(cropbox)
        mainbox = BoxAnnotation(fill_alpha=0.1, line_alpha=0.5, level='underlay', 
                                fill_color = 'green', left=crop_start, right=crop_end, name='mbox,' +  str(crop_start) + "," + str(crop_end))
        p1.add_layout(mainbox)
        tryconf = doc.get_model_by_name('confirm,' + str(elite.numstrokes*10))
        tryconf.visible = True

        
    # Set the callback for the toggle button
    make_piece.on_click(toggleMakeCallback)


    # Box selection
    box = BoxAnnotation(fill_alpha=0.5, line_alpha=0.5, level='underlay', left=1, right=elite.numstrokes)

    def update_range(attr, old, new):
        box.left = new[0]
        box.right = new[1]
        p1.x_range.start = new[0]
        p1.x_range.end = new[1]

    rslider.on_change('value',update_range)

    # Plot

    p2.line(x = stroke_nums, y = boat_pow, line_join = 'bevel', line_width = 2)
    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']
    
    for peep in range(8):
        p1.line(np.arange(elite.numstrokes), elite.aper_data[:,1+peep][:-1], line_color = colors[peep], line_join = 'bevel', line_width = 2)

    # Layout
    p2.add_layout(box)
    
    rootLayout = layout(p1, p2, row(spacer_edit,rslider, make_piece, plot, name = 'slider,-1,0'), row(Spacer(height = 5000)), name='rootLayout', sizing_mode="scale_both")
    mainLayout = gridplot(children = [], ncols=2)
    rootLayout.children.append(mainLayout)
    confirm_button = Button(label="Confirm Pieces Creation", button_type="success", width_policy='max',
                            height = 60, height_policy = "fixed", visible = False, 
                            name = 'confirm,' + str(elite.numstrokes*10), margin=(115,0,5,0))
    confirm_button.on_click(toggleConfirmCallback)
    rootLayout.children.append(confirm_button)
    doc.add_root(rootLayout)
    return doc