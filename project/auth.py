from .database import getCredentials, queryAthleteByName, getCredentialsbyId, queryTeam, editCredentialsBatch
from .database import editCredentials, addAthlete, addTeam, addCredentialsJson, getAllAthletes

from flask import Flask, Blueprint, request, make_response, redirect, url_for, Response, current_app
from flask import render_template, Markup, flash, session, jsonify, abort
from flask_login import current_user, login_required, logout_user, login_user, UserMixin
from . import login_manager
import bcrypt
import random
import uuid
import certifi
from .models import User
from fuzzywuzzy import fuzz
from fuzzywuzzy import process


ca = certifi.where()

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

    # on form submission (POST request)
    if request.method == 'POST':
        # get email and password from form
        email = request.form['username']
        password = bytes(request.form['password'],'utf-8')
        # get the credentials 
        find_user = getCredentials(email)

        if User.login_valid(email, password):
            loguser = User(find_user["_id"], find_user["email"], find_user["pwHash"], find_user["salt"])
            login_user(loguser, force=True)
            print(f'{email} logged in, new session')
            # print(res)
            return redirect('/home')
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')



""" log out the user """
@login_required
@auth_bp.route('/logout')
def logout():
    logout_user()
    res = redirect('/')
    # set the email cookie to empty, make it expire 
    # session.pop('user', None)
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
        checkIfNewEmail = User.get_by_email(email)
        checkIfTeam = queryTeam(team)
        if checkIfNewEmail:
            error = 'Account already exists with this email'
        elif not checkIfTeam:
            error = f'No team exists with id: {team}'
        else:
            allAthletes = getAllAthletes(team)
            already_here = None
            for existingAthlete in allAthletes:
                if fuzz.token_sort_ratio(existingAthlete['namestring'], first + " " + last) >= 85:
                    already_here = existingAthlete
                    break
            if already_here: 
                already_cred = getCredentialsbyId(already_here["_id"])
                if already_cred["pwHash"] == "pwhash":
                    # temped cred, update the cred
                    count = 0

                    count += editCredentialsBatch(already_here["_id"], "email", email, "pwHash", pwhash, "salt", salt)
                    if count != 3:
                        error = 'failed to update user credentials'
                    print(f'New user updated: {first} {last}, email: {email}, {side} side, {team} team')
                    html = redirect('/home')
                    return make_response(html)
                else:
                    error = 'Account already exists for this user. Try another email'

            else: 

                newId = random.randint(10, 100000)
                already_id = getCredentialsbyId(newId)
                while already_id:
                    newId = random.randint(10, 100000)
                    already_id = getCredentialsbyId(newId)

                # add the login credentials to credentials DB
                add = User.register(email, pwhash, salt, newId)

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
                    "namestring": first+ " " + last,
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
                add = addAthlete(athlete)
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

        teamId = addTeam(name)

        print(f'New team added: {name}. id:{teamId}')

        html = render_template('signup.html', newTeam=True, teamId=teamId)
        return redirect(f'/signup?t={teamId}')

    html = render_template('register.html', error=error)
    return make_response(html)

#-----------------------------------------------------------------------
""" flask_login methods """
#-----------------------------------------------------------------------


""" loads the user using the 'email' cookie set during login"""
