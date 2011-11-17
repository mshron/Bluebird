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
    consumer_secret='Wxij3J8N0jkcDoCBVRPxPGEsm1JXw4JUY27atr4ZjE'
)

def put(attrs, obj_type=None):
    '''write an object in dictionary representation to datastore'''
    if obj_type:
        attrs['type'] = obj_type
    obj = data.parse(attrs)
    print obj
    key = ds.put(obj)
    return key.id() if key else ''

def get_all(key):
    '''retrieve a set of object in JSON representation from datastore'''
    assert(ds.redis.exists(key))
    return ds.get_all(key)

def collection_handler(request, col_key, obj_type=None):
    '''Default handling for fl.requests on object urls:
    * Write object on post,
    * Retrieve list objects in collection on GET'''
    if request.method in ['POST','PUT']:
        return put(fl.request.json, obj_type=obj_type); 
    else:
        return fl.Response(js.dumps(get_all(col_key), cls=data.DataEncoder), mimetype='application/json')


@app.before_request
def before_request():
    fl.g.user = None
    if 'user_id' in fl.session:
        user_key = '%s:%s' ('User', fl.session['user_id'])
        fl.g.user = ds.get(user_key)

@twitter.tokengetter
def get_twitter_token():
    user = fl.g.user
    if user is not None:
        return user.oauth_token, user.oauth_secret

@app.route('/login')
def login():
    """Calling into authorize will cause the OpenID auth machinery to kick
in. When all worked out as expected, the remote application will
redirect back to the callback URL provided.
"""
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
        user = data.User(key=user_key)

    # in any case we update the authenciation token in the db
    # In case the user temporarily revoked access we will have
    # new tokens here.
    user.oauth_token = resp['oauth_token']
    user.oauth_secret = resp['oauth_token_secret']
    ds.put(user)

    fl.session['user_id'] = user.key.id()
    fl.flash('You were signed in')
    return redirect(next_url)

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

@app.route('/api/documents/<doc_id>/revisions/<rev_id>',
            methods=['PUT'])
def revision(doc_id, rev_id):
    key = 'Document:%s:revisions' % doc_id
    return collection_handler(fl.request, key, obj_type='Revision')

@app.route('/api/documents/<doc_id>/revisions/<rev_id>/vote', 
            methods=['PUT'])
def vote(doc_id, rev_id):
    if fl.request.method == 'PUT':
        # use default user for now
        vote = fl.request.json['vote']
        ukey = fl.request.json['user']
        rkey = 'Revision:%s' % (rev_id)
        dkey = 'Document:%s' % doc_id
        up_voted = ds.inter(['%s:revisions' % dkey, '%s:up_voted' % ukey])
        down_voted = ds.inter(['%s:revisions' % dkey, '%s:down_voted' % ukey])
        # vote blanking is always ok
        if vote==0 or (vote==-1 and (rkey in up_voted)) \
           or (vote==1 and (rkey in down_voted)): 
            ds.vote(ukey, rkey, vote)
        else:
            # allow vote if user has votes left, and has not voted in thread
            rev = ds.get(rkey)
            if (vote==1) and (len(up_voted) < MAX_UP):
                if not ds.inter(['%s:revisions' % rev.root, '%s:up_voted' % ukey]):
                    ds.vote(ukey, rkey, vote)
                else:
                    fl.abort(403)
            elif (vote==-1) and (len(down_voted) < MAX_DOWN):   
                if not ds.inter(['%s:revisions' % rev.root, '%s:down_voted' % ukey]):
                    ds.vote(ukey, rkey, vote)
                else:
                    fl.abort(403)
            else:
                fl.abort(403)
        return fl.Response('Succes')

@app.route('/documents/<doc_id>')
def dochtml(doc_id):
    ddata = [obj.__dict__ for obj in get_all('Document:%s:revisions'%doc_id)]
        return fl.render_template('test.html', data=ddata) #FIXME

if __name__ == "__main__":
    app.run()
