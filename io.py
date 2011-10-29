'''A flask webapp for the data model'''
from data import *
from random import randrange
from datetime import datetime
from flask import Flask, request, render_template
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

@app.route("/vote/<userid>/<rid>/<int:vote>/", 
    methods=['PUT'])
def vote(userid, rid, vote):
    u = state['user'][userid]
    r = state['revisions'][rid]
    print vote
    u.vote(r, r.docid, vote)
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
def thread(docid):
    if request.method == 'POST':
        text = request.form['text']    
        topics = request.form['topics']
        rid = rnd()
        r = Revision(docid, text, rid, topics, [], True)
        state.setdefault('revisions',{})[rid] = r
        return str(rid)
    else:
        r = state.get('revisions',{})
        d = state['documents'].get(docid,[])
        return render_template('document.html', d=d, r=[x for x in r.values() if x.docid==docid])

def rankRevisions(revision):
    '''Should be handed a root revision'''
    pass

if __name__ == "__main__":
    app.debug = True
    app.run()
