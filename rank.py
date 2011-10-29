from math import gamma

def rankDoc(docid, topic=None):
    '''Ranks all threads in a document, optionally filtered by topic'''
    revs = state.get('revisions', {})
    if topic is None:
        root_revs = [r for r in revs if r.isRoot and (r.docid == docid)]
    else:
        root_revs = [r for r in revs if r.isRoot and (r.docid == docid) 
                                        and (topic in r.topics)]
    return rankThreads(root_revs)

def rankThreads(root_revs):
    '''Ranks all threads under supplied list of root nodes'''
    # get score for each thread
    thread_scores = [scoreThread(r) for r in root_revs]
    # sort list of tuples (score, rev)
    tuples = sorted(zip(thread_scores, root_revs))
    # output list of root revisions and scores
    scores, revs = zip(*tuples)
    return revs, scores

def rankRevisions(root_rev):
    '''Ranks all revisions under supplied thread root'''
    scores, revs = scoreChildren(root_rev)
    # sort list of tuples (score, rev)
    tuples = sorted(zip(scores, revs))
    # output list of root revisions and scores
    scores, revs = zip(*tuples)
    return revs, scores

def scoreThread(root_rev):
    '''Returns score for thread, based on total up and down votes'''
    u, d = sumVotes(root_rev)
    return score(u, d)

def scoreChildren(rev):
    '''This may need optimization'''
    rscore = probAcceptance(r.up, r.down)
    scores = [1]
    revs = [rev]
    for child in rev.children:
        cscore(probAcceptance(r.up, r.down))
        revs.append(child)
        scores.append(cscore/rscore)
        # get scores from 
        s,r = scoreChildren(child)
        scores.extend(s)
        revs.extend(r)
    return scores, revs

def sumVotes(rev):
    '''Sums votes over revision and all its children'''
    # optimize this if it turns out to be slow
    up = rev.up
    down = rev.down
    for child in rev.children:
        u, d = totalVotes(child)
        up += u
        down += d
    return up, down    

def probConsensus(up, down, f):
    '''Probability that a fraction of the population of at least f
    votes for a proposal.

        p(mu>f | up, down) = Beta(f, up, down)
    '''
    pass

def probAcceptance(up, down):
    '''Probability that a proposal would be accepted by majority vote. 
    Given a set of votes, this is equal to the expectation value
    of the beta distribution associated with the votes

        p =  Int_mu Beta(mu | up, down) mu 
          =  (up + 1) / (up + down + 2)
    '''
    return (up + 1.) / (up + down + 2.)
