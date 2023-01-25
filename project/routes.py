from bokeh.layouts import layout, grid, gridplot, row
from bokeh.embed import components, server_document
from bokeh.resources import INLINE
import os
from flask_login import current_user, login_required
from . import peachhelp
from flask import Blueprint, request, make_response, redirect, current_app
from flask import render_template, current_app
from .database import getAllAthletes, getAllWorkouts, queryWorkoutData, queryUnsplitMeta, editTeam
from .database import deleteWorkout, removeWorkoutFromAthlete, editAthlete, editWorkout, deleteUnsplit
from .database import getAllUnsplits, queryAthlete
from . import socketio, cache
import collections
from concurrent.futures import ThreadPoolExecutor
from .forms import TeamForm
from .middleman import getTeamInfo, getWorkoutMeta, getAthleteByName, getAthleteById

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
    if current_user.is_anonymous():
        print("anon!")
        return redirect('/login')
    athlete = getAthleteById(user._id)
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

    athlete = getAthleteById(user._id)
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
            if os.environ.get('ENV') == 'PRODUCTION':   
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
            if athlete['teamId'] != getWorkoutMeta(workoutId)['teamId']:
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
        workout = getWorkoutMeta(workoutId)
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
    athlete = getAthleteById(user._id)

    if 'admin' in athlete['permissions'] or 'cox' in athlete['permissions']:
        isAdmin = True
    else:
        isAdmin = False

    # print(athlete['permissions'])
    workoutId = request.args.get('w')
    _, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not meta:
        meta = getWorkoutMeta(workoutId)

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
        num_seats = range(len(meta['athlete_list'][0])),
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
        meta = getWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta

    if not piece_num:
        piece_num = '0'
    elite = practice['peach_data'][int(piece_num)]


    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    
    athleteMap = meta['athlete_list']

    ax = peachhelp.gen_overall_plots(piece_num, athleteMap)
    
    stroke_nums = list(range(1, elite.numstrokes+1))
    num_seats = len(athleteMap[int(piece_num)])
    average_aper_data = elite.get_average_aper_data()
    with ThreadPoolExecutor() as executor:
        seat_futures = [executor.submit(peachhelp.plot_individual, npts, piece_num, elite, colors, athleteMap, ax, stroke_nums, average_aper_data, peep) for peep in range(num_seats)]
        boat_future = executor.submit(peachhelp.plot_boat_pwrinfo, elite, ax, stroke_nums, average_aper_data)

    [f.result() for f in seat_futures]
    _ = boat_future.result()

    my_grid = layout([
        gridplot(children = ax[0:len(athleteMap[int(piece_num)])], ncols=4),
        ax[-1]
    ])

    multi_piece = len(meta['piece_list']) > 1

    response = peachhelp.gen_overall_response(elite.numseats, internalId, piece_num, meta, multi_piece)

    script, div = components(my_grid)
    
    return response + '<div id = "overall">' + div+script + '<div>'


@main_bp.route('/workoutoverallpieces', methods = ['POST'])
@login_required
def workoutoverallpieces():
    npts = 100

    workoutId = request.args.get('w')

    practice, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not practice:
        practice = queryWorkoutData(workoutId)
        meta = getWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta

    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    
    athleteMap = meta['athlete_list']
   
    athDict = peachhelp.gen_athlete_dict(meta['athlete_list'])  

    ax = peachhelp.gen_overall_plots_all_pieces(athDict.keys())
    
    data_table, data_table2 = peachhelp.generate_tables(npts, practice, colors, athleteMap, athDict, ax)

    my_grid = layout([
        gridplot(children = ax[0:len(athDict.keys())], ncols=4),
        data_table,
        data_table2
    ])
    
    
    script, div = components(my_grid)

    multi_piece = True

    response = peachhelp.gen_overall_response(len(athleteMap[0]), False, -1, meta, multi_piece)

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
        meta = getWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta
    checkIfTeam = getTeamInfo(meta['teamId'])
    
    athlete_name = meta['athlete_list'][piece_num][seat_num]
    athlete_db = getAthleteByName(athlete_name, meta['teamId'])
    renders = athlete_db['renders']
    elite = practice['peach_data'][piece_num]
    if request.args.get('ad') is None:
        athDict = peachhelp.gen_athlete_dict(meta['athlete_list'])
        my_pieces = athDict[athlete_name]
        return individual_workout(elite, renders, checkIfTeam['analysis'], seat_num, meta, False, piece_num, my_pieces)[0]
    return individual_workout(elite, renders, checkIfTeam['analysis'], seat_num, meta, False, piece_num, None, True)[0]

  
""" display an individual's portal for workout """
@main_bp.route('/myworkout', methods=['GET'])
@login_required
def myworkout(internalId = None):
    user = current_user
    # print(user)
    athlete = getAthleteById(user._id)

    if internalId is not None:
        workoutId = internalId
    else:
        workoutId = request.args.get('w')
    
    practice, meta = unpickledWorkouts.get(workoutId, (None, None))
    
    if not practice:
        practice = queryWorkoutData(workoutId)
        meta = getWorkoutMeta(workoutId)
        unpickledWorkouts[workoutId] = practice, meta
    checkIfTeam = getTeamInfo(meta['teamId'])

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
    
    return seat_num, individual_workout(elite, athlete['renders'], checkIfTeam['analysis'], seat_num, meta, internal, piece_num, my_pieces)



def individual_workout(elite, renders, analysis, seat_num, meta, internal = False, piece_num = 0, piecers=None, ad=False):
    npts = 100

    colors = ['#ffe119', '#3cb44b', '#f58231', '#dcbeff', '#800000', '#000075', '#a9a9a9', '#f032e6', '#aaffc3']

    ax, bx, cx, dx = peachhelp.generate_figs(analysis)
    average_aper_data = elite.get_average_aper_data()
    
    seatMean = peachhelp.mean_module(elite, 100, seat_num)
    
    
    with ThreadPoolExecutor() as executor:
    
        resamp_future = executor.submit(peachhelp.resample_and_superimposed, elite, renders, seat_num, npts, colors, ax, average_aper_data)
        mean_ideal_future = executor.submit(peachhelp.mean_and_ideal, seatMean, analysis, ax, bx, dx)
        
        if analysis:
            dips_late_future = executor.submit(peachhelp.dips_and_late, elite.numseats, seat_num, bx, average_aper_data, seatMean, elite)
            
        rec_mean_future = executor.submit(peachhelp.recovery_and_mean, elite, seat_num, bx)

        splits_future = executor.submit(peachhelp.splits, elite, seat_num, cx)



    _ = resamp_future.result()
    _ = rec_mean_future.result()
    _ = splits_future.result()
    
    if analysis:
        mathDict,sloppy_bladework,tail_off = mean_ideal_future.result()
        double_dips, late_placement = dips_late_future.result()

        early_build = True
        
        sudden_accel = False

        max_force_pct = average_aper_data[elite.max_force_percentage_idx]

        analysis_pts = peachhelp.tech_tree(early_build, max_force_pct, sloppy_bladework, tail_off,
                double_dips, sudden_accel, late_placement, mathDict['work_first_half'], mathDict['work_second_half'])

        peachhelp.render_analysis(dx, analysis_pts)


    ax[1].legend.click_policy = "hide"
    bx[1].legend.click_policy = "hide"
    cx[1].legend.click_policy = "hide"
    cx[0].legend.click_policy = "hide"

    if analysis:
        my_grid = grid([
            [ax[0], ax[1], bx[0]],
            [bx[1], cx[0], cx[1]],
            [dx[0], dx[1], dx[2]]
        ])
    else:
        my_grid = grid([
            [ax[0], ax[1], bx[0]],
            [bx[1], cx[0], cx[1]]
        ])
    my_grid.sizing_mode = "scale_both"

    multi_piece = len(meta['piece_list']) > 1

    # TODO: only render the pieces that belong to this athlete
    piece_loop = []
    if piecers is None:
        piece_loop = list(zip(meta['piece_list'], list(range(len(meta['piece_list']))), [seat_num]*len(meta['piece_list'])))
    else:
        piece_loop = [(meta['piece_list'][pieceIdx], pieceIdx, seat_spot) for (pieceIdx, seat_spot) in piecers]

    response = peachhelp.gen_indv_response(elite.numseats, seat_num, meta, internal, piece_num, multi_piece, piece_loop, ad)

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
        athlete = getAthleteById(athleteId)

        # security check: is the req'd athlete on the same team?
        viewerTeam = getAthleteById(user._id)['teamId']
        if viewerTeam != athlete['teamId']:
            return make_response(render_template('error.html'))

    # if no 'a', load the self's profile
    else:
        athleteId = user._id
        athlete = getAthleteById(athleteId)

    return render_template('profile.html', athlete=athlete)

@main_bp.route('/team', methods=['GET', 'POST'])
@login_required
def team():

    user = current_user
    if user.is_anonymous():
        return redirect('/login')
    # print(user)
    athleteId = user._id
    athlete = getAthleteById(athleteId)

    if 'admin' not in athlete['permissions']:
        return render_template('error.html'), 500




    teamId = athlete['teamId']
    teamInfo = getTeamInfo(teamId)
    teamName = teamInfo['name']
    teammates = getAllAthletes(teamId)
    athDict = {}
    athList = []
    for teammate in list(teammates):
        if 'class' not in teammate:
            classId = 0
        else:
            classId = int(teammate['class'])
        athlet = {'athleteId' : str(teammate['_id']), 'namestring': teammate['namestring'], 
                  'classId' : classId, 'side' : teammate['side'], 'active':teammate['active'], 
                  'permissions' : teammate['permissions'], 'renders': teammate['renders']}
        athDict[teammate['_id']] = athlet
        athList.append(athlet)
    print(teamInfo['analysis'])
    form = TeamForm(data = {'athletes':athList, 'analysis':teamInfo['analysis']})
    
    if form.validate_on_submit():
        for athlete in form.athletes.data:
            athlete.pop('csrf_token')
            if athDict[int(athlete['athleteId'])] != athlete:
                thisId = athlete.pop('athleteId')
                for field, val in athlete.items():
                    if athDict[int(thisId)][field] != val:
                        editAthlete(int(thisId), field, val)
                cache.delete_memoized(getAthleteById, athDict[int(thisId)])
                
        if form.analysis.data != teamInfo['analysis']:
            editTeam(teamId, 'analysis', form.analysis.data)
            cache.delete_memoized(getTeamInfo, teamId)
        return redirect('/team')

    html= render_template('team.html', form = form, teamId=teamId, teamName=teamName)
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
    athlete = getAthleteById(athleteId)

    if 'admin' not in athlete['permissions'] and 'cox' not in athlete['permissions']:
        return render_template('error.html'), 500
     


    teamId = athlete['teamId']
        
    if os.environ.get('ENV') == 'PRODUCTION':   
        script = server_document('https://www.peachrow.net:%d/bkapp' % current_app._bokehport, arguments={"id": unsplitId, "teamId": teamId})
    else:
        script = server_document('http://localhost:%d/bkapp' % current_app._bokehport, arguments={"id": unsplitId, "teamId": teamId})
    
    
    return render_template("embed.html", script=script, template="Flask")

