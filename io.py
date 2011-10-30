'''A flask webapp for the data model'''
from data import *
from logic import *
from random import randrange
from datetime import datetime
from flask import Flask, request, render_template
app = Flask(__name__)

state = {}

def rnd():
    return hex(randrange(0,2**64))[2:]

@app.route("/user/<userid>",methods=['GET','PUT'])
def user(userid):
    '''Creates users and gets user summaries'''
    if request.method == 'PUT':
        state.setdefault('user',{})[userid] = User(userid)
        return "1"
    else:
       return str(state['user'].get(userid)) + '\n'

@app.route("/vote/<userid>/<rid>/<int:vote>/", 
    methods=['PUT'])
def vote(userid, rid, vote):
    '''Count an (up/down) vote'''
    u = state['user'][userid]
    r = state['revisions'][rid]
    out = u.vote(r, r.docid, vote)
    return str(out) # t/f for success

@app.route("/document/", methods=['POST','GET'])
def document():
    '''Create new documents or return the list of all documents'''
    if request.method == 'POST':
        name = request.form['name']
        docid = rnd()
        state.setdefault('documents',{})[docid] = Document(name)
        return str(docid)
    else:
        return str(state['documents']) + '\n'
                

@app.route("/document/<docid>/", methods=['POST', 'GET'])
def revision(docid):
    '''Create new threads or get all threads in a document'''
    if request.method == 'POST':
        rid = rnd()
        text = request.form['text']    
        topics = request.form['topics']
        r = Revision(docid, text, rid, topics, [], True)
        state.setdefault('revisions',{})[rid] = r
        return str(rid)
    else:
        r = state.get('revisions',{})
        d = state['documents'].get(docid,[])
        roots = [x for x in r.values() if x.docid==docid and x.root]
        roots = map(rankRevisions, roots)
        roots = rankThreads(roots)
        return render_template('document.html', d=d, r=roots)


@app.route("/revision/<rid>/", methods=['POST', 'GET'])
def fork(rid):
    '''Fork a revision or display all descendants of a revision'''
    try:
        prev = state.get('revisions',{})[rid]
        docid = prev.docid
    except KeyError:
        return 'Sorry, the revision with id "%s" does not exist' % rid
    if request.method == 'POST':
        fid = rnd()
        text = request.form['text']    
        topics = request.form['topics']
        frev = Revision(docid, text, fid, topics, [], False)
        state['revisions'][fid] = frev
        prev.children.append(frev)
        return str(fid)
    else:
        doc = state['documents'].get(docid,[])
        revs = state.get('revisions',{})
        return str(doc) + "\n" + str(prev) + "\n" + "\n".join([str(revs[rid]) for rid in prev.children])

@app.route("/_debug")
def debug():
    raise IndexError


if __name__ == "__main__":
    app.debug = True
    app.run()
