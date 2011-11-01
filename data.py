'''Data model for collaborative manifesto maker'''

class User:
    def __init__(self, userid):
        self.userid = userid
        self.createdRev = []
        self.upVotesRev = []
        self.downVotesRev = []
        self.THRESHOLD_UP = 3
        self.THRESHOLD_DOWN = 3


    def __repr__(self):
        return self.userid + \
          "\nUp: %s"%("\n".join(self.upVotesRev)) + \
          "\nDown: %s"%("\n".join(self.downVotesRev))
   
    def vote(self, revision, docid, vote):
        assert(vote == 1 or vote == 0)
        if vote == 1:
            u = [v for v in self.upVotesRev if v[0] == docid]
            if len(u) + 1 > self.THRESHOLD_UP:
                return 0
            self.upVotesRev.append((docid,revision.rid))
        else:
            d = [v for v in self.downVotesRev if v[0] == docid]
            if len(d) + 1 > self.THRESHOLD_DOWN:
                return 0
            self.downVotesRev.append((docid,revision.rid))
        up = 1 if vote == 1 else 0
        down = 1 if vote == 0 else 0
        revision.addVote(up, down)
        return 1

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

    def inherit(self, rev):
        self.votesFor = rev.votesFor
        self.votesAgainst = rev.votesAgainst

    def __repr__(self):
        return self.text + "\nFor: %s\nAgainst: %s\nScore: %s\n"%(self.votesFor,self.votesAgainst,self.score)

    def addVote(self, up, down):
        self.votesFor += up
        self.votesAgainst += down
        self.score = self.calculateScore()
        for child in self.children:
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


