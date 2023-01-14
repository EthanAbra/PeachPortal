from .database import getCredentials, getCredentialsbyId, queryTeam, editCredentialsPassword
from .database import addAthlete, addTeam, getAllAthletes, queryAthlete, editCredentialsBatch
from datetime import timedelta
from flask import Blueprint, request, make_response, redirect, url_for, current_app
from flask import render_template, flash
from flask_login import login_required, logout_user, login_user
from . import mail
import bcrypt
import random
import certifi
from .models import User
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from flask_mail import Message
from threading import Thread
import os
from .forms import LoginForm, SignupForm, RegisterForm


ca = certifi.where()

# Blueprint Configuration
auth_bp = Blueprint(
    "auth_bp", __name__, template_folder="templates", static_folder="static"
)
#-----------------------------------------------------------------------
""" Authentication methods """
#-----------------------------------------------------------------------

def send_email(app, msg):
    with app.app_context():
        if os.environ.get('ENV') == 'PRODUCTION':
            mail.send(msg)
        pass

""" renders the login page and processes user logins"""
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit() and getCredentials(form.email.data) is not None:
        print('validated')
        find_user = getCredentials(form.email.data)
        loguser = User(find_user["_id"], find_user["email"], find_user["pwHash"], find_user["salt"])
        login_user(loguser, force=True, duration=timedelta(hours=2))
        print(f'{form.email.data} logged in, new session')
        return redirect('/home')
    return render_template('login.html', form = form)



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
    form = SignupForm()
    # on form submission
    if form.validate_on_submit():
        # get form inputs 
        first = form.first.data.capitalize()
        last = form.last.data.capitalize()
        email = form.email.data
        password = form.password.data.encode('utf-8')
        classYr = form.classId.data
        side = form.side.data
        team = request.args.get('t')
        if not team:
            team = form.teamId.data

        salt = bcrypt.gensalt()
        pwhash = bcrypt.hashpw(password, salt)

        # check if this email is already in database
        checkIfNewEmail = User.get_by_email(email)
        checkIfTeam = queryTeam(team)
        if checkIfNewEmail:
            flash('Account already exists with this email')
        elif not checkIfTeam:
            flash(f'No team exists with id: {team}')
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
                        print('failed to update user credentials')
                        flash('failed. please try again')
                    else:
                        print(f'New user updated: {first} {last}, email: {email}, {side} side, {team} team')
                        html = redirect('/home')
                        return make_response(html)
                else:
                    flash('Account already exists for this user. Try another email')

            else: 
                newId = random.randint(10, 100000)
                already_id = getCredentialsbyId(newId)
                while already_id:
                    newId = random.randint(10, 100000)
                    already_id = getCredentialsbyId(newId)

                # add the login credentials to credentials DB
                add = User.register(newId, email, pwhash, salt)

                if not add:
                    flash('failed to add user')
                else:
                    # create athlete document from entered info

                    athlete = {
                        "_id" : newId,
                        "first" : first,
                        "last" : last,
                        "namestring": first+ " " + last,
                        "permissions" : [],
                        "workouts" : [],
                        "side" : side,
                        "class" : classYr,
                        "active" : True,
                        "teamId" : int(team)
                    }
                    
                    # add athlete document to athlete db
                    add = addAthlete(athlete)
                    if not add:
                        flash("failed to add user")
                    else:
                        print(f'New user registered: {first} {last}, email: {email}, {side} side, {team} team')
                        html = redirect('/home')
                        return make_response(html)
    teamId = request.args.get('t')
    if teamId:
        form.teamId.data = int(teamId)
    html = render_template('signup.html', form = form)
    return make_response(html)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.teamName.data.capitalize()

        teamId = addTeam(name)

        print(f'New team added: {name}. id:{teamId}')
        signupForm = SignupForm()
        signupForm.teamId.data = teamId
        html = render_template('signup.html', form = signupForm, newTeam=True, teamId=teamId)
        return redirect(f'/signup?t={teamId}')

    html = render_template('register.html', form=form)
    return make_response(html)


@auth_bp.route('/forgotpassword', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['username']

        checkIfNewEmail = User.get_by_email(email)

        if checkIfNewEmail is not None:
            athlete = queryAthlete(checkIfNewEmail._id)
            token = checkIfNewEmail.get_reset_token()
            print(f'Forgot password for {email}')
            msg = Message()
            msg.subject = "[PeachPortal] Password Reset Link (expires in 24 hours)"
            msg.recipients = [email]
            msg.sender = 'noreply@mail.peachrow.net'
            msg.body = ''
            reset_url = url_for('auth_bp.new_password', email=email, token=token, _external=True)
            msg.html = render_template('forgotpasswordemail.html', first = athlete['first'], reset_url = reset_url)
            msg.attach('peach.png','image/png', open(os.path.join(os.getcwd(), 'static/peach.png'), 'rb').read(),
                       'inline', headers=[['Content-ID','<PeachLogo>'],])
            Thread(target=send_email, args=(current_app._get_current_object(), msg)).start()

        flash("Recovery email sent if email is in our database. Don't forget to check spam")

    html = render_template('forgotpassword.html')
    return make_response(html)    


@auth_bp.route('/resetverified', methods=['GET', 'POST'])
def new_password():
    token = request.args.get('token')
    email = request.args.get('email')


    if request.method == 'POST':
        token = request.form['token']
        new_password = bytes(request.form['pass'], 'utf-8')
        user = User.verify_reset_token(token)

        if user is not None:

            salt = bcrypt.gensalt()
            pwhash = bcrypt.hashpw(new_password, salt)

            count = 0

            count += editCredentialsPassword(int(user._id), "pwHash", pwhash, "salt", salt)
            if count < 1:
                print('failed to update user credentials')
                flash('failed. please try again')

            flash("Password Sucessfully Reset! Redirecting to Login...")
            return redirect('/login')
        else:
            flash("Invalid token. Try another password reset link.")

    html = render_template('resetverified.html', token = token, email = email)
    return make_response(html)    
