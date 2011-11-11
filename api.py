'''A flask webapp for the data model'''
# TODO: Some API calls need to perform multiple datastore writes. 
# If one of these fails after others have succeeded, then 
# the datastore will be in an inconsistent state. -- JWM 

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

def put(attrs):
    '''write an object in dictionary representation to datastore'''
    obj = data.parse(attrs)
    return ds.put(obj)

# def get(key):
#     '''retrieve an object in JSON representation from datastore'''
#     assert(ds.redis.exists(key))
#     return js.dumps(ds.get(key).__dict__)

def get_all(key):
    '''retrieve a set of object in JSON representation from datastore'''
    assert(ds.redis.exists(key))
    return js.dumps(ds.get_all(key), cls=data.DataEncoder)

def collection_handler(request, col_key):
    '''Default handling for fl.requests on object urls:
    * Write object on post,
    * Retrieve list objects in collection on GET'''
    if request.method in ['POST','PUT']:
        return put(fl.request.json); 
    else:
        return fl.Response(get_all(col_key), mimetype='application/json')

@app.route('/api/users',
            methods=['GET','POST'])
def users():
    key = 'users'
    return collection_handler(fl.request, key)

@app.route('/api/documents',
            methods=['GET','POST'])
def documents():
    key = 'documents'
    return collection_handler(fl.request, key)

@app.route('/api/documents/<doc_id>/revisions',
            methods=['GET','POST'])
def threads(doc_id):
    key = 'Document:%s:revisions' % doc_id
    return collection_handler(fl.request, key)

@app.route('/api/documents/<doc_id>/revisions/<rev_id>',
            methods=['PUT'])
def revision(doc_id, rev_id):
    key = 'Document:%s:revisions' % doc_id
    return collection_handler(fl.request, key)

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

#@app.route('/documents/<doc_id>')
#def dochtml(doc_id):
  
     

if __name__ == "__main__":
    app.debug = True
    app.run()
