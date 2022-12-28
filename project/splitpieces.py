import numpy as np
from bokeh.plotting import figure, show
from bokeh.io import output_notebook, curdoc
from bokeh.layouts import layout, row, column, Spacer, gridplot, grid
from bokeh.models import CustomJS, RangeSlider, BoxAnnotation, Button, Dropdown, TextInput, AutocompleteInput
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from .database import queryUnsplitData, getAllAthletes
import os
from dotenv import load_dotenv
import pymongo
from bokeh.models import Tabs, TabPanel


load_dotenv()
if 'database_url' not in os.environ:
    CONNECTION_STRING = os.environ.get('database_url')
else:
    CONNECTION_STRING = os.environ['database_url']
bokehdb = pymongo.MongoClient(CONNECTION_STRING).peach


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
        rootLayout = doc.get_model_by_name('rootLayout')
        listOfSubLayouts = rootLayout.children[-2].children.copy()
        listOfSubLayouts = [x[0] for x in listOfSubLayouts]
        pieceArr = []
        for slitem in listOfSubLayouts:
            item = slitem._property_values['tabs'][1]._property_values['child']._property_values['children']
            retDict = {}
            retDict['title'] = item[1].value
            retDict['athletemap'] =  [x[0].value for x in item[2]._property_values['children']]
            pieceArr.append(retDict)
        print(pieceArr)
        about()


    def toggleMakeCallback(attr):
        # Get the layout object added to the documents root
        rootLayout = doc.get_model_by_name('rootLayout')
        listOfSubLayouts = rootLayout.children[-2].children.copy()

        crop_start = int(box.left)
        crop_end = int(box.right)

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
    
    rootLayout = layout(p1, p2, row(spacer_edit,rslider, make_piece, name = 'slider,-1,0'), row(Spacer(height = 5000)), name='rootLayout', sizing_mode="scale_both")
    mainLayout = gridplot(children = [], ncols=2)
    rootLayout.children.append(mainLayout)
    confirm_button = Button(label="Confirm Pieces Creation", button_type="success", width_policy='max',
                            height = 60, height_policy = "fixed", visible = False, 
                            name = 'confirm,' + str(elite.numstrokes*10), margin=(115,0,5,0))
    confirm_button.on_click(toggleConfirmCallback)
    rootLayout.children.append(confirm_button)
    doc.add_root(rootLayout)
    return doc