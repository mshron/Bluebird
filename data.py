'''Data model for collaborative manifesto maker'''

class User:
    THRESHOLD_UP = 3
    THRESHOLD_DOWN = 3
    def __init__(self, userid):
        self.userid = userid
        self.createdRev = []
        self.upVotesRev = []
        self.downVotesRev = []

    def __repr__(self):
        return self.userid + \
          "\nUp: %s"%("\n".join(self.upVotesRev)) + \
          "\nDown: %s"%("\n".join(self.downVotesRev))
   
    def vote(self, revision, up, down):
        assert(up==0 or down==0)
        if up >= 0:
            if len(self.upVotesRev) >= THRESHOLD_UP:
                raise
        else:
            if len(self.downVotesRev) >= THRESHOLD_DOWN:
                raise
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

    def __repr__(self):
        return self.text + "\nFor: %s\nAgainst: %s\nScore: %s\n"%(self.votesFor,self.votesAgainst,self.score)

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
    def __init__(self, name):
        self.topics = set()
        self.topicCacheDirty = False
        self.name = name

    def __repr__(self):
        return self.name + "\n" + "\t".join(self.topics)

    def rankThreads(self):
        pass


