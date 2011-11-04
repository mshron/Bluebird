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

# open datastore instance (threadsafe)
ds = data.DataStore()

# initialize dummy user (no authentication implemented yet)
user = data.User(handle='wonka', name='willie', location='UK', bio='i make chocolate')

# define maximum up and down votes (not sure where this should live yet)
MAX_UP = 3
MAX_DOWN = 3

# def put_json(key, json):
#     '''write an object in JSON representation to datastore,
#     updating parent objects if necessary'''
#     attrs = json.loads(json)
#     # ensure object key matches post url
#     attrs['key'] = key
#     # check if url has parent
#     parent_key = ':'.join(key.split(':')[:-2])
#     if parent_key:
#         # check that parent reference exists
#         assert(ds.redis.exists(parent_key))
#         # ensure parent referenced in object matches url
#         attrs['parent'] = parent_key
#         # update children of parent
#         pobj = ds.get(parent_key)
#         if not key in pobj.children:
#             pobj.children.append(key)
#             # write parent to datastore
#             ds.put(pobj)
#     # write object to datastore
#     ds.put(data.parse(attrs))
#     return '1'

def put_json(key, attrs):
    '''write an object in dictionary representation to datastore,
    updating parent objects if necessary'''
    # ensure object key matches post url
    obj = data.parse(attrs)
    obj.key = key
    return ds.put(obj)

def get_json(key):
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
        return put_json(obj_key, request.json)
    else:
        json = get_json(obj_key)
        return fl.Response(json, mimetype='application/json')

def collection_handler(request, col_key):
    '''Default handling for fl.requests on object urls:
    * Add object with new id to collection on POST,
    * Retrieve list objects in collection on GET'''
    if request.method == 'POST':
        obj_id = data.rnd()
        obj_key = '%s:%s' % (col_key, obj_id) 
        return put_json(obj_key, fl.request.json); 
    else:
        json = list_json(col_key)
        return fl.Response(json, mimetype='application/json')

@app.route('/api/Documents',
            methods=['GET','PUT'])
def documents():
    key = 'Documents'
    return collection_handler(fl.request, key)

@app.route('/api/Documents/<doc_id>/Threads',
            methods=['GET','PUT'])
def threads(doc_id):
    key = 'Documents:%s:Threads' % doc_id
    return collection_handler(fl.request, key)

@app.route('/api/Documents/<doc_id>/Threads/<thread_id>/Revisions',
            methods=['GET','PUT'])
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
            put_json(key, json)
            # the parent revision needs updating, since 
            # the fork parent (updated in put_json) is the thread
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

# @app.route("/document/<docid>/", methods=['POST', 'GET'])
# def document(docid):
#     '''Create new threads or get all threads in a document'''
#     if fl.request.method == 'POST':
#         rev_id = rnd()
#         text = fl.request.form['text']    
#         topics = fl.request.form['topics']
#         r = Revision(docid, text, rev_id, topics, [], True)
#         state.setdefault('revisions',{})[rev_id] = r
#         return str(rev_id)
#     else:
#         r = state.get('revisions',{})
#         d = state['documents'].get(docid,[])
#         roots = [x for x in r.values() if x.docid==docid and x.root]
#         roots = map(rankRevisions, roots)
#         roots = rankThreads(roots)
#         return render_template('document.html', d=d, r=roots)


# @app.route("/revision/<rev_id>/", methods=['POST', 'GET'])
# def fork(rev_id):
#     '''Fork a revision or display all descendants of a revision'''
#     try:
#         prev = state.get('revisions',{})[rev_id]
#         docid = prev.docid
#     except KeyError:
#         return 'Sorry, the revision with id "%s" does not exist' % rev_id
#     if fl.request.method == 'POST':
#         fork_id = rnd()
#         text = fl.request.form['text']    
#         topics = fl.request.form['topics']
#         frev = Revision(docid, text, fork_id, topics, [], False)
#         frev.inherit(prev)
#         state['revisions'][fork_id] = frev
#         prev.children.append(frev)
#         return str(fork_id)
#     else:
#         doc = state['documents'].get(docid,[])
#         revs = state.get('revisions',{})
#         return str(doc) + "\n" + str(prev) + "\n" + "\n".join([str(revs[rev_id]) for rev_id in prev.children])

# @app.route("/_debug")
# def debug():
#     raise IndexError

# @app.route("/vote/<userev_id>/<rev_id>/<int:vote>/", 
#     methods=['PUT'])
# def vote(userev_id, rev_id, vote):
#     '''Count an (up/down) vote'''
#     u = state['user'][userev_id]
#     r = state['revisions'][rev_id]
#     out = u.vote(r, r.docid, vote)
#     return str(out) # t/f for success



if __name__ == "__main__":
    app.debug = True
    app.run()
