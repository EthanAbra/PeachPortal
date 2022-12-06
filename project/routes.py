from polyfile.magic import MagicMatcher
from bokeh.models import Label, LabelSet
import seaborn as sns
from bokeh.layouts import layout, grid
from bokeh.plotting import show
from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.palettes import Oranges9
from bokeh.resources import INLINE
import json
from flask_login import current_user, login_required, logout_user
import uuid
from threading import Lock, Thread
import polyfile
from . import peachhelp
from flask import Flask, Blueprint, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from .database import getAllAthletes, getAllWorkouts, queryAthlete, queryWorkoutData, queryTeam
from .database import queryWorkoutMeta, deleteWorkout, removeWorkoutFromAthlete, editAthlete, editWorkout
import numpy as np
from . import socketio
from . import login_manager
from .models import User
from . import peach



# Blueprint Configuration
main_bp = Blueprint(
    "main_bp", __name__, template_folder="templates", static_folder="static"
)

#-----------------------------------------------------------------------
""" Static page rendering """
#-----------------------------------------------------------------------

""" renders the index page """
@main_bp.route('/', methods=['GET'])
def index():
    html = render_template('index.html')
    return make_response(html)

""" renders the about page """
@main_bp.route('/about', methods=['GET'])
def about():
    html = render_template('about.html')
    return make_response(html)

""" renders the home page """
@main_bp.route('/home', methods=['GET'])
@login_required
def home():

    user = current_user
    print(user)
    print(vars(user))
    if current_user.is_anonymous():
        print("anon!")
        return redirect('/login')
    athlete = queryAthlete(user._id)
    html = render_template('home.html', perms=athlete['permissions'], first=athlete['first'], async_mode=socketio.async_mode)
    return make_response(html)



#-----------------------------------------------------------------------
""" data-based page rendering """
#-----------------------------------------------------------------------

""" display all workouts """
@login_required
@main_bp.route('/workouts', methods=['GET'])
def workouts():
    user = current_user
    print(user)

    if user.is_anonymous():
        return redirect('/login')

    athlete = queryAthlete(user._id)

    workouts = getAllWorkouts(athlete['teamId'])
    
    if 'cox' in athlete['permissions'] or 'admin' in athlete['permissions']:
        delPerm = True
    else:
        delPerm = False

    renderlist = []
    for workout in workouts:
        if 'cox' in athlete['permissions'] or athlete['first'] + " " + athlete['last'] in queryWorkoutMeta(workout['_id'])['athlete_list']:
            renderlist += [workout]

    
    html = render_template('workouts.html' ,workouts=renderlist, delPerm=delPerm, athId=athlete['_id'], athlete_name = athlete['first'] + " " + athlete['last'])
    return make_response(html)

@login_required
@main_bp.route('/deleteWorkout', methods=['POST'])
def delete():
    # load the user

    user = current_user

    if user.is_anonymous():
        return redirect('/login')

    # print(user)
    athlete = queryAthlete(user._id)

    workoutId = request.args.get('wid')
    athleteId = request.args.get('aid')

    if request.method == 'POST':
        athleteId = int(request.form['aid'])
        workoutId = int(request.form['wid'])

        # verify requesting athlete is signed in athlete
        if athleteId != athlete['_id']:
            print(f"Delete accessed by unauthorized user {athlete['first']} {athlete['last']}")
            return render_template('error.html'), 500
        # verify requesting athlete 'owns' that workout
        if athlete['teamId'] != queryWorkoutMeta(workoutId)['teamId']:
            print(f"Cross-team delete attempted by user {athlete['first']} {athlete['last']} on team:{athlete['teamId']}")
            return render_template('error.html'), 500
        
        deleted = deleteWorkout(workoutId)


        if deleted:
            ctr = 0
            for athlete in getAllAthletes(athlete['teamId']):
                res = removeWorkoutFromAthlete(athlete['_id'], workoutId)
                print(f'unattributing {workoutId} from {athlete["_id"]}', end='\r')
                ctr += 1
            print(f'workout {workoutId} deleted, removed from {ctr} profiles')
            return redirect('/workouts')

    workout = queryWorkoutMeta(workoutId)
    html = render_template('confirmDelete.html', workout=workout, wid=workoutId, aid=athleteId)
    return make_response(html)


""" display a coach/coxswain portal for workout """
@login_required
@main_bp.route('/workout', methods=['GET'])
def workout():
    # load the user 
    user = current_user
    print(user)

    if user.is_anonymous():
        return redirect('/login')
    # print(user)
    athlete = queryAthlete(user._id)

    if 'admin' in athlete['permissions'] or 'cox' in athlete['permissions']:
        isAdmin = True
    else:
        isAdmin = False

    print(athlete['permissions'])
    workoutId = request.args.get('w')
    

    meta = queryWorkoutMeta(workoutId)

    piece_list = meta['piece_list']


    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    seatnum = 0
    if isAdmin:
        startingview = overallView(workoutId)
    else:
        seatnum, startingview = myworkout(workoutId)
        

    html = render_template(
        'workout.html',
        workout = meta,
        plot_div=startingview,
        js_resources=js_resources,
        css_resources=css_resources,
        isAdmin = isAdmin,
        num_seats = range(8),
        athId = athlete['_id'],
        colors = colors,
        piece_list = piece_list,
        seatnum = seatnum
    )

    return html


@login_required
@main_bp.route('/workoutoverall', methods = ['POST'])
def overallView(internalId= None):

    npts = 100

    user = current_user
    print(user)
    # print(user)
    if internalId:
        workoutId = internalId
    else:
        workoutId = request.args.get('w')

    piece_num = request.args.get('piece')
    
    practice = queryWorkoutData(workoutId)

    meta = queryWorkoutMeta(workoutId)

    if not piece_num:
        elite = practice['peach_data'][0]
    else:
        elite = practice['peach_data'][int(piece_num)]



    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    ax = [None]*9
    sizer = "scale_width"
    ax[0] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[1] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[2] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[3] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[4] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[5] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[6] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[7] = figure(background_fill_color="#fafafa", sizing_mode = sizer)
    ax[8] = figure(background_fill_color="#fafafa", sizing_mode="stretch_width")


    stroke_nums = list(range(1, elite.numstrokes+1))

    average_aper_data = elite.get_average_aper_data()
    for peep in range(8):
        theta3 = []
        thetadot3 = []
        for s in range(1, elite.numstrokes):
            dat3 = elite.resample_stroke(s, [0, peep+1,peep+1+8], npts)
            theta3 += [dat3[:,1]]
            thetadot3 += [dat3[:,2]]
        label = Label(x=np.min(theta3), y=-23, x_units='data', y_units = 'data', 
        text='Average:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %
        (average_aper_data[1+peep],average_aper_data[17+peep], average_aper_data[33+peep], average_aper_data[121+peep]),
            border_line_color='black', border_line_alpha=.5,
            background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')

        ax[peep].multi_line(xs = theta3, ys = thetadot3, color=colors[peep],line_alpha = max(-0.001111*elite.numstrokes + 0.2722, .02), line_join = 'bevel', line_width = 2, legend_label="%d seat" %(peep+1))
        ax[peep].xaxis.axis_label='Gate Angle °'
        ax[peep].yaxis.axis_label='Gate Force (N)'
        ax[peep].add_layout(label)
        ax[8].line(x = stroke_nums, y = elite.aper_data[:,1+peep][:-1], line_color = colors[peep], line_join = 'bevel', line_width = 2, legend_label="%d seat" %(peep+1))

    boat_pow = elite.get_boat_power()
    ax[8].line(x = stroke_nums, y = boat_pow, line_join = 'bevel', line_width = 2, legend_label = "Average Boat Power")

    

    label = Label(x=elite.numstrokes//2-10, y=550, x_units='data', y_units = 'data', 
        text='Average Boat:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %
        (np.mean(average_aper_data[1:9]),np.mean(average_aper_data[17:25]), np.mean(average_aper_data[33:41]), np.mean(average_aper_data[121:129])),
            border_line_color='black', border_line_alpha=.5,
            background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')

    ax[8].add_layout(label)


    bow_four = [ax[0], ax[1], ax[2], ax[3]]
    stern_four = [ax[4],ax[5],ax[6],ax[7]]


    my_grid = grid([
        bow_four,
        stern_four,
        [ax[8]],
    ])

    my_grid.sizing_mode = "scale_both"

    response = ""

    if not internalId:
        if len(meta['piece_list']) > 1:
            response = '<div id = "piecelist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
            for num, piece in enumerate(meta['piece_list']):
                response +=  '<li class="nav-item">'  
                response += '<button class="btn btn-outline-info"'
                response +=  'hx-post= "/workoutoverall?w=' + str(meta['_id']) + '&piece=' + str(num) + '" hx-target = "#raw">' + piece + '</button>' 
                response += '</li>'
            response += '</ul> </div>'
 

    # render template
    script, div = components(my_grid)
    
    return response + '<div id = "overall">' + div+script + '<div>'


@login_required
@main_bp.route('/workoutseat', methods = ['POST'])
def workoutforseat():
    user=  current_user
    # print(user)

    athlete = queryAthlete(user._id)


    workoutId = request.args.get('w')
    seat_num = int(request.args.get('s'))
    piece_num = int(request.args.get('piece'))
    
    practice = queryWorkoutData(workoutId)
    meta = queryWorkoutMeta(workoutId)

    elite = practice['peach_data'][piece_num]


    return individual_workout(elite, seat_num, meta)
     


""" display an individual's portal for workout """
@login_required
@main_bp.route('/myworkout', methods=['GET'])
def myworkout(internalId = None):
    # load the user 

    user = current_user
    # print(user)
    athlete = queryAthlete(user._id)

    if internalId:
        workoutId = internalId
    else:
        workoutId = request.args.get('w')
    
    practice = queryWorkoutData(workoutId)

    meta = queryWorkoutMeta(workoutId)

    piece_num = request.args.get('piece')

    if piece_num:
        elite = practice['peach_data']
    else:
        elite = practice['peach_data'][0]

    if internalId:
        internal = True

    seat_num = meta['athlete_list'].index(athlete['first'] + " " + athlete['last'])
    
    return seat_num, individual_workout(elite, seat_num, meta, internal)



def individual_workout(elite, seat_num, meta, internal = False):
    npts = 100

    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']



    ax = [None]*2
    ax[0] = figure(background_fill_color="#fafafa")
    ax[1] = figure(background_fill_color="#fafafa")
    bx = [None]*2
    bx[0] = figure(background_fill_color="#fafafa")
    bx[1] = figure(background_fill_color="#fafafa")


    cx = [None]*2
    cx[0] = figure(background_fill_color="#fafafa")
    cx[1] = figure(background_fill_color="#fafafa")



    # stroke_nums = list(range(1, elite.numstrokes+1))

    theta3 = []
    thetadot3 = []
    time_resamp = []
    for s in range(1, elite.numstrokes):
        dat3 = elite.resample_stroke(s, [0, seat_num+1,seat_num+1+8], npts)
        time_resamp += [dat3[:,0]]
        theta3 += [dat3[:,1]]
        thetadot3 += [dat3[:,2]]
    ax[0].multi_line(xs = theta3, ys = thetadot3, line_alpha = max(-0.001111*elite.numstrokes + 0.2722, .02), color=colors[seat_num], legend_label = 'All Strokes Superimposed', line_join = 'bevel', line_width = 2)
    ax[0].xaxis.axis_label='Gate Angle °'
    ax[0].yaxis.axis_label='Gate Force (N)'
    average_aper_data = elite.get_average_aper_data()
    label = Label(x=np.min(theta3), y=-23, x_units='data', y_units = 'data', 
    text='Average:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %
    (average_aper_data[1+seat_num],average_aper_data[17+seat_num], average_aper_data[33+seat_num], average_aper_data[121+seat_num]),
        border_line_color='black', border_line_alpha=.5,
        background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')
    ax[0].add_layout(label)



    svdDict = peachhelp.svd_module(elite, 100, seat_num)
    
    peachhelp.plot_vector(svdDict['mean'], label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery', ax=bx)

    boat_svd = peachhelp.svd_module(elite, 100)

    peachhelp.plot_vector(boat_svd['mean'], color = "#ba34eb", label = 'Boat Mean Stroke', suppress_power=True, label2='Boat Mean Recovery', ax = bx)

    if seat_num !=7:
        stroke_svd = peachhelp.svd_module(elite, 100, 7)
        peachhelp.plot_vector(stroke_svd['mean'], color = "#30d93e", suppress_power=True, label2='Stroke Mean Recovery', ax = bx)


    mathDict = peachhelp.plot_single(boat_svd['mean'], ax, color = "#FFA500", label= "Actual Stroke")


    split = elite.get_rating_chunks()

    # TODO: GIVE LEGEND A TITLE
    for idx, one_split in enumerate(split):
        split_svd = peachhelp.svd_module(elite, 100, seat_num, (one_split[0], one_split[1]))
        peachhelp.plot_vector(split_svd['mean'], ax=cx, color=Oranges9[idx], legend_title = "Stroke over Time",
        label="Stroke %d-%d, avg s/m: %.1f, avg W: %.1fW" 
        %(one_split[0]+1, one_split[1]+1, 
        elite.get_average_aper_data(one_split)[129], 
        elite.get_average_aper_data(one_split)[1+seat_num]), 
        label2 = "Stroke %d-%d, avg Max Force: %.2f%%" 
        %(one_split[0]+1, one_split[1]+1, 
        elite.get_average_aper_data(one_split)[121+seat_num]))



    my_grid = grid([
        [ax[0],ax[1]],
        [bx[0], bx[1]],
        [cx[0], cx[1]]
    ])

    my_grid.sizing_mode = "scale_both"

    response = ""

    if len(meta['piece_list']) > 1 and not internal:
        response = '<div id = "piecelist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
        for num, piece in enumerate(meta['piece_list']):
            response +=  '<li class="nav-item">'  
            response += '<button class="btn btn-outline-info"'
            response +=  'hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s=' 
            response += str(seat_num) + '&piece=' + str(num) + '" hx-target = "#raw">' + piece + '</button>' 
            response += '</li>'
        response += '</ul> </div>'

    # render template
    script, div = components(my_grid)

    return response + '<div id = "individual">' + div + script + "</div>"


@login_required
@main_bp.route('/profile', methods=['GET', 'POST'])
def profile():

    user = current_user

    if user.is_anonymous():
        return redirect('/login')
    # print(user)

    # if loading another athlete, pass in the id as 'a'
    if request.args.get('a'):
        athleteId = request.args.get('a')
        athlete = queryAthlete(athleteId)

        # security check: is the req'd athlete on the same team?
        viewerTeam = queryAthlete(user._id)['teamId']
        if viewerTeam != athlete['teamId']:
            return make_response(render_template('error.html'))

    # if no 'a', load the self's profile
    else:
        athleteId = user._id
        athlete = queryAthlete(athleteId)

    return render_template('profile.html', athlete=athlete)

@login_required
@main_bp.route('/team', methods=['GET', 'POST'])
def team():

    user = current_user
    if user.is_anonymous():
        return redirect('/login')
    # print(user)
    athleteId = user._id
    athlete = queryAthlete(athleteId)

    if 'admin' not in athlete['permissions']:
        return render_template('error.html'), 500



    teamId = athlete['teamId']
    teamName = queryTeam(teamId)['name']
    teammates = getAllAthletes(teamId)

    sumModified = 0
    if request.method == 'POST':
        for key in list(request.form):
            field, athleteId = key.split('_')
            newVal = request.form[key]
            if field == 'active':
                sumModified += editAthlete(int(athleteId), field, True)
            else:
                sumModified += editAthlete(int(athleteId), field, newVal)

            if 'active' not in request.form:
                sumModified += editAthlete(int(athleteId), 'active', False)

    print(f'Team "{teamName}" edited by {athlete["first"]} {athlete["last"]}')

    html= render_template('team.html', athletes=teammates, teamName=teamName)
    return make_response(html)


#-----------------------------------------------------------------------
""" database edit routes """
#-----------------------------------------------------------------------
@main_bp.route('/editWorkout', methods=['POST'])
def editWorkoutRoute():
    field = request.form['field']
    newVal = request.form['newVal']
    workoutID = int(request.form['workoutId'])

    res = editWorkout(workoutID, field, newVal)

    print(res, f' workout {workoutID} edited fied {field} with {newVal}')

    return redirect(f'/workout?w={workoutID}')



#-----------------------------------------------------------------------
""" Error handling """
#-----------------------------------------------------------------------

@main_bp.errorhandler(404)
@main_bp.errorhandler(500)
def handleError(ex):

    html = render_template('error.html')
    response = make_response(html)
    return response


