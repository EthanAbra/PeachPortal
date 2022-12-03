from . import database as db
from flask import Flask, Blueprint, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from flask_login import current_user, login_required, logout_user, login_user, UserMixin
from . import login_manager
import bcrypt
import random


# Blueprint Configuration
auth_bp = Blueprint(
    "auth_bp", __name__, template_folder="templates", static_folder="static"
)
#-----------------------------------------------------------------------
""" Authentication methods """
#-----------------------------------------------------------------------

""" renders the login page and processes user logins"""
@auth_bp.route('/login', methods=['GET', 'POST'])
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
                login_user(user)
                session.permanent = False
                res = redirect('/home')
                session['user'] = email
                print(f'{email} logged in, new session')
                return res
            else:
                error = 'Invalid Credentials. Please try again.'


    return render_template('login.html', error=error)

""" log out the user """
@login_required
@auth_bp.route('/logout')
def logout():
    logout_user()
    res = redirect('/')
    # set the email cookie to empty, make it expire 
    session.pop('user', None)
    return res


""" sign up a new user """
@auth_bp.route('/signup', methods=['GET', 'POST'])
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


@auth_bp.route('/register', methods=['GET', 'POST'])
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
""" flask_login methods """
#-----------------------------------------------------------------------

class User(UserMixin):
    pass

""" loads a user from the database, using their email as the key """
@login_manager.user_loader
def user_loader(email):
    creds = db.getCredentials(email)
    # print(creds)
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
    # print(creds)
    user = User()
    user.id = creds['_id']
    return user