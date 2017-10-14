#!/usr/bin/env python3

from flask import (
    Flask, render_template, request,
    redirect, jsonify, url_for, flash, make_response)
from sqlalchemy import create_engine, asc, func
from sqlalchemy.orm import sessionmaker
from models import Base, User, Item, Category, Vote
from flask import session as login_session
import random
import string
import httplib2
import json
import requests
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

# fill ye olde Flask
app = Flask(__name__)
app.secret_key = ''.join(
    random.choice(string.ascii_uppercase + string.digits)
    for x in range(32))

CLIENT_ID = json.loads(
    open('/var/www/html/opinionated/client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Opinionated"


# Connect to Database and create database session
engine = create_engine("postgresql://grader:grader@localhost:5432/opinionated")
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# [=====================]
# I   Authentication    I
# [=====================]

# generates state token for authentication
@app.route('/opinionated/login')
def userLogin():
    login_session['onTheLoginPage'] = True
    formerPage = request.args.get('formerPage')
    if formerPage is None:
        formerPage = '/home'
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for x in range(32))
    login_session['state'] = state
    template = render_template(
        'login.html',
        STATE=state,
        formerPage=formerPage,
        client_id=CLIENT_ID)
    login_session['onTheLoginPage'] = False
    return template


# for OAuth connection
@app.route('/opinionated/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps(
            'Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(
            '/var/www/opinionated/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'),
            401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = (
        'https://www.googleapis.com/oauth2/v1/'
        'tokeninfo?access_token={}'.format(
            access_token))
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    response = response.decode('utf8')

    result = json.loads(response.json())
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps(
            "Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps(
                'Current user is already connected.'), 200)
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

    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    if session.query(User).filter_by(
            email=login_session['email']).first() is None:

        login_session['username'] = data['name']
        session.add(User(
            username=login_session['username'],
            email=login_session['email'],
            about="Hi. I'm new to Opinionated and haven't configured "
                  "my profile",
            picture=login_session['picture']))
        session.commit()

    theUser = session.query(User).filter_by(
        email=login_session['email']).one()

    login_session['user_id'] = theUser.id
    login_session['username'] = theUser.username
    # build an actual welcome template
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img class="profilePic" src="'
    output += login_session['picture']
    output += ' " style = "width: 200px; height: 200px;' \
        'border-radius: 50%;"> '
    flash("you are now logged in as {}".format(login_session['username']))

    return output


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/opinionated/gdisconnect')
def gdisconnect():
    # clear the login_session right away. Even if revocation fails
    # user will want this. also. little to nothing user could do
    # to fix this, so. better just to do it.
    login_session.clear()

    # then we get google to revoke the token
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return redirect('/')
    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(
        login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        login_session.clear()
        flash("logging out worked")
        return redirect(url_for('showIndex'))
    else:
        flash("logging out failed")
        return redirect(url_for('showIndex'))


# [=====================]
# I Routes for viewing  I
# [=====================]


# Main Page
@app.route('/opinionated/')
@app.route('/opinionated/home')
def showIndex():
    categories = session.query(Category).order_by(Category.name).all()

    for category in categories:
        category.users_name = session.query(User).filter_by(
            id=category.created_by).one().username
    return render_template('categoryList.html', categories=categories)


# category page
@app.route('/opinionated/categories/<int:category_id>')
def showCategory(category_id):
    category = session.query(Category).filter_by(
        id=category_id).one()
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    user = session.query(User).filter_by(
        id=category.created_by).one()

    return render_template(
        'categoryPage.html',
        category=category,
        items=items,
        user=user)


# individual item page
@app.route('/opinionated/opinions/<int:item_id>')
def showItem(item_id):
    item = session.query(Item).filter_by(
        id=item_id).one()
    category = session.query(Category).filter_by(
       id=item.category_id).one()
    user = session.query(User).filter_by(
        id=item.created_by).one()
    user_voted = False
    if login_session.get('user_id'):
        user_voted = session.query(Vote).filter_by(
            item=item_id,
            voter=login_session['user_id']).first()
    up_votes = session.query(func.count(Vote.id)).filter_by(
        item=item_id,
        up_or_down=1).one()[0]
    down_votes = session.query(func.count(Vote.id)).filter_by(
        item=item_id,
        up_or_down=0).one()[0]
    return render_template(
        'itemPage.html',
        category=category,
        item=item,
        user=user,
        up_votes=up_votes,
        down_votes=down_votes,
        user_voted=user_voted)


# user categories page
@app.route('/opinionated/users/<int:user_id>/categories')
def showUserCats(user_id):
    categories = session.query(Category).filter_by(
        created_by=user_id).all()
    user = session.query(User).filter_by(
        id=user_id).one()
    up_votes = session.query(func.count(Vote.id)).filter_by(
        votee=user_id,
        up_or_down=1).one()[0]
    down_votes = session.query(func.count(Vote.id)).filter_by(
        votee=user_id,
        up_or_down=0).one()[0]
    user_upVotes = session.query(func.count(Vote.id)).filter_by(
        voter=user_id,
        up_or_down=1).one()[0]
    user_downVotes = session.query(func.count(Vote.id)).filter_by(
        voter=user_id,
        up_or_down=0).one()[0]
    user_votes = [user_upVotes, user_downVotes]
    return render_template(
        'userCategoriesPage.html',
        categories=categories,
        user=user,
        up_votes=up_votes,
        down_votes=down_votes,
        user_votes=user_votes)


# search results page
@app.route('/opinionated/search')
def showSearchResults():
    searchType = request.args['searchType']
    if searchType == 'Category' or searchType == "Item":
        if not request.args['search']:
            flash('Search cannot be empty')
            return render_template(
                'showIndex',
                categories=None)
        term = request.args['search']
        if searchType == 'Category':
            categories = session.query(Category).filter(
                Category.name.like("%"+term+"%")).all()
            for category in categories:
                category.users_name = session.query(User).filter_by(
                    id=category.created_by).one().username
            return render_template(
                'categoryList.html',
                categories=categories,
                search=term)
        elif searchType == 'Item':
            items = session.query(Item).filter(
                Item.name.like("%"+term+"%")).all()
            return render_template(
                'categoryPage.html',
                category=Category(
                    name="Search results for {}".format(term),
                    created_by=1,
                    id=0),
                items=items)

    else:
        flash('An error occured. Try searching again')
        return redirect(url_for('showIndex'))


@app.route('/opinionated/users')
def showAllUsers():
    users = session.query(User).all()
    return render_template('allUsers.html', users=users)


@app.route('/opinionated/developers')
def forDevelopers():
    return render_template('forDevelopers.html')


# I=====================I
# I Routes for editing  I
# I=====================I


# edit user's profile
@app.route('/opinionated/users/<int:user_id>/edit', methods=['GET', 'POST'])
def editProfile(user_id):

    if request.method == 'GET':
        # first, check to make sure user is logged in
        email = login_session.get('email')
        if email is None:
            flash("You must be logged in to proceed")
            return redirect(url_for(
                'userLogin')+'?formerPage=users/'+str(user_id)+'/edit')
        currentUser = session.query(User).filter_by(
            email=login_session['email']).first()
        pageUser = session.query(User).filter_by(
            id=user_id).one()
        if currentUser is None:
            flash("You must be logged in to proceed")
            return redirect(url_for(
                'userLogin')+'?formerPage=users/'+str(user_id)+'/edit')
        # then make sure they are logged in as the right user
        elif currentUser.id != user_id:
            flash(
                "You must be logged in as {} to edit this page."
                "Try logging in with a different account".format(
                    pageUser.username))
            return redirect(url_for(
                'userLogin')+'?formerPage=users/'+str(user_id)+'/edit')
        # if so, we give them the resource
        else:
            return render_template(
                'edituser.html',
                user=currentUser)
    elif request.method == 'POST':
        if login_session.get('user_id') == user_id:
            user = session.query(User).filter_by(
                id=user_id).one()
            if request.form.get('username'):
                user.username = request.form['username']
            if request.form.get('about'):
                user.about = request.form['about']
            session.commit()

            flash("Profile updated")
            return render_template(
                'edituser.html',
                user=user)
        else:
            flash("Authentication error. Try logging in again")
            return redirect(url_for(
                'userLogin')+'?formerPage=users/'+str(user_id)+'/edit')


# edit an individual item
@app.route('/opinionated/opinions/<int:item_id>/edit', methods=['GET', 'POST'])
def editItem(item_id):
    item = session.query(Item).filter_by(id=item_id).first()
    if request.method == 'POST':
        if request.form.get('name'):
            item.name = request.form.get('name')
        if request.form.get('description'):
            item.description = request.form.get('description')
        session.commit()
        category = session.query(Category).filter_by(
            id=item.category_id).one()
        flash("Item has been updated")
        return redirect(url_for('showCategory', category_id=category.id))
    else:
        if item.created_by == login_session['user_id']:
            return render_template('editItem.html', item=item)
        else:
            flash("Authentication error. Try logging in again")
            return redirect(url_for(
                'userLogin')+'?formerPage=opinions/'+str(item_id)+'/edit')


# I=====================I
# I Routes for adding   I
# I=====================I


# add item
@app.route('/opinionated/categories/<int:category_id>/newitem', methods=['GET', 'POST'])
def makeNewItem(category_id):
    if login_session.get('user_id') is None:
        flash('You must be logged in to submit new opinions')
        return redirect(url_for(
            'userLogin')+'?formerPage=categories/'+str(category_id)+'/newitem')
    category = session.query(Category).filter_by(id=category_id).one()

    if category.created_by != login_session['user_id']:
        flash('You must be the creator of this category to add new opinions.')
        flash('Log in to confirm your identity, chump.')
        return redirect(url_for(
            'userLogin')+'?formerPage=categories/'+str(category_id)+'/newitem')

    else:

        if request.method == "POST":
            session.add(Item(
                name=request.form['name'],
                description=request.form['description'],
                category_id=category_id,
                created_by=login_session['user_id']))
            session.commit()
            flash('New opinion on {} uselessly submitted to the void'.format(
                request.form['name']))
            return redirect(url_for(
                'showCategory',
                category_id=category_id))

        else:
            return render_template(
                'makeNewItem.html',
                category=category)


# add category
@app.route('/opinionated/categories/new', methods=['GET', 'POST'])
def makeNewCategory():
    if login_session.get('user_id') is None:
        flash('You must be logged in to create new categories')
        return redirect(url_for(
            'userLogin')+'?formerPage=categories/new')
    else:
        if request.method == 'POST':
            if request.form.get('name') is None:
                flash('There was an error submitting your request')
                return redirect('./#')
            else:
                newCat = Category(
                    name=request.form['name'],
                    created_by=login_session['user_id'])
                session.add(newCat)
                session.commit()

                return redirect(url_for(
                    'showCategory',
                    category_id=newCat.id))


# I=====================I
# I Routes for deleting I
# I=====================I

# delete item
@app.route('/opinionated/opinions/<int:item_id>/delete', methods=['DELETE'])
def deleteItem(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    if login_session['user_id'] == item.created_by:
        name = item.name
        category_id = item.category_id
        session.delete(item)
        session.commit()
        flash('{} has been deleted'.format(name))
        return redirect(url_for(
            'showCategory', category_id=category_id), code=200)
    else:
        flash('Users can only delete their own items')
        flash('Please log in to continue')
        return redirect(url_for(
            'userLogin')+'?formerPage=/home', code=200)


# delete user
@app.route('/opinionated/users/<int:user_id>/delete', methods=['DELETE'])
def deleteUser(user_id):
    if login_session['user_id'] == user_id:
        # delete all categories, votes and items associated with user
        categories = session.query(Category).filter_by(
            created_by=user_id).all()
        for category in categories:
            session.delete(category)

        items = session.query(Item).filter_by(created_by=user_id).all()
        for item in items:
            session.delete(item)

        votes = session.query(Vote).filter_by(voter=user_id).all()
        for vote in votes:
            session.delete(vote)
        # delete user once we have gotten rid of their stuff
        session.delete(session.query(User).filter_by(id=user_id).one())
        session.commit()
        login_session.clear()
        flash("You have deleted your account")
        # return to index
        return redirect(url_for('showIndex'), code=200)
    else:
        flash('Users can only delete their own accounts')
        flash('Please log in to proceed')
        return redirect(url_for('userLogin')+'?formerPage=/home', code=200)


# delete category
@app.route('/opinionated/categories/<int:category_id>/delete', methods=['DELETE'])
def deleteCategory(category_id):
    category = session.query(Category).filter_by(id=category_id).one()
    if login_session['user_id'] != category.created_by:
        flash('Users can only delete their own items.')
        flash('Please try logging in to proceed')
        return redirect(url_for('userLogin')+'?formerPage=/home')
    else:
        session.delete(category)
        items = session.query(Item).filter_by(category_id=category_id).all()
        for item in items:
            session.delete(item)
        session.commit()
        flash('Successfully deleted category')
        return make_response('OK', 200)


# I=====================I
# I   Voting Endpoint   I
# I=====================I


@app.route(
    '/opinionated/opinions/vote/<int:vote>/<int:user_id>/<int:item_id>',
    methods=['POST'])
def userVote(vote, user_id, item_id):
    session.add(Vote(
        voter=user_id,
        item=item_id,
        up_or_down=vote))
    session.commit()
    return "Thanks! Your vote has been recorded"


# I=====================I
# I    API Endpoints    I
# I=====================I


@app.route('/opinionated/api/opinions/<string:item_id>')
def apiOpinion(item_id):
    item = session.query(Item).filter_by(id=item_id).first()
    if not item:
        return jsonify({'Error': 'No such opinion'})
    votes = session.query(Vote).filter_by(item=item_id).all()
    voteDict = {}
    if len(votes):
        for i, vote in enumerate(votes):
            voteDict[i] = vote.serialize()

    return jsonify({
        'Opinion': item.serialize(),
        'Votes': voteDict})


@app.route('/opinionated/api/users/<string:user_identifier>')
def apiUserSearch(user_identifier):
    # first, we determine how the user is being queried
    user_identifier = user_identifier.encode()
    # if the route variable is an integer
    if str.isdigit(user_identifier):
        user = session.query(User).filter_by(id=user_identifier).first()
    # otherwise, we assume it is an email
    else:
        user = session.query(User).filter_by(email=user_identifier).first()

    # but if not, then we let the user know the request didn't work
    if not user:
        return jsonify({
            'Error': 'Your request failed to identify a user '
            'Check to make sure your request was properly formatted and/or '
            'confirm that there is a user matching your query'})

    # and if it did, we give them information about the user
    if not request.args:
        return jsonify({'user': user.serialize()})

    # if a search parameter is given, we see what they are searching for
    elif request.args['search']:
        # return all categories by identified user
        if request.args['search'] == 'categories':
            catDict = {}
            categories = session.query(Category).filter_by(
                created_by=user.id).all()
            for i, category in enumerate(categories):
                info = category.serialize()
                catDict[i] = info
            return jsonify({'categories': catDict})
        # return all opinions by identified user
        elif request.args['search'] == 'opinions':
            opDict = {}
            for i, opinion in enumerate(session.query(Item).filter_by(
                    created_by=user.id).all()):
                info = opinion.serialize()
                opDict[i] = info
            return jsonify({'opinions': opDict})

    else:
        return jsonify({'Error': "Could not understand your request"})


@app.route('/opinionated/api/categories/<int:category_id>')
def apiCategory(category_id):
    # check if request parameters are included
    if request.args:
        limit = request.args.get('limit').encode()
        # check to make sure request is formatted properly
        if not str.isdigit(limit):
            return jsonify({
                'Error': "Could not understand your request. Limit must"
                " be an integer"})
        else:
            categories = session.query(Item).filter_by(
                category_id=category_id).limit(limit).all()
            catDict = {}
            for i, category in enumerate(categories):
                catDict[i] = category.serialize()
            return jsonify({'opinions': catDict})
    # if not, return information on the category
    else:
        category = session.query(Item).filter_by(
            category_id=category_id).all()
        if category:
            catDict = {}
            for i, o in enumerate(category):
                catDict[i] = o.serialize()
            return jsonify({'opinions': catDict})
        else:
            return jsonify({"error": "no match for your search"})


@app.route('/opinionated/api/search/<string:searchType>')
def apiSearch(searchType):
    # just to be certain, we uppercase the search term
    searchType = searchType[0].upper() + searchType[1:]

    if searchType == 'Category' or searchType == "Opinion":
        if searchType == 'Category':
            searchType = Category
        elif searchType == 'Opinion':
            searchType = Item

        if not request.args:
            result = session.query(searchType).all().order_by(
                searchType.name).limit(10)
            resDict = {}
            for i, thing in enumerate(result):
                resDict[i] = thing.serialize()
            return jsonify({'result': resDict})
        else:
            if request.args.get('limit') and str.isdigit(
                    request.args.get('limit').encode()):
                limit = request.args.get('limit')
            else:
                limit = 10
            result = session.query(searchType).filter(searchType.name.like(
                "%"+request.args['find']+"%")).limit(limit).all()
            resDict = {}
            for i, thing in enumerate(result):
                resDict[i] = thing.serialize()
            return jsonify({'result': resDict})
    else:
        return jsonify({
            'Error': 'SearchType {} is not supported'.format(searchType)})


if __name__ == '__main__':

    app.debug = True
    app.run(host='localhost' , port=2222)
