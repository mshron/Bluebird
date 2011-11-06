'''A flask webapp for the data model'''
# TODO: Some API calls need to perform multiple datastore writes. 
# If one of these fails after others have succeeded, then 
# the datastore will be in an inconsistent state. I've strived to
# catch  -- JWM 

import flask as fl
import json as js
import data
import logic

# open app instance
app = fl.Flask(__name__)
app.debug = True

# open datastore instance (threadsafe)
ds = data.DataStore()

# initialize dummy user (no authentication implemented yet)
user = data.User(handle='wonka', name='willie', location='UK', bio='i make chocolate')

# define maximum up and down votes (not sure where this should live yet)
MAX_UP = 3
MAX_DOWN = 3

def put(obj_key, attrs):
    '''write an object in dictionary representation to datastore'''
    # ensure object key matches post url
    obj = data.parse(attrs)
    obj.key = obj_key
    return ds.put(obj)

def post(col_key, attrs):
    '''post an object in dictionary representation to datastore'''
    obj = data.parse(attrs)
    obj.key = '%s:%s' % (col_key, data.rnd())
    return ds.put(obj)

def get(key):
    '''retrieve an object in JSON representation from datastore'''
    assert(ds.redis.exists(key))
    return js.dumps(ds.get(key).__dict__)

def list_json(key):
    '''retrieve an object in JSON representation from datastore'''
    assert(ds.redis.exists(key))
    return js.dumps(ds.list(key).__dict__)

def object_handler(request, obj_key):
    '''Default handling for fl.requests on object urls:
    * Write to datastore on PUT,
    * Retrieve from datastore on GET'''
    if request.method == 'PUT':
        return put(obj_key, request.json)
    else:
        json = get(obj_key)
        return fl.Response(json, mimetype='application/json')

def collection_handler(request, col_key):
    '''Default handling for fl.requests on object urls:
    * Add object with new id to collection on POST,
    * Retrieve list objects in collection on GET'''
    if request.method == 'POST':
        return post(col_key, fl.request.json); 
    else:
        json = list_json(col_key)
        return fl.Response(json, mimetype='application/json')

@app.route('/api/Users',
            methods=['GET','POST'])
def documents():
    key = 'Users'
    return collection_handler(fl.request, key)

@app.route('/api/Documents',
            methods=['GET','POST'])
def documents():
    key = 'Documents'
    return collection_handler(fl.request, key)

@app.route('/api/Documents/<doc_id>/Threads',
            methods=['GET','POST'])
def threads(doc_id):
    key = 'Documents:%s:Threads' % doc_id
    return collection_handler(fl.request, key)

@app.route('/api/Documents/<doc_id>/Threads/<thread_id>/Revisions',
            methods=['GET','POST'])
def revisions(doc_id, thread_id):
    key = 'Documents:%s:Threads:%s:Revisions' % (doc_id, thread_id)
    return collection_handler(fl.request, key)

@app.route('/api/Users/<user_id>', 
           methods=['GET','PUT'])
def user(user_id):
    '''Retrieve and write back user info'''
    key = 'Users:%s' % user_id
    return object_handler(fl.request, key)

@app.route('/api/Documents/<doc_id>', 
           methods=['GET','PUT'])
def document(doc_id):
    '''Retrieve and write back document records'''
    key = 'Documents:%s' % doc_id
    return object_handler(fl.request, key)
     
@app.route('/api/Documents/<doc_id>/Threads/<thread_id>', 
           methods=['GET','PUT'])
def thread(doc_id, thread_id):
    '''Retrieve and write back thread records'''
    key = 'Documents:%s:Threads:%s' % (doc_id, thread_id)
    return object_handler(fl.request, key)

@app.route('/api/Documents/<doc_id>/Threads/<thread_id>/Revisions/<rev_id>', 
            methods=['GET','PUT'])
def revision(doc_id, thread_id, rev_id):
    '''Retrieve and write back revision records'''
    key = 'Documents:%s:Threads:%s:Revisions:%s' % (doc_id, thread_id, rev_id)
    return object_handler(fl.request, key)

@app.route('/api/Documents/<doc_id>/Threads/<thread_id>/Revisions/<rev_id>/Forks/<fork_id>', 
            methods=['PUT'])
def fork(doc_id, thread_id, rev_id):
    '''Retrieve and write back revision records'''
    if fl.request.method == 'PUT':
        try:
            # check that parent revision exists
            rkey = 'Documents:%s:Threads:%s:Revision:%s' % (doc_id, thread_id, rev_id)
            assert ds.redis.exists(rkey)
            # write out fork
            fkey = 'Documents:%s:Threads:%s:Revision:%s' % (doc_id, thread_id, fork_id)
            json = fl.request.json
            put(key, json)
            # the parent revision needs updating, since 
            # the fork parent (updated in put) is the thread
            rev = ds.get(rkey)
            if not fkey in rev.children:
                rev.children.append(fkey)
                ds.put(rev)
        except AssertionError:
            fl.abort(404)

@app.route('/api/documents/<doc_id>/threads/<thread_id>/revisions/<rev_id>/vote/<int:vote>', 
            methods=['PUT'])
def vote(doc_id, thread_id, rev_id, vote):
    rkey = 'Documents:%s:Threads:%s:Revision:%s' % (doc_id, thread_id, rev_id)
    assert(ds.redis.exists(rkey))
    dkey = 'Documents:%s' % doc_id
    up_voted = set(user.up_voted[dkey])
    down_voted = set(user.down_voted[dkey])
    up = (vote > 0)
    down = (vote < 0)
    blank = (vote == 0) \
            or (down and key in up_voted) \
            or (up and key in down_voted)
    if blank: 
        if key in up_voted:
            user.up_voted[dkey].remove(key)
            return ds.redis.hset(key, 'up', 0) 
        if key in down_voted:
            user.down_voted[dkey].remove(key)
            return ds.redis.hset(key, 'down', 0)
        else:
            return '1'
    else:
        # check whether user has voted in thread already
        tkey = ds.redis.hget(key, 'parent')
        siblings = ds.redis.hget(tkey, 'children').strip('[]').split(':')
        thread_up = up_voted.intersection(siblings)
        thread_down = down_voted.intersection(siblings)
        # a second vote within a thread displaces the old vote
        if up and thread_up:
            # this loop should run only once, but meh
            for k in thread_up:
                user.up_voted[dkey].remove(k)
                ds.redis.hset(k, 'up', 0)
            user.up_voted[dkey].append(key)
            return ds.redis.hset(key, 'up', 1)
        elif down and thread_down:
            # same for this loop, but meh^2
            for k in thread_down:
                user.down_voted[dkey].remove(k)
                ds.redis.hset(k, 'down', 0)
            user.down_voted[dkey].append(key)
            return ds.redis.hset(key, 'down', 1)
        else:
            # user is voting in new thread
            if up and (len(up_voted) < MAX_UP):
                user.up_voted[dkey].append(key)
                return ds.redis.hset(key, 'up', 1)
            elif down and (len(down_voted) < MAX_DOWN):
                user.down_voted[dkey].append(key)
                return ds.redis.hset(key, 'down', 1)
            else:
                return '0'

if __name__ == "__main__":
    app.debug = True
    app.run()
