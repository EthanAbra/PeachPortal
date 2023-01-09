from polyfile.magic import MagicMatcher
from bokeh.models import Label, LabelSet, PolyAnnotation, Text, Range1d, ColumnDataSource
import seaborn as sns
from bokeh.layouts import layout, grid, gridplot, row
from bokeh.plotting import show
from bokeh.embed import components, server_document
from bokeh.plotting import figure
from bokeh.palettes import Oranges9
from bokeh.resources import INLINE
import json
import os
from flask_login import current_user, login_required, logout_user
import uuid
import polyfile
from . import peachhelp
from flask import Flask, Blueprint, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from flask import current_app, g
from .database import getAllAthletes, getAllWorkouts, queryAthlete, queryWorkoutData, queryTeam, queryUnsplitMeta
from .database import queryWorkoutMeta, deleteWorkout, removeWorkoutFromAthlete, editAthlete, editWorkout, deleteUnsplit
from .database import getAllUnsplits
import numpy as np
from . import socketio
from . import login_manager
from .models import User
from . import peach
import collections
from bokeh.server.util import bind_sockets

unpickledWorkouts = collections.defaultdict()


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
@main_bp.route('/workouts', methods=['GET'])
@login_required
def workouts():
    user = current_user
    if user.is_anonymous():
        return redirect('/login')

    athlete = queryAthlete(user._id)
    unsplitworkouts = []
    workouts = list(getAllWorkouts(athlete['teamId']))
    if 'cox' in athlete['permissions'] or 'admin' in athlete['permissions']:
        unsplitworkouts = list(getAllUnsplits(athlete['teamId']))
        delPerm = True
    else:
        delPerm = False
    renderlist = []
    for workout in workouts:
        if 'cox' in athlete['permissions'] or any(athlete['namestring'] in sublist for sublist in workout['athlete_list']):
            renderlist += [workout]

    render_unsplit = []
    for workout in unsplitworkouts:
        if not os.path.exists(workout['serverfilename']):
            deleteUnsplit(workout['_id'])
            unsplitworkouts.remove(workout)
        else:
            render_unsplit.append(workout)
    html = render_template('workouts.html' ,workouts=renderlist, unsplitworkouts = render_unsplit, delPerm=delPerm, athId=athlete['_id'], athlete_name = athlete['first'] + " " + athlete['last'])
    return make_response(html)

@main_bp.route('/deleteWorkout', methods=['GET', 'POST'])
@login_required
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
        print(request.form)
        athleteId = int(request.form['aid'])
        workoutId = int(request.form['wid'])

        # verify requesting athlete is signed in athlete
        if athleteId != athlete['_id']:
            print(f"Delete accessed by unauthorized user {athlete['first']} {athlete['last']}")
            return render_template('error.html'), 500
        # verify requesting athlete 'owns' that workout

        
        if request.form['unsplit'] == 'True':
            if athlete['teamId'] != queryUnsplitMeta(workoutId)['teamId']:
                print(f"Cross-team delete attempted by user {athlete['first']} {athlete['last']} on team:{athlete['teamId']}")
                return render_template('error.html'), 500
            deleted = deleteUnsplit(workoutId)
            return redirect('/workouts')
        else:
            if athlete['teamId'] != queryWorkoutMeta(workoutId)['teamId']:
                print(f"Cross-team delete attempted by user {athlete['first']} {athlete['last']} on team:{athlete['teamId']}")
                return render_template('error.html'), 500
            deleted = deleteWorkout(workoutId)


        if deleted:
            removed_value = unpickledWorkouts.pop(workoutId, 'No workout found')
            ctr = 0
            for athlete in getAllAthletes(athlete['teamId']):
                res = removeWorkoutFromAthlete(athlete['_id'], workoutId)
                print(f'unattributing {workoutId} from {athlete["_id"]}', end='\r')
                ctr += 1
            print(f'workout {workoutId} deleted, removed from {ctr} profiles')
            return redirect('/workouts')

    unsplit = False
    if request.args.get('unsplit') is not None:
        workout = queryUnsplitMeta(workoutId)
        unsplit = True
    else:
        workout = queryWorkoutMeta(workoutId)
    html = render_template('confirmDelete.html', workout=workout, wid=workoutId, aid=athleteId, unsplit = str(unsplit))
    return make_response(html)


""" display a coach/coxswain portal for workout """
@main_bp.route('/workout', methods=['GET'])
@login_required
def workout():
    # load the user 
    user = current_user
    # print(user)

    if user.is_anonymous():
        return redirect('/login')
    # print(user)
    athlete = queryAthlete(user._id)

    if 'admin' in athlete['permissions'] or 'cox' in athlete['permissions']:
        isAdmin = True
    else:
        isAdmin = False

    # print(athlete['permissions'])
    workoutId = request.args.get('w')
    

    meta = queryWorkoutMeta(workoutId)

    if not meta:
        print('no meta found')
        return redirect('/workouts')
    
    if meta['teamId'] != athlete['teamId']:
        print(f"Cross-team access attempted by user {athlete['first']} {athlete['last']} on team:{athlete['teamId']}")
        return redirect('/workouts')

    if not isAdmin and int(workoutId) not in athlete['workouts']:
        print(f"Unauthorized access attempted by user {athlete['first']} {athlete['last']} on team:{athlete['teamId']}")
        return redirect('/workouts')




    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    js_resources = INLINE.render_js()
    css_resources = INLINE.render_css()

    seatnum = 0
    if isAdmin:
        startingview = overallView(workoutId)
        piece_list = list(zip(meta['piece_list'], list(range(len(meta['piece_list']))), [seatnum]*len(meta['piece_list'])))
    else:
        seatnum, startingview = myworkout(workoutId)
        startingview, piece_list = startingview
        

    totalspan = ""
    if isAdmin:
        for pieceIdx, piece in enumerate(meta['athlete_list']):
            spanner = '<span>Piece ' + str(pieceIdx+1) + ": </span>"
            for idx, athlet in enumerate(piece):
                spapender = ", </span>" if idx<7 else "</span>"
                spanner += '<span style=color:' +  colors[idx] + '>Seat ' +str(idx+1) + \
                    ": "+ athlet + spapender
            if pieceIdx > 0:
                totalspan += "<br>"
            totalspan += spanner
                

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
        seatnum = seatnum,
        athlete_map = totalspan
    )

    return html


@main_bp.route('/workoutoverall', methods = ['POST'])
@login_required
def overallView(internalId= None):
    # TODO: SEATRACING LOGIC. GROSS.
    npts = 100

    user = current_user

    # print(user)
    if internalId:
        workoutId = internalId
    else:
        workoutId = request.args.get('w')

    piece_num = request.args.get('piece')
    
    practice, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not practice:
        practice = queryWorkoutData(workoutId)
        meta = queryWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta

    if not piece_num:
        piece_num = '0'
    elite = practice['peach_data'][int(piece_num)]



    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']


    athDict = {}
    athleteMap = meta['athlete_list']
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

    
    ax = [None]* len(athleteMap[int(piece_num)])
    for i in range(len(athleteMap[int(piece_num)])):
        ax[i] = figure(background_fill_color="#fafafa")

    ax.append(figure(background_fill_color="#fafafa", sizing_mode="stretch_width"))


    stroke_nums = list(range(1, elite.numstrokes+1))

    average_aper_data = elite.get_average_aper_data()
    for peep in range(len(athleteMap[int(piece_num)])):
        theta3 = []
        thetadot3 = []
        for s in range(1, elite.numstrokes):
            dat3 = elite.resample_stroke(s, [0, peep+1,peep+1+8], npts)
            theta3 += [dat3[:,1]]
            thetadot3 += [dat3[:,2]]
        label = Label(x=np.min(theta3), y=np.min(thetadot3), x_units='data', y_units = 'data', 
        text='Average:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %
        (average_aper_data[1+peep],average_aper_data[17+peep], average_aper_data[33+peep], average_aper_data[121+peep]),
            border_line_color='black', border_line_alpha=.5,
            background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')

        ax[peep].multi_line(xs = theta3, ys = thetadot3, color=colors[peep],line_alpha = max(-0.001111*elite.numstrokes + 0.2722, .02), 
                            line_join = 'bevel', line_width = 2, legend_label=athleteMap[int(piece_num)][peep])
        ax[peep].xaxis.axis_label='Gate Angle °'
        ax[peep].yaxis.axis_label='Gate Force (N)'
        ax[peep].add_layout(label)
        ax[-1].line(x = stroke_nums, y = elite.aper_data[:,1+peep][:-1], line_color = colors[peep], line_join = 'bevel', line_width = 2, legend_label=athleteMap[int(piece_num)][peep])

    boat_pow = elite.get_boat_power()
    ax[-1].line(x = stroke_nums, y = boat_pow, line_join = 'bevel', line_width = 2, legend_label = "Average Boat Power")

    

    label = Label(x=elite.numstrokes//2-10, y=np.max(boat_pow), x_units='data', y_units = 'data', 
        text='Average Boat:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %
        (np.mean(average_aper_data[1:9]),np.mean(average_aper_data[17:25]), np.mean(average_aper_data[33:41]), np.mean(average_aper_data[121:129])),
            border_line_color='black', border_line_alpha=.5,
            background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')

    ax[-1].add_layout(label)
    ax[-1].legend.click_policy="hide"



    my_grid = layout([
        gridplot(children = ax[0:len(athleteMap[int(piece_num)])], ncols=4),
        ax[-1]
    ])

    # my_grid.sizing_mode = "scale_both"

    response = ""

    multi_piece = len(meta['piece_list']) > 1

    response = gen_overall_response(internalId, piece_num, meta, multi_piece)

    # render template
    script, div = components(my_grid)
    
    return response + '<div id = "overall">' + div+script + '<div>'



@main_bp.route('/workoutseat', methods = ['POST'])
@login_required
def workoutforseat():
    workoutId = request.args.get('w')
    seat_num = int(request.args.get('s'))

    piece_num = request.args.get('piece')
        

    if piece_num:
        piece_num = int(piece_num)
    else:
        piece_num = 0
    
    practice, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not practice:
        practice = queryWorkoutData(workoutId)
        meta = queryWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta
    athlete_name = meta['athlete_list'][piece_num][seat_num]

    elite = practice['peach_data'][piece_num]
    if request.args.get('ad') is None:
        athDict = {}
        athleteMap = meta['athlete_list']
        for pieceIdx in range(len(athleteMap)):
            for paidx, piece_athlete in enumerate(athleteMap[pieceIdx]):
                in_dict = athDict.get(piece_athlete,None)
                if in_dict is not None:
                    pl = in_dict
                    pl.append((pieceIdx, paidx))
                    athDict[piece_athlete] = pl
                else:
                    athDict[piece_athlete] = [(pieceIdx, paidx)]
            
        my_pieces = athDict[athlete_name]
        print(my_pieces)
        return individual_workout(elite, seat_num, meta, False, piece_num, my_pieces)[0]
    return individual_workout(elite, seat_num, meta, False, piece_num, None, True)[0]
    
     


""" display an individual's portal for workout """
@main_bp.route('/myworkout', methods=['GET'])
@login_required
def myworkout(internalId = None):
    # load the user 

    user = current_user
    # print(user)
    athlete = queryAthlete(user._id)

    if internalId:
        workoutId = internalId
    else:
        workoutId = request.args.get('w')
    
    practice, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not practice:
        practice = queryWorkoutData(workoutId)
        meta = queryWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta

    piece_num = request.args.get('piece')

    if not piece_num:
        piece_num = int(min(athlete['piecelist'][workoutId]))
    else:
        if int(piece_num) not in athlete['piecelist'][workoutId]:
            piece_num = int(min(athlete['piecelist'][workoutId]))
    elite = practice['peach_data'][int(piece_num)]
        
    athDict = {}
    athleteMap = meta['athlete_list']
    for pieceIdx in range(len(athleteMap)):
        for paidx, piece_athlete in enumerate(athleteMap[pieceIdx]):
            in_dict = athDict.get(piece_athlete,None)
            if in_dict is not None:
                pl = in_dict
                pl.append((pieceIdx, paidx))
                athDict[piece_athlete] = pl
            else:
                athDict[piece_athlete] = [(pieceIdx, paidx)]
        
    my_pieces = athDict[athlete['namestring']]
    print(my_pieces)
    if internalId:
        internal = True

    seat_num = meta['athlete_list'][int(piece_num)].index(athlete['namestring'])
    
    return seat_num, individual_workout(elite, seat_num, meta, internal, piece_num, my_pieces)



def individual_workout(elite, seat_num, meta, internal = False, piece_num = 0, piecers=None, ad=False):
    npts = 100

    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    ax, bx, cx, dx = generate_figs()

    analysis_pts = []


    theta3 = []
    thetadot3 = []
    time_resamp = []
    for s in range(1, elite.numstrokes):
        dat3 = elite.resample_stroke(s, [0, seat_num+1,seat_num+1+8], npts)
        time_resamp += [dat3[:,0]]
        theta3 += [dat3[:,1]]
        thetadot3 += [dat3[:,2]]
    
    average_aper_data = plot_superimposed(elite, seat_num, colors, ax, theta3, thetadot3)

    max_force_pct = average_aper_data[121+seat_num]

    early_build = True

    if max_force_pct <= 33:
        analysis_pts.append("Max Force Percentage is too early.")
    elif max_force_pct > 40:
        analysis_pts.append("Max Force Percentage is too late")
        analysis_pts.append("Try springing off the footplate at the catch")
        early_build = False
    else:
        analysis_pts.append("Max Force Percentage looks good!!.")

    svdDict = peachhelp.svd_module(elite, 100, seat_num)
    
    peachhelp.plot_vector(svdDict['mean'], label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery', ax=bx)

    sloppy_bladework, tail_off = peachhelp.plot_degree_velocity(svdDict['mean'], label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery', ax=dx)

    boat_svd = peachhelp.svd_module(elite, 100)

    peachhelp.plot_vector(boat_svd['mean'], color = "#ba34eb", label = 'Boat Mean Stroke', suppress_power=True, label2='Boat Mean Recovery', ax = bx)

    if seat_num !=7:
        stroke_svd = peachhelp.svd_module(elite, 100, 7)
        peachhelp.plot_vector(stroke_svd['mean'], color = "#30d93e", suppress_power=True, label2='Stroke Mean Recovery', ax = bx)



    mathDict = peachhelp.plot_single(svdDict['mean'], ax, color = "#FFA500", label= "Actual Stroke")

    polygons = []
    coordinates = mathDict['double_dip_coords']
    plot_double_dip(bx, polygons, coordinates)


    print(mathDict['work_first_half'])
    print(mathDict['work_second_half'])



    if early_build and coordinates and tail_off:
        analysis_pts.append("You are likely using too much body at the front end")
        analysis_pts.append("Try a quicker leg drive and push through the heels")
    elif early_build and tail_off:
        analysis_pts.append("Try to leverage your body better.")
        analysis_pts.append("Fully extend your hips late in the drive")
        analysis_pts.append("Gather more bend at the catch.")
        analysis_pts.append("Connect through the foot stretchers with your heels")
    elif early_build and not tail_off:
        analysis_pts.append("Nice work quickly acheiving and maintaining force!")

    sudden_accel = False

    late_placement = False

    if seat_num < 7:
        look_ahead_avg = np.mean(average_aper_data[41+seat_num+1:49])/200
        if look_ahead_avg-average_aper_data[41+seat_num] <= .01 or average_aper_data[41+7]- average_aper_data[41+seat_num] <= .01:
            late_placement = True




    late_prep = sudden_accel and late_placement

    if not early_build and late_prep:
        analysis_pts.append("You are likely lunging at the catch")
        analysis_pts.append("Try to prepare the body earlier.") 
        analysis_pts.append("Catch through your fingertips, not shoulders")
    if not early_build and not late_prep:
        analysis_pts.append("Get those legs down faster! ")
        analysis_pts.append("Try to focus on changing direction quicker.")


    if sloppy_bladework:
        analysis_pts.append("Your blade is entering before accelerating to stern")
        analysis_pts.append("Try not to \"pull\" the handle at the catch.")
        analysis_pts.append("Relax and elongate your upper body")


    x = [5]*len(analysis_pts)

    y = list(np.linspace(5,85,len(analysis_pts)))[::-1]



    source = ColumnDataSource(dict(x=x, y=y, text = analysis_pts))    

    title  = Text(x='x', y='y', text='text', text_color = '#00008b', text_font_size = "20px")

    dx[1].add_glyph(source, title)

    split = elite.get_rating_chunks()

    for idx, one_split in enumerate(split):
        plot_splits(elite, seat_num, cx, idx, one_split)


    ax[1].legend.click_policy = "hide"
    bx[1].legend.click_policy = "hide"
    cx[1].legend.click_policy = "hide"
    cx[0].legend.click_policy = "hide"

    my_grid = grid([
        [ax[0], ax[1], bx[0]],
        [bx[1], cx[0], cx[1]],
        [dx[0], dx[1], dx[2]]
    ])

    my_grid.sizing_mode = "scale_both"

    multi_piece = len(meta['piece_list']) > 1

    # TODO: only render the pieces that belong to this athlete
    piece_loop = []
    if piecers is None:
        piece_loop = list(zip(meta['piece_list'], list(range(len(meta['piece_list']))), [seat_num]*len(meta['piece_list'])))
    else:
        piece_loop = [(meta['piece_list'][pieceIdx], pieceIdx, seat_spot) for (pieceIdx, seat_spot) in piecers]


    response = gen_indv_response(seat_num, meta, internal, piece_num, multi_piece, piece_loop, ad)

    # render template
    script, div = components(my_grid)

    return (response + '<div id = "individual">' + div + script + "</div>", piece_loop)




@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
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

@main_bp.route('/team', methods=['GET', 'POST'])
@login_required
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
@login_required
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


#----------------------------------------------------------------------
"""Bokeh application"""
#----------------------------------------------------------------------


@main_bp.route('/splitpieces', methods = ['GET', 'POST'])
@login_required
def splitPieces():
    user = current_user
    if user.is_anonymous():
        return redirect('/login')
    
    if request.args.get('w'):
        unsplitId = int(request.args.get('w'))
    else:
        return render_template('error.html'), 500

    athleteId = user._id
    athlete = queryAthlete(athleteId)

    if 'admin' not in athlete['permissions'] and 'cox' not in athlete['permissions']:
        return render_template('error.html'), 500
     


    teamId = athlete['teamId']
        
    if os.environ.get('ENV') == 'PRODUCTION':   
        script = server_document('https://www.peachrow.net:%d/bkapp' % current_app._bokehport, arguments={"id": unsplitId, "teamId": teamId})
    else:
        script = server_document('http://localhost:%d/bkapp' % current_app._bokehport, arguments={"id": unsplitId, "teamId": teamId})
    
    
    return render_template("embed.html", script=script, template="Flask")


def gen_indv_response(seat_num, meta, internal, piece_num, multi_piece, piece_loop,ad):
    response = ""
    if not internal:
        if multi_piece:
            response = '<div id = "piecelist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
            for piece, num, s_num in piece_loop:
                response +=  '<li class="nav-item">'  
                response += '<button class="btn btn-outline-info'
                if num == piece_num:
                    response += ' active" role = "button" aria-pressed = "true'
                response +=  '" hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s=' 
                response += str(s_num) + '&piece=' + str(num)
                if ad:
                    response+= '&ad=1'
                response += '" hx-target = "#raw">' + str(piece) + '</button>' 
                response += '</li>'
            response += '</ul> </div>'
        response += '<div id = "seatlist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
        response +=  '<li class="nav-item">'  
        response += '<button class="btn btn-outline-primary'
        if multi_piece: 
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '&piece=' + str(piece_num) + '" hx-target = "#raw">' + "Overall View" + '</button>' 
        else:
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '" hx-target = "#raw">' + "Overall View" + '</button>' 
        response += '</li>'
        for num in range(8):
            response +=  '<li class="nav-item">'  
            response += '<button class="btn btn-outline-primary'
            if num == seat_num:
                response += ' active" role = "button" aria-pressed = "true'
            if not multi_piece:
                response +=  '" hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num)
                if ad:
                    response+= '&ad=1'
                response += '" hx-target = "#raw">' + "Seat " + str(num+1) + " Details" + '</button>'
            else:
                response +=  '" hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num) + '&piece=' + str(piece_num)
                if ad:
                    response+= '&ad=1'
                response += '" hx-target = "#raw">' + "Seat " + str(num+1) +  " Details" + '</button>' 
            response += '</li>'
        response += '</ul> </div>'
    return response

def plot_double_dip(bx, polygons, coordinates):
    for coordIdx in range(0,len(coordinates), 2):
        plotxs=[coordinates[coordIdx][0], coordinates[coordIdx][0], coordinates[coordIdx+1][0], coordinates[coordIdx+1][0]]
        plotys=[coordinates[coordIdx][1]-5, coordinates[coordIdx][1]+2, coordinates[coordIdx+1][1]+2, coordinates[coordIdx+1][1]-5]
        polygons += [(
            PolyAnnotation(
            fill_color="red",
            fill_alpha=0.3,
            xs=plotxs,
            ys = plotys
        ), 
        Label(
            x=coordinates[coordIdx][0],
         y=(coordinates[coordIdx][1] + coordinates[coordIdx+1][1] + 1)/2,
         angle = (plotys[2]-plotys[1])/(plotxs[2]-plotxs[1]), 
         x_units='data', y_units = 'data', 
         text='Disconnect')
         )]

    for polygon, polylabel in polygons:
        bx[0].add_layout(polygon)
        bx[0].add_layout(polylabel)

def generate_figs():
    ax = [None]*2
    ax[0] = figure(background_fill_color="#fafafa")
    ax[1] = figure(background_fill_color="#fafafa")
    bx = [None]*2
    bx[0] = figure(background_fill_color="#fafafa")
    bx[1] = figure(background_fill_color="#fafafa")


    cx = [None]*2
    cx[0] = figure(background_fill_color="#fafafa")
    cx[1] = figure(background_fill_color="#fafafa")


    dx = [None]*3
    dx[0] = figure(background_fill_color="#fafafa")
    dx[1] = figure(background_fill_color="#ffffff", x_range = Range1d(0,100), y_range = Range1d(0,100), tools =[])
    dx[2] = figure(background_fill_color="#fafafa")

    dx[1].xaxis.major_tick_line_color = None  
    dx[1].xaxis.minor_tick_line_color = None  
    dx[1].yaxis.major_tick_line_color = None  
    dx[1].yaxis.minor_tick_line_color = None  
    dx[1].xaxis.major_label_text_font_size = '0pt'  
    dx[1].yaxis.major_label_text_font_size = '0pt'  
    dx[1].outline_line_width = 7
    dx[1].outline_line_alpha = 0.3
    dx[1].outline_line_color = "navy"
    dx[1].grid.visible = False
    dx[1].xaxis.visible = False 
    dx[1].yaxis.visible = False 

    x = [39]
    y = [90]
    text = ["Analysis"]


    source = ColumnDataSource(dict(x=x, y=y, text = text))    

    title  = Text(x='x', y='y', text='text', text_color = '#00008b', text_font_size = "32px")

    dx[1].add_glyph(source, title)
    return ax,bx,cx,dx


def gen_overall_response(internalId, piece_num, meta, multi_piece):
    response = ""
    if not internalId:
        if multi_piece:
            response = '<div id = "piecelist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
            for num, piece in enumerate(meta['piece_list']):
                response +=  '<li class="nav-item">'  
                response += '<button class="btn btn-outline-info'
                if str(num) == piece_num:
                    response += ' active" role = "button" aria-pressed = "true'
                response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '&piece=' + str(num) + '" hx-target = "#raw">' + piece + '</button>' 
                response += '</li>'
            response += '</ul> </div>'

        
        response += '<div id = "seatlist" hx-swap-oob = "true"> <ul class="navbar-nav mr-auto">'
        response +=  '<li class="nav-item">'  
        response += '<button class="btn btn-outline-primary'
        response += ' active" role = "button" aria-pressed = "true'
        if multi_piece: 
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + '&piece=' + piece_num + 'ad=1" hx-target = "#raw">' + "Overall View" + '</button>' 
        else:
            response +=  '" hx-post= "/workoutoverall?w=' + str(meta['_id']) + 'ad=1" hx-target = "#raw">' + "Overall View" + '</button>' 
        response += '</li>'
        for num in range(8):
            response +=  '<li class="nav-item">'  
            response += '<button class="btn btn-outline-primary"'
            if not multi_piece:
                response +=  ' hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num) + 'ad=1" hx-target = "#raw">' + "Seat " + str(num+1) + " Details" + '</button>'
            else:
                response +=  ' hx-post= "/workoutseat?w=' + str(meta['_id']) + '&s='+str(num) + '&piece=' + piece_num + '&ad=1" hx-target = "#raw">' + "Seat " + str(num+1) +  " Details" + '</button>' 
            response += '</li>'
        response += '</ul> </div>'
    return response



def plot_splits(elite, seat_num, cx, idx, one_split):
    split_svd = peachhelp.svd_module(elite, 100, seat_num, (one_split[0], one_split[1]))
    peachhelp.plot_vector(split_svd['mean'], ax=cx, color=Oranges9[idx], legend_title = "Stroke over Time",
        label="Stroke %d-%d, avg s/m: %.1f, avg W: %.1fW" 
        %(one_split[0]+1, one_split[1]+1, 
        elite.get_average_aper_data(one_split)[129], 
        elite.get_average_aper_data(one_split)[1+seat_num]), 
        label2 = "Stroke %d-%d, avg Max Force: %.2f%%" 
        %(one_split[0]+1, one_split[1]+1, 
        elite.get_average_aper_data(one_split)[121+seat_num]))
    
    
def plot_superimposed(elite, seat_num, colors, ax, theta3, thetadot3):
    ax[0].multi_line(xs = theta3, ys = thetadot3, line_alpha = max(-0.001111*elite.numstrokes + 0.2722, .02), color=colors[seat_num], legend_label = 'All Strokes Superimposed', line_join = 'bevel', line_width = 2)
    ax[0].xaxis.axis_label='Gate Angle °'
    ax[0].yaxis.axis_label='Gate Force (N)'
    average_aper_data = elite.get_average_aper_data()
    label = Label(x=np.min(theta3), y=np.min(thetadot3), x_units='data', y_units = 'data', 
    text='Average:\nPower: %.2f N\nSlip: %.2f°\nWash: %.2f°\nMax Force: %.2f%%' %
    (average_aper_data[1+seat_num],average_aper_data[17+seat_num], average_aper_data[33+seat_num], average_aper_data[121+seat_num]),
        border_line_color='black', border_line_alpha=.5,
        background_fill_color='#fafafa', background_fill_alpha=0, text_color = '#0096FF')
    ax[0].add_layout(label)
    return average_aper_data
