'''Data model for collaborative manifesto maker'''

class User:
    THRESHOLD = 3
    def __init__(self, userid):
        self.userid = userid
        self.createdRev = []
        self.votesRev = []
   
    def vote(self, revision, up, down):
        if len(self.votesRev) >= THRESHOLD:
            raise
        else: #ultimately revision ids
            revision.addVote(up, down)
            

class Revision:
    def __init__(self, docid, text, rid, topics, children=[], root=False):
        '''Indexed on docid'''
        self.docid = docid
        self.root = root
        self.text = text
        self.rid = rid
        self.children = children
        self.votesFor = 0
        self.votesAgainst = 0
        self.topics = topics
        self.creationTime = None
        self.score = None

    def addVote(self, up, down):
        self.votesFor += up
        self.votesAgainst += down
        self.score = self.calculateScore()
        for child in children:
            child.addVote(up, down)

    def addFork(self, revision):
        self.children.append(revision)

    def calculateScore(self):
        pass

class Document:
    def __init__(self):
        self.topics = set()
        self.topicCacheDirty = False

    def addThread(self, revision):
        self.threads.append(revision)

    def rankThreads(self):
        pass

def rankRevisions(revision):
    '''Should be handed a root revision'''
    pass
