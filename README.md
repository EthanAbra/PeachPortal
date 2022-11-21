# irgo
## Easily view team erg workout data
### by Henry Vecchione, 2021 
### Version 1.0 
*irgo is based on the original, now defunct MyBoathouse, developed for COS333 by Lucas Manning and others*

## Develop locally:
Navigate to the root directory and run `python3 runserver.py <port>`

## What it does 
irgo is a way to keep a rowing team's erg workout data in one place, allowing rowers to compare their scores with others, track performance over time, and look back on scores from previous years. It also allows coxswains and coaches to easily upload workout data. 

## How to use it 
### Logging in, signing up, and registering 
Navigate to [irgo.herokuapp.com](http://irgo.herokuapp.com). Existing users, select "Log in" and enter your login credentials. For first time users whose team is registered with irgo, select "Sign up" and enter your information to create a profile, including the Team Id created when registering your team. For first time users whose team is **not** registered, select "Register team" and enter your team name, which will then direct you to create an account. This first account will be made a team admim, giving them special priviliges to edit team and workout data. 

### /home
Once an account is signed in, you'll be directed to the /home page. From here, you can navigate to the **/workouts** and **/profile** pages. Coxswains and users with 'admin' permissions can download a template sheet and upload a completed sheet. Admins can navigate to the **/team** page. Select the hamburger at the top right to log out. 

### /workouts
This is a list of all workouts your team has done. Click on a workout to view a piece-by-piece breakdown for each athlete. Click "Raw/Split" (top right) to change from viewing raw time and meters to average time/500m. 

Unimplemented: 
- Download workout as .xlsx 

### /profile
See your own profile page, with workouts you've completed, your PRs, and awarded shirts and championships

Unimplemented:
- Profile page
- personal PRs
- shirts

### /team


## How it works ## 

