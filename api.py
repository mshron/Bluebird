'''A flask webapp for the data model'''
# TODO: Some API calls need to perform multiple datastore writes. 
# If one of these fails after others have succeeded, then 
# the datastore will be in an inconsistent state. -- JWM 

import flask as fl
from flaskext.oauth import OAuth
import json as js
import data
import logic

# configuration
SECRET_KEY = 'abcdef'
DEBUG = True
MAX_UP = 3
MAX_DOWN = 3
TEST_USER = None

# open app instance
app = fl.Flask(__name__)
app.debug = DEBUG
app.secret_key = SECRET_KEY

# open datastore instance (threadsafe)
ds = data.DataStore()

# set up oauth authentication with twitter
oauth = OAuth()
twitter = oauth.remote_app('twitter',
    base_url='http://api.twitter.com/1/',
    request_token_url='http://api.twitter.com/oauth/request_token',
    access_token_url='http://api.twitter.com/oauth/access_token',
    authorize_url='http://api.twitter.com/oauth/authenticate',
    consumer_key='QzW7VFbwH2uhUrVqdtwrA',
    consumer_secret='Wxij3J8N0jkcDoCBVRPxPGEsm1JXw4JUY27atr4ZjE')

def put(attrs, obj_type=None):
    '''write an object in dictionary representation to datastore'''
    if obj_type:
        attrs['type'] = obj_type
    obj = data.parse(attrs)
    # ensure current user is author of new revision
    if hasattr(obj, 'author'):
        obj.author = fl.g.user.key
    key = ds.put(obj)
    return key.id() if key else ''

def get(key):
    '''retrieve an object in JSON representation from datastore'''
    assert(ds.redis.exists(key))
    return ds.get(key)

def get_all(key):
    '''retrieve a set of objects in JSON representation from datastore'''
    assert(ds.redis.exists(key))
    return ds.get_all(key)

def collection_handler(request, col_key, obj_type=None):
    '''Default handling for fl.requests on collection urls:
    * Write object on POST/PUT
    * Retrieve list objects in collection on GET'''
    app.logger.debug('[collection_handler] collection: %s, method: %s user: %s' % (col_key, fl.request.method, fl.g.user))
    if fl.request.method in ['POST','PUT']:
        return put(fl.request.json, obj_type=obj_type); 
    else:
        return fl.Response(js.dumps(get_all(col_key), cls=data.DataEncoder), mimetype='application/json')

def object_handler(request, obj_key, obj_type=None):
    '''Default handling for fl.requests on object urls:
    * Write object on POST/PUT
    * Retrieve list objects in collection on GET'''
    app.logger.debug('[object_handler] collection: %s, method: %s user: %s' % (obj_key, fl.request.method, fl.g.user))
    if fl.request.method in ['POST','PUT']:
        return put(fl.request.json, obj_type=obj_type); 
    else:
        return fl.Response(js.dumps(get(obj_key), cls=data.DataEncoder), mimetype='application/json')

@app.before_request
def before_request():
    fl.g.user = None
    if 'user_id' in fl.session:
        user_key = '%s:%s' % ('User', fl.session['user_id'])
        fl.g.user = ds.get(user_key)
    elif TEST_USER:
        fl.g.user = TEST_USER

@twitter.tokengetter
def get_twitter_token():
    user = fl.g.user
    if user is not None:
        return user.oauth_token, user.oauth_secret

@app.route('/login')
def login():
    return twitter.authorize(callback=fl.url_for('oauth_authorized',
        next=fl.request.args.get('next') or fl.request.referrer or None))

@app.route('/logout')
def logout():
    fl.session.pop('user_id', None)
    fl.flash('You were signed out')
    return fl.redirect(fl.request.referrer or fl.url_for('index'))

@app.route('/oauth-authorized')
@twitter.authorized_handler
def oauth_authorized(resp):
    next_url = fl.request.args.get('next') or fl.url_for('index')
    if resp is None:
        fl.flash(u'You denied the request to sign in.')
        return fl.redirect(next_url)
    
    user_key = 'User:twitter_%s' % resp['screen_name']
    user = ds.get(user_key)

    # user never signed on
    if user is None:
        user = data.User(key=user_key, screen_name=resp['screen_name'])

    # in any case we update the authenciation token in the db
    # In case the user temporarily revoked access we will have
    # new tokens here.
    user.oauth_token = resp['oauth_token']
    user.oauth_secret = resp['oauth_token_secret']
    ds.put(user)

    fl.session['user_id'] = user.key.id()
    fl.flash('You were signed in')
    return fl.redirect(next_url)

@app.route('/api/users',
            methods=['GET','POST'])
def users():
    key = 'users'
    return collection_handler(fl.request, key, obj_type='User')

@app.route('/api/documents',
            methods=['GET','POST'])
def documents():
    key = 'documents'
    return collection_handler(fl.request, key, obj_type='Document')

@app.route('/api/documents/<doc_id>/revisions',
            methods=['GET','POST'])
def threads(doc_id):
    key = 'Document:%s:revisions' % doc_id
    return collection_handler(fl.request, key, obj_type='Revision')

@app.route('/api/users/<user_id>',
            methods=['GET','PET'])
def user(user_id):
    key = 'User:%s' % user_id
    return object_handler(fl.request, key, obj_type='User')

@app.route('/api/documents/<doc_id>/revisions/<rev_id>',
            methods=['PUT', 'DELETE'])
def revision(doc_id, rev_id):
    if fl.request.method == 'PUT':
        key = 'Document:%s:revisions' % doc_id
        return collection_handler(fl.request, key, obj_type='Revision')
    if fl.request.method == 'DELETE':
        key = 'Revision:%s' % rev_id
        return ds.delete(key)

@app.route('/api/documents/<doc_id>/revisions/<rev_id>/vote', 
            methods=['PUT'])
def vote(doc_id, rev_id):
    if fl.request.method == 'PUT':
        vote = int(fl.request.args.get('type', None))
        if not vote is None:
            user = fl.g.user
            rkey = 'Revision:%s' % (rev_id)
            dkey = 'Document:%s' % doc_id
            up_voted = ds.inter(['%s:revisions' % dkey, '%s:up_voted' % user])
            down_voted = ds.inter(['%s:revisions' % dkey, '%s:down_voted' % user])
            # vote blanking is always ok
            if vote==0 or (vote==-1 and (rkey in up_voted)) \
               or (vote==1 and (rkey in down_voted)): 
                ds.vote(user, rkey, vote)
            else:
                # allow vote if user has votes left, and has not voted in thread
                rev = ds.get(rkey)
                if (vote==1) and (len(up_voted) < MAX_UP):
                    if not ds.inter(['%s:revisions' % rev.root, '%s:up_voted' % user]):
                        ds.vote(user, rkey, vote)
                    else:
                        fl.abort(403)
                elif (vote==-1) and (len(down_voted) < MAX_DOWN):   
                    if not ds.inter(['%s:revisions' % rev.root, '%s:down_voted' % user]):
                        ds.vote(user, rkey, vote)
                    else:
                        fl.abort(403)
                else:
                    fl.abort(403)
            return fl.Response('Succes')
        else:
            fl.abort(403)

@app.route('/documents/<doc_id>')
def dochtml(doc_id):
    if fl.g.user is None:
        app.logger.debug('[collection_handler] redirect')
        return fl.redirect(fl.url_for('login', next=fl.request.url))
    ddata = [obj.__dict__ for obj in get_all('Document:%s:revisions'%doc_id)]
    return fl.render_template('test.html', data=ddata) #FIXME

if __name__ == "__main__":
    import logging
    file_handler = logging.FileHandler('api.log')
    file_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(file_handler)
    app.run()
