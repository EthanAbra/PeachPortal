from gevent import monkey
monkey.patch_all()

from flask import Flask, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash, gen_salt
import flask_login
import requests
import os
import urllib3
import urllib
import database as db
import random
import bcrypt
import peachhelp
from xlsxMethods import xlsxRead
from io import StringIO
from datetime import datetime
import mimetypes
import pickle
from bson.binary import Binary
import io
import base64
import numpy as np
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
import uuid
from flask_socketio import SocketIO, emit
from threading import Lock, Thread
import time
import polyfile

from engineio.payload import Payload

Payload.max_decode_packets = 500

class ThreadWithReturnValue(Thread):
    
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                                **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TEMPLATE_DIR = './templates'
STATIC_DIR = './static'

if 'secret_key' not in os.environ:
    from dotenv import load_dotenv
    load_dotenv()
    secret_key = os.environ.get('secret_key')
else:
    secret_key = os.environ['secret_key']



thread = None
thread_lock = Lock()
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

global message_queue
message_queue = []

app.secret_key = secret_key
app.config['SECRET_KEY'] = app.secret_key

app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024* 20

login_manager = flask_login.LoginManager()
login_manager.login_view = '/login'
login_manager.init_app(app)

socketio = SocketIO(app, async_mode = "gevent", cors_allowed_origins='*', manage_session=False, always_connect = True)


class User(flask_login.UserMixin):
    pass


#-----------------------------------------------------------------------
""" flask_login methods """
#-----------------------------------------------------------------------

""" loads a user from the database, using their email as the key """
@login_manager.user_loader
def user_loader(email):
    creds = db.getCredentials(email)
    if not creds:
        return

    user = User()
    user.id = creds['_id']

    return user

""" loads the user using the 'email' cookie set during login"""
@login_manager.request_loader
def request_loader(request):
    if 'user' not in session:
        return
    else:
        email = session['user']

    creds = db.getCredentials(email)
    user = User()
    user.id = creds['_id']
    
    return user


#-----------------------------------------------------------------------
""" Static page rendering """
#-----------------------------------------------------------------------

""" renders the index page """
@app.route('/', methods=['GET'])
def index():
    html = render_template('index.html')
    return make_response(html)

""" renders the about page """
@app.route('/about', methods=['GET'])
def about():
    html = render_template('about.html')
    return make_response(html)

""" renders the home page """
@flask_login.login_required
@app.route('/home', methods=['GET'])
def home():
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athlete = db.queryAthlete(user.id)
    html = render_template('home.html', perms=athlete['permissions'], first=athlete['first'], async_mode=socketio.async_mode)
    return make_response(html)

@app.route('/howToUpload', methods=['GET'])
def howToUpload():
    html = render_template('howToUpload.html')
    return make_response(html)

#-----------------------------------------------------------------------
""" File upload method"""
#-----------------------------------------------------------------------
@socketio.on('start-transfer')
def start_transfer(filename, size):
    """Process an upload request from the client."""
    _, ext = os.path.splitext(filename)
    if ext in ['.exe', '.bin', '.js', '.sh', '.py', '.php']:
        return False  # reject the upload

    id = uuid.uuid4().hex  # server-side filename
    with open( id + ext, 'wb') as f:
        pass
    return id + ext  # allow the upload


@socketio.on('write-chunk')
def write_chunk(filename, offset, data):
    """Write a chunk of data sent by the client."""
    if not os.path.exists(filename):
        return False
    try:
        with open( filename, 'r+b') as f:
            f.seek(offset)
            f.write(data)
    except IOError:
        return False
    return True

@socketio.on('write-complete')
def write_complete(filename):
    print("revced wr comp")
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athleteId = user.id
    athlete = db.queryAthlete(athleteId)
    teamId = athlete['teamId']

    def mimewrap(filename):
        for match in MagicMatcher.DEFAULT_INSTANCE.match(filename):
            print(f"Match string: {match!s}")
            if str(match).startswith("Microsoft Excel"):
                return True


    
    if not mimewrap(filename):
        os.remove(filename)
        return False
    # file = open(filename, 'r')
    success, workout = xlsxRead(filename, teamId)

    if not success:
        os.remove(filename)
        return False

    addedId = db.addWorkout(workout, teamId)
    os.remove(filename)
    if not addedId:
        return False
    else:
        print(f'Sheet uploaded by {athlete["first"]} {athlete["last"]}. WorkoutId: {addedId}')
    return True, addedId, teamId, workout['athlete_list']


    
    
@socketio.on('valid-athletes')
def valid_athletes(addedId, teamId, athleteList):
    if len(athleteList) :
        for ath_idx, athlete in enumerate(athleteList):
            if len(athlete.split())==1:
                first, last = athlete[0], athlete[0]
            else:
                first, last = athlete.split() # TODO: this is dangerous!!!!!!
            # print()
            athlete_query = db.queryAthleteByName(first, last, teamId) # TODO: introduce fuzzy matching
            if athlete_query:
                athleteId = athlete_query['_id']
                print(f'attributed to {athlete}', end='\r')

                edited = db.addWorkoutToAthlete(athleteId, addedId)
            else: # we need to create a new athlete for this individual

                error = ''
                newId = random.randint(10, 100000)
                # add the login credentials to credentials DB
                add = db.addCredentials(newId, athlete, "pwhash", "salt")
                if not add:
                    error += 'failed to add user cred'

                # create athlete document from entered info
                permissions = ['']
                # if 'admin' in request.form.keys():
                #     permissions.append('admin')
                side = 'starboard'
                if ath_idx % 2:
                    side = 'port'

                athlete = {
                    "_id" : newId,
                    "first" : first,
                    "last" : last,
                    "permissions" : permissions,
                    "workouts" : [addedId],
                    "side" : side,
                    "active" : True,
                    "teamId" : teamId
                }
                # add athlete document to athlete db
                add = db.addAthlete(athlete)
                if not add:
                    error += "failed to add athlete"
                
                if len(error):
                    return redirect(f'/home?e=1&em={error}')

                print(f'attributed to {athlete}', end='\r')
                # edited = db.addWorkoutToAthlete(add, addedId)
        return True
    else:
        db.deleteWorkout(addedId)
        return False

    

#-----------------------------------------------------------------------
""" Authentication methods """
#-----------------------------------------------------------------------

""" renders the login page and processes user logins"""
@app.route('/login', methods=['GET', 'POST'])
def login():
    error=''

    # if the user has already logged in (and has not logged out)
    # sign them in
    if 'user' in session:
        email = session['user'] 
        user = user_loader(email)
        athlete = db.queryAthlete(user.id)
        print(f'{athlete["first"]} {athlete["last"]} logged in, old session')
        return redirect('/home')


    # on form submission (POST request)
    if request.method == 'POST':

        # get email and password from form
        email = request.form['username']
        password = bytes(request.form['password'],'utf-8')
        # get the credentials 
        creds = db.getCredentials(email)

        session.clear()

        # getCredentials returns none if email not found in DB
        if not creds:
            error = 'Invalid Credentials. Please try again.'
        # else check password hash
        else:

            email = creds['email']
            pwHash = creds['pwHash']
            salt = creds['salt']
            # check the entered password against that in database
            verified = bcrypt.checkpw(password, pwHash)
            if verified:
                user = user_loader(email)
                flask_login.login_user(user)
                session.permanent = False
                res = redirect('/home')
                session['user'] = email
                print(f'{email} logged in, new session')
                return res
            else:
                error = 'Invalid Credentials. Please try again.'


    return render_template('login.html', error=error)

""" log out the user """
@flask_login.login_required
@app.route('/logout')
def logout():
    flask_login.logout_user()
    res = redirect('/')
    # set the email cookie to empty, make it expire 
    session.pop('user', None)
    return res


""" sign up a new user """
@app.route('/signup', methods=['GET', 'POST'])
def signup():

    error = ''
    # on form submission
    if request.method =='POST':
        # get form inputs 
        first = request.form['first'].capitalize()
        last = request.form['last'].capitalize()
        email = request.form['username']
        password = bytes(request.form['password'], 'utf-8')
        classYr = request.form['class']
        side = request.form['side']

        team = request.args.get('t')
        if not team:
            team = request.form['team']

        salt = bcrypt.gensalt()
        pwhash = bcrypt.hashpw(password, salt)

        # check if this email is already in database
        checkIfNewEmail = db.getCredentials(email)
        checkIfTeam = db.queryTeam(team)
        if checkIfNewEmail:
            error = 'Account already exists with this email'
        elif not checkIfTeam:
            error = f'No team exists with id: {team}'
        else:
            already_here = db.queryAthleteByName(first, last, team)
            if already_here: 
                already_cred = db.getCredentialsbyId(already_here["_id"])
                if already_cred["pwHash"] == "pwhash":
                    # temped cred, update the cred
                    count = 0
                    count += db.editCredentials(already_here["_id"], "email", email)
                    count += db.editCredentials(already_here["_id"], "pwHash", pwhash)
                    count += db.editCredentials(already_here["_id"], "salt", salt)
                    if count != 3:
                        error = 'failed to update user credentials'


                    print(f'New user updated: {first} {last}, email: {email}, {side} side, {team} team')
                    html = redirect('/home')
                    return make_response(html)
                else:
                    error = 'Account already exists for this user. Try another email'

            else: 

                newId = random.randint(10, 100000)
                already_id = db.getCredentialsbyId(newId)
                while already_id:
                    newId = random.randint(10, 100000)
                    already_id = db.getCredentialsbyId(newId)

                # add the login credentials to credentials DB
                add = db.addCredentials(newId, email, pwhash, salt)
                if not add:
                    error = 'failed to add user'

                # create athlete document from entered info
                permissions = ['']
                if side == 'cox':
                    permissions.append('cox')

                # if 'admin' in request.form.keys():
                #     permissions.append('admin')

                athlete = {
                    "_id" : newId,
                    "first" : first,
                    "last" : last,
                    "permissions" : permissions,
                    "prs" : {
                        "2000m" : '-1',
                        "6000m" : '-1'
                    },
                    "workouts" : [],
                    "side" : side,
                    "class" : classYr,
                    "active" : True,
                    "teamId" : team
                }
                # add athlete document to athlete db
                add = db.addAthlete(athlete)
                if not add:
                    error = "failed to add user"


                print(f'New user registered: {first} {last}, email: {email}, {side} side, {team} team')

                html = redirect('/home')
                return make_response(html)
    teamId = request.args.get('t')
    if teamId:
        html = render_template('signup.html', newTeam=True, error=error, teamId=teamId)
    else:
        html = render_template('signup.html', newTeam=False, error=error)
    return make_response(html)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = ''
    if request.method == 'POST':
        name = request.form['teamName'].capitalize()

        teamId = db.addTeam(name)

        print(f'New team added: {name}. id:{teamId}')

        html = render_template('signup.html', newTeam=True, teamId=teamId)
        return redirect(f'/signup?t={teamId}')

    html = render_template('register.html', error=error)
    return make_response(html)


#-----------------------------------------------------------------------
""" data-based page rendering """
#-----------------------------------------------------------------------

""" display all workouts """
@flask_login.login_required
@app.route('/workouts', methods=['GET'])
def workouts():
    # load the user
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athlete = db.queryAthlete(user.id)

    workouts = db.getAllWorkouts(athlete['teamId'])
    
    if 'cox' in athlete['permissions'] or 'admin' in athlete['permissions']:
        delPerm = True
    else:
        delPerm = False

    
    html = render_template('workouts.html' ,workouts=workouts, delPerm=delPerm, athId=athlete['_id'])
    return make_response(html)

@flask_login.login_required
@app.route('/deleteWorkout', methods=['GET', 'POST'])
def delete():
    # load the user
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athlete = db.queryAthlete(user.id)

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
        if athlete['teamId'] != db.queryWorkoutMeta(workoutId)['teamId']:
            print(f"Cross-team delete attempted by user {athlete['first']} {athlete['last']} on team:{athlete['teamId']}")
            return render_template('error.html'), 500
        
        deleted = db.deleteWorkout(workoutId)


        if deleted:
            ctr = 0
            for athlete in db.getAllAthletes(athlete['teamId']):
                res = db.removeWorkoutFromAthlete(athlete['_id'], workoutId)
                print(f'unattributing {workoutId} from {athlete["_id"]}', end='\r')
                ctr += 1
            print(f'workout {workoutId} deleted, removed from {ctr} profiles')
            return redirect('/workouts')

    workout = db.queryWorkoutMeta(workoutId)
    html = render_template('confirmDelete.html', workout=workout, wid=workoutId, aid=athleteId)
    return make_response(html)


""" display a coach/coxswain portal for workout """
@flask_login.login_required
@app.route('/workout', methods=['GET'])
def workout():
    # load the user 
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athlete = db.queryAthlete(user.id)

    if 'admin' in athlete['permissions']:
        isAdmin = True
    else:
        isAdmin = False

    workoutId = request.args.get('w')
    

    if 'cox' not in athlete['permissions']:
        return redirect(f'/myworkout?w={workoutId}')

    practice = db.queryWorkoutData(workoutId)

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
@flask_login.login_required
@app.route('/myworkout', methods=['GET'])
def myworkout():
    # load the user 
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athlete = db.queryAthlete(user.id)

    workoutId = request.args.get('w')
    

    practice = db.queryWorkoutData(workoutId)

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


@flask_login.login_required
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)

    # if loading another athlete, pass in the id as 'a'
    if request.args.get('a'):
        athleteId = request.args.get('a')
        athlete = db.queryAthlete(athleteId)

        # security check: is the req'd athlete on the same team?
        viewerTeam = db.queryAthlete(user.id)['teamId']
        if viewerTeam != athlete['teamId']:
            return make_response(render_template('error.html'))

    # if no 'a', load the self's profile
    else:
        athleteId = user.id
        athlete = db.queryAthlete(athleteId)

    return render_template('profile.html', athlete=athlete)

@flask_login.login_required
@app.route('/team', methods=['GET', 'POST'])
def team():
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athleteId = user.id
    athlete = db.queryAthlete(athleteId)

    if 'admin' not in athlete['permissions']:
        return render_template('error.html'), 500



    teamId = athlete['teamId']
    teamName = db.queryTeam(teamId)['name']
    teammates = db.getAllAthletes(teamId)

    sumModified = 0
    if request.method == 'POST':
        for key in list(request.form):
            field, athleteId = key.split('_')
            newVal = request.form[key]
            if field == 'active':
                sumModified += db.editAthlete(int(athleteId), field, True)
            else:
                sumModified += db.editAthlete(int(athleteId), field, newVal)

            if 'active' not in request.form:
                sumModified += db.editAthlete(int(athleteId), 'active', False)

    print(f'Team "{teamName}" edited by {athlete["first"]} {athlete["last"]}')

    html= render_template('team.html', athletes=teammates, teamName=teamName)
    return make_response(html)


#-----------------------------------------------------------------------
""" database edit routes """
#-----------------------------------------------------------------------
@app.route('/editWorkout', methods=['POST'])
def editWorkout():

    field = request.form['field']
    newVal = request.form['newVal']
    workoutID = int(request.form['workoutId'])

    res = db.editWorkout(workoutID, field, newVal)

    print(res, f' workout {workoutID} edited fied {field} with {newVal}')

    return redirect(f'/workout?w={workoutID}')



#-----------------------------------------------------------------------
""" Error handling """
#-----------------------------------------------------------------------

@app.errorhandler(404)
@app.errorhandler(500)
def handleError(ex):

    html = render_template('error.html')
    response = make_response(html)
    return response


#-----------------------------------------------------------------------
""" other and testing """
#-----------------------------------------------------------------------

@app.route('/allWorkouts', methods=['GET'])
def allWorkouts():
    wo = db.getAllWorkouts()
    html = ''
    for w in wo:
        html += str(w) +"\n"
    return make_response(html)

@app.route('/allAthletes', methods=['GET'])
def allAthletes():
    ath = db.getAllAthletes()
    html = ''
    for a in ath:
        html += str(a) + '\n'
    return make_response(html)


if __name__ == '__main__':
    socketio.run(app, port=8000, host='0.0.0.0', debug=True)
    print('socket io start')