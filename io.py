'''A flask webapp for the data model'''
from data import *
from flask import Flask, request
from random import randrange
from datetime import datetime
app = Flask(__name__)

state = {}

def rnd():
    return str(randrange(0,2**64))

@app.route("/user/<userid>",methods=['GET','PUT'])
def user(userid):
    if request.method == 'PUT':
        state.setdefault('user',{})[userid] = User(userid)
        return "1"
    else:
       return str(state['user'].get(userid)) + '\n'

@app.route("/vote/<userid>/<rid>/<int:up>/<int:down>", 
    methods=['PUT'])
def vote(userid, rid, up, down):
    u = state['user'][userid]
    u.vote(state['revisions'][rid], up, down)
    return '1'

@app.route("/document/", methods=['POST','GET'])
def document():
    if request.method == 'POST':
        name = request.form['name']
        docid = rnd()
        state.setdefault('documents',{})[docid] = Document(name)
        return str(docid)
    else:
        return str(state['documents']) + '\n'
                

@app.route("/document/<docid>/", methods=['POST', 'GET'])
def revision(docid):
    if request.method == 'POST':
        rid = rnd()
        text = request.form['text']    
        topics = request.form['topics']
        r = Revision(docid, text, rid, topics, [], True)
        state.setdefault('revisions',{})[rid] = r
        return str(rid)
    else:
        revs = state.get('revisions',{})
        doc = state['documents'].get(docid,[])
        return str(doc) + "\n" + "\n".join([str(x) for x in revs.values() 
                                            if x.docid==docid])

@app.route("/revision/<rid>/", methods=['POST', 'GET'])
def fork(rid):
    try:
        prev = state.get('revisions',{})[rid]
        docid = prev.docid
    except KeyError:
        return 'Sorry, the revision with id "%s" does not exist' % rid
    if request.method == 'POST':
        fid = rnd()
        text = request.form['text']    
        topics = request.form['topics']
        frev = Revision(docid, text, fid, topics, [], True)
        state['revisions'][fid] = frev
        prev.children.append(fid)
        return str(fid)
    else:
        doc = state['documents'].get(docid,[])
        revs = state.get('revisions',{})
        return str(doc) + "\n" + str(prev) + "\n" + "\n".join([str(revs[rid]) for rid in prev.children])


def rankRevisions(revision):
    '''Should be handed a root revision'''
    pass

if __name__ == "__main__":
    app.debug = True
    app.run()
