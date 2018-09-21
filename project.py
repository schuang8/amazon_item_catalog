from flask import (Flask, render_template, request, redirect, jsonify,
                   url_for, flash)
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker, scoped_session
from database_setup import Base, WatchList, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Amazon Watch List Application"

engine = create_engine('sqlite:///watchlistwithusers.db')
Base.metadata.bind = engine


# Connect to Database and create database session
def createDBSession():
    session = scoped_session(sessionmaker(bind=engine))
    return session


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    print("server connection")
    if request.args.get('state') != login_session['state']:
        response = make_response(('Invalid state parameter.', 401))
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data.decode("utf-8")
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange
        we have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then we
        split it on colons to pull out the actual token value and replace the
        remaining quotes with nothing so that it can be used directly in the
        graph api calls
    '''

    url = ("https://graph.facebook.com/v2.8/me?"
           "access_token=%s&fields=name,id,email") % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = access_token

    # Get user picture
    url = ("https://graph.facebook.com/v2.8/me/picture?"
           "access_token=%s&redirect=0&height=200&width=200") % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += """ " style = "width: 300px;
                    height: 300px;
                    border-radius: 150px;
                    -webkit-border-radius: 150px;
                    -moz-border-radius: 150px;"> """

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = ("https://graph.facebook.com/%s"
           "/permissions?access_token=%s") % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(('Invalid state parameter.', 401))
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            ('Failed to upgrade the authorization code.', 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response((result.get('error'), 500))
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            ("Token's user ID doesn't match given user ID.", 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            ("Token's client ID does not match app's.", 401))
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(('Current user is already connected.', 200))
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += """ " style = "width: 300px;
                    height: 300px;
                    border-radius: 150px;
                    -webkit-border-radius: 150px;
                    -moz-border-radius: 150px;"> """
    flash("you are now logged in as %s" % login_session['username'])
    return output


# User Helper Functions
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session = createDBSession()
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one_or_none()
    session.remove()
    return user.id


def getUserInfo(user_id):
    session = createDBSession()
    user = session.query(User).filter_by(id=user_id).one_or_none()
    session.remove()
    return user


def getUserID(email):
    session = createDBSession()
    try:
        user = session.query(User).filter_by(email=email).one_or_none()
        session.remove()
        return user.id
    except:
        session.remove()
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(('Current user not connected.', 401))
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(('Successfully disconnected.', 200))
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(
            ('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Watch List Information
@app.route('/watchlist/<int:watch_list_id>/list/JSON')
def watchListJSON(watch_list_id):
    session = createDBSession()
    watch_list = session.query(WatchList).filter_by(id=watch_list_id).one_or_none()
    items = session.query(Item).filter_by(
        watch_list_id=watch_list_id).all()
    session.remove()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/watchlist/<int:watch_list_id>/list/<int:item_id>/JSON')
def itemJSON(watch_list_id, item_id):
    session = createDBSession()
    item = session.query(Item).filter_by(id=item_id).one_or_none()
    session.remove()
    return jsonify(item=item.serialize)


@app.route('/watchlist/JSON')
def allListsJSON():
    session = createDBSession()
    watch_list = session.query(WatchList).all()
    session.remove()
    return jsonify(watch_list=[r.serialize for r in watch_list])


# Show all Watch Lists
@app.route('/')
@app.route('/watchlist/')
def showAllLists():
    session = createDBSession()
    watch_list = session.query(WatchList).order_by(asc(WatchList.name))
    session.remove()
    if 'username' not in login_session:
        return render_template('publicAllLists.html', watch_list=watch_list)
    else:
        return render_template('allLists.html', watch_list=watch_list)


# Create a new watchlist
@app.route('/watchlist/new/', methods=['GET', 'POST'])
def newWatchList():
    session = createDBSession()
    if 'username' not in login_session:
        session.remove()
        return redirect('/login')
    if request.method == 'POST':
        newWatchList = WatchList(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newWatchList)
        flash('New Watch List %s Successfully Created' % newWatchList.name)
        session.commit()
        session.remove()
        return redirect(url_for('showAllLists'))
    else:
        session.remove()
        return render_template('newWatchList.html')


# Edit a Watch List
@app.route('/watchlist/<int:watch_list_id>/edit/', methods=['GET', 'POST'])
def editWatchList(watch_list_id):
    session = createDBSession()
    editedWatchList = session.query(
        WatchList).filter_by(id=watch_list_id).one_or_none()
    if 'username' not in login_session:
        session.remove()
        return redirect('/login')
    if editedWatchList.user_id != login_session['user_id']:
        session.remove()
        return """<script>
                    function myFunction() {
                        alert('You are not authorized to edit this list.');
                    }
                  </script>
                <body onload='myFunction()'>"""
    if request.method == 'POST':
        if request.form['name']:
            editedWatchList.name = request.form['name']
            session.add(editedWatchList)
            session.commit()
            flash('Watch List Successfully Edited %s' % editedWatchList.name)
            session.remove()
            return redirect(url_for('showAllLists'))
    else:
        session.remove()
        return render_template('editWatchList.html',
                               watch_list=editedWatchList)


# Delete a Watch List
@app.route('/watchlist/<int:watch_list_id>/delete/', methods=['GET', 'POST'])
def deleteWatchList(watch_list_id):
    session = createDBSession()
    watchListToDelete = session.query(
        WatchList).filter_by(id=watch_list_id).one_or_none()
    if 'username' not in login_session:
        session.remove()
        return redirect('/login')
    if watchListToDelete.user_id != login_session['user_id']:
        session.remove()
        return """<script>
                    function myFunction() {
                        alert('You are not authorized to delete this list.');
                    }
                  </script>
                  <body onload='myFunction()'>"""
    if request.method == 'POST':
        session.delete(watchListToDelete)
        flash('%s Successfully Deleted' % watchListToDelete.name)
        session.commit()
        session.remove()
        return redirect(url_for('showAllLists', watch_list_id=watch_list_id))
    else:
        session.remove()
        return render_template('deleteWatchList.html',
                               watch_list=watchListToDelete)


# Show a watch list
@app.route('/watchlist/<int:watch_list_id>/')
@app.route('/watchlist/<int:watch_list_id>/list/')
def showWatchList(watch_list_id):
    session = createDBSession()
    watch_list = session.query(WatchList).filter_by(id=watch_list_id).one_or_none()
    creator = getUserInfo(watch_list.user_id)
    items = session.query(Item).filter_by(
        watch_list_id=watch_list_id).all()
    session.remove()
    if (
        'username' not in login_session or
        creator.id != login_session['user_id']
       ):
        return render_template('publicWatchList.html',
                               items=items,
                               watch_list=watch_list,
                               creator=creator)
    else:
        return render_template('watchList.html',
                               items=items,
                               watch_list=watch_list,
                               creator=creator)


# Create a new watchlist item
@app.route('/watchlist/<int:watch_list_id>/list/new/',
           methods=['GET', 'POST'])
def newItem(watch_list_id):
    session = createDBSession()
    if 'username' not in login_session:
        session.remove()
        return redirect('/login')
    watch_list = session.query(WatchList).filter_by(id=watch_list_id).one_or_none()
    if login_session['user_id'] != watch_list.user_id:
        session.remove()
        return """<script>
                    function myFunction() {
                    alert('You are not authorized to add items to this list.');
                    }
                  </script>
                  <body onload='myFunction()'>"""
    if request.method == 'POST':
        newItem = Item(name=request.form['name'],
                       url=request.form['url'],
                       price=request.form['price'],
                       discount=request.form['discount'],
                       category=request.form['category'],
                       in_stock=request.form['in_stock'],
                       watch_list_id=watch_list_id,
                       user_id=watch_list.user_id)
        session.add(newItem)
        session.commit()
        flash('New Item: %s Successfully Created' % (newItem.name))
        session.remove()
        return redirect(url_for('showWatchList', watch_list_id=watch_list_id))
    else:
        session.remove()
        return render_template('newItem.html', watch_list_id=watch_list_id)


# Edit an item
@app.route('/watchlist/<int:watch_list_id>/list/<int:item_id>/edit',
           methods=['GET', 'POST'])
def editListItem(watch_list_id, item_id):
    session = createDBSession()
    if 'username' not in login_session:
        session.remove()
        return redirect('/login')
    editedItem = session.query(Item).filter_by(id=item_id).one_or_none()
    watch_list = session.query(WatchList).filter_by(id=watch_list_id).one_or_none()
    if login_session['user_id'] != watch_list.user_id:
        session.remove()
        return """<script>
                function myFunction() {
                alert('You are not authorized to edit items to this list.');
                }
                </script>
                <body onload='myFunction()'>"""
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['url']:
            editedItem.url = request.form['url']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['discount']:
            editedItem.discount = request.form['discount']
        if request.form['category']:
            editedItem.category = request.form['category']
        if request.form['in_stock']:
            editedItem.in_stock = request.form['in_stock']
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        session.remove()
        return redirect(url_for('showWatchList', watch_list_id=watch_list_id))
    else:
        session.remove()
        return render_template('editListItem.html',
                               watch_list_id=watch_list_id,
                               item_id=item_id,
                               item=editedItem)


# Delete an item
@app.route('/watchlist/<int:watch_list_id>/list/<int:item_id>/delete',
           methods=['GET', 'POST'])
def deleteListItem(watch_list_id, item_id):
    session = createDBSession()
    if 'username' not in login_session:
        session.remove()
        return redirect('/login')
    watch_list = session.query(WatchList).filter_by(id=watch_list_id).one_or_none()
    itemToDelete = session.query(Item).filter_by(id=item_id).one_or_none()
    if login_session['user_id'] != watch_list.user_id:
        session.remove()
        return """<script>
                function myFunction() {
                alert('You are not authorized to delete items to this list.');
                }
                  </script>
                  <body onload='myFunction()'>"""
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted')
        session.remove()
        return redirect(url_for('showWatchList', watch_list_id=watch_list_id))
    else:
        session.remove()
        return render_template('deleteListItem.html', item=itemToDelete)


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showAllLists'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showAllLists'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(debug=True)
