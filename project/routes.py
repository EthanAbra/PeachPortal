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
from .database import queryWorkoutMeta, deleteWorkout, removeWorkoutFromAthlete, editAthlete
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
@login_required
@main_bp.route('/home', methods=['GET'])
def home():

    user = current_user
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
    athlete = queryAthlete(user._id)

    workouts = getAllWorkouts(athlete['teamId'])
    
    if 'cox' in athlete['permissions'] or 'admin' in athlete['permissions']:
        delPerm = True
    else:
        delPerm = False

    
    html = render_template('workouts.html' ,workouts=workouts, delPerm=delPerm, athId=athlete['_id'])
    return make_response(html)

@login_required
@main_bp.route('/deleteWorkout', methods=['GET', 'POST'])
def delete():
    # load the user

    user = current_user
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
    # print(user)
    athlete = queryAthlete(user._id)

    if 'admin' in athlete['permissions']:
        isAdmin = True
    else:
        isAdmin = False

    workoutId = request.args.get('w')
    

    if 'cox' not in athlete['permissions']:
        return redirect(f'/myworkout?w={workoutId}')

    print("sup practice")
    practice = queryWorkoutData(workoutId)
    print(practice)
    elite = practice['peach_data']

    npts = 100

    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    ax = [None]*9
    ax[0] = figure(background_fill_color="#fafafa")
    ax[1] = figure(background_fill_color="#fafafa")
    ax[2] = figure(background_fill_color="#fafafa")
    ax[3] = figure(background_fill_color="#fafafa")
    ax[4] = figure(background_fill_color="#fafafa")
    ax[5] = figure(background_fill_color="#fafafa")
    ax[6] = figure(background_fill_color="#fafafa")
    ax[7] = figure(background_fill_color="#fafafa")
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

        ax[peep].multi_line(xs = theta3, ys = thetadot3, color=colors[peep],line_alpha = .05, line_join = 'bevel', line_width = 2, legend_label="%d seat" %(peep+1))
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

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # render template
    script, div = components(my_grid)
    html = render_template(
        'workout.html',
        workout = workout,
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
    )
    return make_response(html)

    # html = render_template('workout.html' , workout=practice, image = imagestring)
    # return make_response(html)



""" display a coach/coxswain portal for workout """
@login_required
@main_bp.route('/myworkout', methods=['GET'])
def myworkout():
    # load the user 

    user = current_user
    # print(user)
    athlete = queryAthlete(user._id)

    workoutId = request.args.get('w')
    

    practice = queryWorkoutData(workoutId)

    elite = practice['peach_data']

    npts = 100

    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    seat_num = practice['athlete_list'].index(athlete['first'] + " " + athlete['last'])


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
    ax[0].multi_line(xs = theta3, ys = thetadot3, line_alpha = .05, color=colors[0], legend_label = 'All Strokes Superimposed', line_join = 'bevel', line_width = 2)
    ax[0].xaxis.axis_label='Gate Angle °'
    ax[0].yaxis.axis_label='Gate Force (N)'

    # TODO: With average stroke. not individual stroke
    # START WITH JUST ONE STROKE BEFORE WE DO AVERAGING
    chosen_stroke = 100

    mathDict = peachhelp.helperMath(theta3[chosen_stroke], thetadot3[chosen_stroke], time_resamp[chosen_stroke])
    
    ideal_stroke = peachhelp.ideal_stroke_module(theta3[chosen_stroke], thetadot3[chosen_stroke])

    svdDict = peachhelp.svd_module(elite, 100, seat_num)

    peachhelp.plot_vector(svdDict['mean'], label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery', ax=bx)

    boat_svd = peachhelp.svd_module(elite, 100);

    peachhelp.plot_vector(boat_svd['mean'], color = "#ba34eb", label = 'Boat Mean Stroke', suppress_power=True, label2='Boat Mean Recovery', ax = bx)

    if seat_num !=7:
        stroke_svd = peachhelp.svd_module(elite, 100, 7)
        peachhelp.plot_vector(stroke_svd['mean'], color = "#30d93e", suppress_power=True, label2='Stroke Mean Recovery', ax = bx)


    ax[1].line(x = theta3[chosen_stroke], line_color = "#e3242b", y = thetadot3[chosen_stroke], line_join = 'bevel', line_width = 2, legend_label="Actual Stroke")
    ax[1].multi_line(xs = ideal_stroke['idealx'], ys = ideal_stroke['idealy'], line_join = 'bevel', line_width = 2, legend_label="Ideal Stroke")


    split = elite.get_rating_chunks()


    for idx, one_split in enumerate(split):
        split_svd = peachhelp.svd_module(elite, 100, seat_num, (one_split[0], one_split[1]))
        peachhelp.plot_vector(split_svd['mean'], ax=cx, color=Oranges9[idx], 
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

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    # render template
    script, div = components(my_grid)
    html = render_template(
        'workout.html',
        workout = workout,
        plot_script=script,
        plot_div=div,
        js_resources=js_resources,
        css_resources=css_resources,
    )
    return make_response(html)

    # html = render_template('workout.html' , workout=practice, image = imagestring)
    # return make_response(htm


@login_required
@main_bp.route('/profile', methods=['GET', 'POST'])
def profile():

    user = current_user
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
def editWorkout():

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


