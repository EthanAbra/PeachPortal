from bokeh.layouts import layout, grid, gridplot
from bokeh.embed import components, server_document
from bokeh.resources import INLINE
import os
from flask_login import current_user, login_required
from . import peachhelp
from flask import Blueprint, request, make_response, redirect, current_app
from flask import render_template, current_app
from .database import getAllAthletes, getAllWorkouts, queryAthlete, queryWorkoutData, queryTeam, queryUnsplitMeta
from .database import queryWorkoutMeta, deleteWorkout, removeWorkoutFromAthlete, editAthlete, editWorkout, deleteUnsplit
from .database import getAllUnsplits
import numpy as np
from . import socketio
import collections

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
    _, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not meta:
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
        totalspan = peachhelp.athlete_span(meta['athlete_list'], colors)
                

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
    npts = 100

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

    
    ax = peachhelp.gen_overall_plots(piece_num, athleteMap)

    stroke_nums = list(range(1, elite.numstrokes+1))

    average_aper_data = elite.get_average_aper_data()
    for peep in range(len(athleteMap[int(piece_num)])):
        theta3 = []
        thetadot3 = []
        for s in range(1, elite.numstrokes):
            dat3 = elite.resample_stroke(s, [0, peep+1,peep+1+8], npts)
            theta3 += [dat3[:,1]]
            thetadot3 += [dat3[:,2]]
        
        peachhelp.plot_superimposed(average_aper_data, elite.numstrokes, peep, colors, ax, theta3, thetadot3, peep)        
        ax[-1].line(x = stroke_nums, y = elite.aper_data[:,1+peep][:-1], line_color = colors[peep], line_join = 'bevel', line_width = 2, legend_label=athleteMap[int(piece_num)][peep])

    boat_pow = elite.get_boat_power()
    peachhelp.plot_boat_pwrinfo(elite, ax, stroke_nums, average_aper_data, boat_pow)

    my_grid = layout([
        gridplot(children = ax[0:len(athleteMap[int(piece_num)])], ncols=4),
        ax[-1]
    ])

    multi_piece = len(meta['piece_list']) > 1

    response = peachhelp.gen_overall_response(internalId, piece_num, meta, multi_piece)

    script, div = components(my_grid)
    
    return response + '<div id = "overall">' + div+script + '<div>'



@main_bp.route('/workoutseat', methods = ['POST'])
@login_required
def workoutforseat():
    workoutId = request.args.get('w')
    seat_num = int(request.args.get('s'))

    piece_num = request.args.get('piece')
        

    if piece_num is not None:
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
        athDict = peachhelp.gen_athlete_dict(meta['athlete_list'])
        my_pieces = athDict[athlete_name]
        return individual_workout(elite, seat_num, meta, False, piece_num, my_pieces)[0]
    return individual_workout(elite, seat_num, meta, False, piece_num, None, True)[0]

  
""" display an individual's portal for workout """
@main_bp.route('/myworkout', methods=['GET'])
@login_required
def myworkout(internalId = None):
    user = current_user
    # print(user)
    athlete = queryAthlete(user._id)

    if internalId is not None:
        workoutId = internalId
    else:
        workoutId = request.args.get('w')
    
    practice, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not practice:
        practice = queryWorkoutData(workoutId)
        meta = queryWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta

    piece_num = request.args.get('piece')

    if piece_num is None:
        piece_num = int(min(athlete['piecelist'][workoutId]))
    else:
        if int(piece_num) not in athlete['piecelist'][workoutId]:
            piece_num = int(min(athlete['piecelist'][workoutId]))
    elite = practice['peach_data'][int(piece_num)]
        
    athDict = peachhelp.gen_athlete_dict(meta['athlete_list'])
        
    my_pieces = athDict[athlete['namestring']]
    if internalId:
        internal = True

    seat_num = meta['athlete_list'][int(piece_num)].index(athlete['namestring'])
    
    return seat_num, individual_workout(elite, seat_num, meta, internal, piece_num, my_pieces)



def individual_workout(elite, seat_num, meta, internal = False, piece_num = 0, piecers=None, ad=False):
    npts = 100

    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    ax, bx, cx, dx = peachhelp.generate_figs()

    theta3 = []
    thetadot3 = []
    time_resamp = []
    for s in range(1, elite.numstrokes):
        dat3 = elite.resample_stroke(s, [0, seat_num+1,seat_num+1+8], npts)
        time_resamp += [dat3[:,0]]
        theta3 += [dat3[:,1]]
        thetadot3 += [dat3[:,2]]
    
    average_aper_data = elite.get_average_aper_data()
    num_strokes = elite.numstrokes
    peachhelp.plot_superimposed(average_aper_data, num_strokes, seat_num, colors, ax, theta3, thetadot3)

    max_force_pct = average_aper_data[121+seat_num]

    seatMean = peachhelp.mean_module(elite, 100, seat_num)
    
    peachhelp.plot_vector(seatMean, label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery', ax=bx)

    sloppy_bladework, tail_off = peachhelp.plot_degree_velocity(seatMean, label= 'Overall Mean Stroke', label2 = 'Overall Mean Recovery', ax=dx)

    boat_mean = peachhelp.mean_module(elite, 100)

    peachhelp.plot_vector(boat_mean, color = "#ba34eb", label = 'Boat Mean Stroke', suppress_power=True, label2='Boat Mean Recovery', ax = bx)

    if seat_num !=7: # if not stroke seat
        stroke_mean = peachhelp.mean_module(elite, 100, 7)
        peachhelp.plot_vector(stroke_mean, color = "#30d93e", suppress_power=True, label2='Stroke Mean Recovery', ax = bx)


    mathDict = peachhelp.plot_single(seatMean, ax, color = "#FFA500", label= "Actual Stroke")

    double_dips = mathDict['double_dip_coords']
    peachhelp.plot_double_dip(bx, double_dips)

    split = elite.get_rating_chunks()

    for idx, one_split in enumerate(split):
        peachhelp.plot_splits(elite, seat_num, cx, idx, one_split)
        
    sudden_accel = False
    late_placement = False

    if seat_num < 7:
        look_ahead_avg = np.mean(average_aper_data[41+seat_num+1:49])/200 # all seats ahead of seat_num catch time
        if look_ahead_avg-average_aper_data[41+seat_num] <= .01 or average_aper_data[41+7]- average_aper_data[41+seat_num] <= .01:
            late_placement = True

        
    work_first = ['work_first_half']
    work_second = mathDict['work_second_half']

    early_build = True

    analysis_pts = peachhelp.tech_tree(early_build, max_force_pct, sloppy_bladework, tail_off,
              double_dips, sudden_accel, late_placement, work_first, work_second)


    peachhelp.render_analysis(dx, analysis_pts)


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

    response = peachhelp.gen_indv_response(seat_num, meta, internal, piece_num, multi_piece, piece_loop, ad)

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
    athDict = {}
    for teammate in list(teammates):
        athDict[teammate['_id']] = teammate
    sumModified = 0
    
    if request.method == 'POST':
        postDict = {}
        for key in list(request.form):
            newVal = request.form[key]
            field, athleteId = key.split('_')
            if field == 'active':
                if newVal == "none":
                    newVal = False
                else:
                    newVal = True
            elif newVal == "none":
                continue
            oldDict = postDict.get(athleteId, {'permissions':[]})
            if field == "cox" or field == "admin":
                oldPerms = oldDict.get('permissions')
                oldPerms.append(field)
                oldDict['permissions'] = oldPerms               
            else:
                oldDict[field] = request.form[key]
            postDict[athleteId] = oldDict
        for thisId, post_athDict in postDict.items():
            for field, val in post_athDict.items():
                if athDict[int(thisId)][field] != val:
                    sumModified += editAthlete(int(thisId), field, val)
        if sumModified >0 :
            return redirect('/team')
                
                        


        print(f'Team "{teamName}" edited by {athlete["first"]} {athlete["last"]}')
    html= render_template('team.html', athletes=teammates.rewind(), teamName=teamName)
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

