from flask import Flask, request, make_response, redirect, url_for, Response
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
import xlsxMethods
from io import StringIO
from datetime import datetime
import mimetypes
import pickle
from bson.binary import Binary

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TEMPLATE_DIR = './templates'
STATIC_DIR = './static'

if 'secret_key' not in os.environ:
    from dotenv import load_dotenv
    load_dotenv()
    secret_key = os.environ.get('secret_key')
else:
    secret_key = os.environ['secret_key']

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

app.secret_key = secret_key
app.config['SECRET_KEY'] = app.secret_key

login_manager = flask_login.LoginManager()
login_manager.login_view = '/login'
login_manager.init_app(app)

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
    html = render_template('home.html', perms=athlete['permissions'], first=athlete['first'])
    return make_response(html)

@app.route('/howToUpload', methods=['GET'])
def howToUpload():
    html = render_template('howToUpload.html')
    return make_response(html)

#-----------------------------------------------------------------------
""" File upload and download methods """
#-----------------------------------------------------------------------

""" download a blank .xlsx file for recording a workout """
@flask_login.login_required
@app.route('/download')
def download():

    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
        
    user = user_loader(email)
    athleteId = user.id
    athlete = db.queryAthlete(athleteId)
    teamId = athlete['teamId']
    try:
        blankOutput = xlsxMethods.xlsxBlank(teamId)
        response = Response()
        response.data = blankOutput.read()
        response.status_code = 200
        file_name = 'workout_{}.xlsx'.format(datetime.now().strftime('%d/%m/%Y'))
        mimetype_tuple = mimetypes.guess_type(file_name)
        headers = {
            'Pragma': "public",  # required,
            'Expires': '0',
            'Cache-Control': 'must-revalidate, post-check=0, pre-check=0',
            'Cache-Control': 'private',  # required for certain browsers,
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'Content-Disposition': 'attachment; filename=\"%s\";' % file_name,
            'Content-Transfer-Encoding': 'binary',
            'Content-Length': len(response.data)
        }

        for k in headers:
            response.headers[k] = headers[k]

        if not mimetype_tuple[1] is None:
            response.update({
                'Content-Encoding': mimetype_tuple[1]
            })
        response.set_cookie('fileDownload', 'true', path='/')

        print(f'/download accessed by {athlete["first"]} {athlete["last"]}')

        return response
    except Exception as e:
        print(e, ' in download')

""" upload a .xlsx file for processing and storing in database """
@flask_login.login_required
@app.route('/upload', methods=["GET", 'POST'])
def upload():
    if 'user' not in session:
        return redirect('/login')
    else:
        email = session['user']
    user = user_loader(email)
    athleteId = user.id
    athlete = db.queryAthlete(athleteId)
    teamId = athlete['teamId']

    if request.method == "GET":
        return redirect('/home')

    file = request.files['sheet']

    try:
        success, workout = xlsxMethods.xlsxRead(file, teamId)
        if not success:
            message = urllib.parse.quote(workout)
            return redirect(f'/home?e=1&em={message}')

        addedId = db.addWorkout(workout, teamId)
        if not addedId:
            flash("failed to add workout")
        else:
            print(f'Sheet uploaded by {athlete["first"]} {athlete["last"]}. WorkoutId: {addedId}')

            if len(workout['athlete_list']) :
                for ath_idx, athlete in enumerate(workout['athlete_list']):
                    first, last = athlete.split() # TODO: this is dangerous!!!!!!
                    print()
                    athlete_query = db.queryAthleteByName(first, last, teamId) # TODO: check if working, then introduce fuzzy matching
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
            return redirect('workout?w={}'.format(addedId))
        
    except Exception as e:
        print(str(e), ' in upload')
        flash("There was an error uploading the file")
        return redirect('/home')

    

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
        if athlete['teamId'] != db.queryWorkout(workoutId)['teamId']:
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

    workout = db.queryWorkout(workoutId)
    html = render_template('confirmDelete.html', workout=workout, wid=workoutId, aid=athleteId)
    return make_response(html)


""" display a single workout """
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
    practice = db.queryWorkout(workoutId)

    results = practice['scores']
    notes = ", ".join([str(n) for n in practice['notes']])
    athletes = {}
    scoresDict = {}
    averages = {}

    bikeAthletes = {}
    bikeScores = {}
    bikeAverages = {}


    # for workout in results:
    #     athleteId = workout.athleteId
    #     ath = db.queryAthlete(athleteId)

    #     ad = {
    #         'first' : ath['first'],
    #         'last' : ath['last'],
    #         'side' : ath['side']
    #     }

    #     if hasattr(workout, 'mod'):
    #         if workout.mod == 'B': # if bike modifier, add them to bike athletes
    #             bikeAthletes[athleteId] = ad
    #             bikeScores[athleteId] = workout.split, workout.scores, workout.watts()
    #             bikeAverages[athleteId] = workout.split.strftime('%-M:%S.%f')[:-5]
    #         else:
    #             athletes[athleteId] = ad
    #             scoresDict[athleteId] = workout.split, workout.scores, workout.watts()
    #             averages[athleteId] = workout.split.strftime('%-M:%S.%f')[:-5]
    #     else:      
    #         athletes[athleteId] = ad
    #         scoresDict[athleteId] = workout.split, workout.scores, workout.watts()
    #         averages[athleteId] = workout.split.strftime('%-M:%S.%f')[:-5]


    # scoresDict_sorted = sorted(scoresDict.items(), key=lambda wo:wo[1][0])
    # bikeScores_sorted = sorted(scoresDict.items(), key=lambda wo:wo[1][0])

    # html = render_template('workout.html' , workout=practice, scores=scoresDict_sorted, athletes=athletes, averages=averages, bikeScores=bikeScores_sorted, bikeAthletes=bikeAthletes, bikeAverages=bikeAverages, isAdmin=isAdmin, athId=user.id)
    # return make_response(html)

    for workout in results:
        athleteId = workout.athleteId
        ath = db.queryAthlete(athleteId)
        athletes[athleteId] = {
            'first' : ath['first'],
            'last' : ath['last'],
            'side' : ath['side']
        }
        scoresDict[athleteId] = workout.split, workout.scores, workout.watts()
        averages[athleteId] = workout.split.strftime('%-M:%S.%f')[:-5]


    scoresDict_sorted = sorted(scoresDict.items(), key=lambda wo:wo[1][0])
    viewer = athlete['first'] + ' ' + athlete['last']

    html = render_template('workout.html' , workout=practice, scores=scoresDict_sorted, athletes=athletes, averages=averages, isAdmin=isAdmin, viewer=viewer)
    return make_response(html)


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
