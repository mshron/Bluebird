'''Data model for collaborative manifesto maker'''
from random import randrange
import time
import json
import sys
from redis import Redis

# this is how times are stored (chosen to be sortable)
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# we only allow gets and puts of these types of objects
DATA_TYPES = ['Document', 'Thread', 'Revision', 'User']

# since redis does not support nesting lists in hashes,
# lists are stored in a string representation. 
#
# we could detect lists by checking whether the first and
# last characters are '[]', but then you'd have to worry
# about what happens when someone tries to use '[bold]'
# as their username. 
#
# tl;dr -- we'll keep a lookup with list-valued 
# attributes for each data type for now
LIST_ATTRS = {'Document': ['threads'],
              'Thread': ['topics', 'revisions'],
              'Revision': ['children'],
              'User': ['upvoted', 'downvoted', 'created']}

def rnd():
    '''Generates a random value for usage in keys'''
    return hex(randrange(0,2**64))[2:]

def parse(attrs):
    '''Takes a dictionary representation of a DataModel
    instance and returns the corresponding object'''
    obj_type = attrs['key'].split(':')[-1]
    if not obj_type in DATA_TYPES:
        raise ValueError('Illegal type for DataModel instance: %s' % obj_type)
    # parse lists where necessary
    for key in LIST_ATTRS[obj_type]:
        if isinstance(attrs[key], basestring):
            attrs[key] = attrs[key].strip('[]').split(', ')
    # get object class
    Obj = globals()[obj_type]
    # init new object with specified attributes
    return Obj(**attrs)


class DataModel():
    '''Base class for DataStore object model. Each DataModel instance
    must have a key property, which indicates its location in the 
    redis backend. Keys encode relations between objects as:

      obj_key = ParentClass:parent_id:ObjClass:obj_id

    where the parent object could be retrieved from

      parent_key = ParentClass:parent_id
    '''
    def __init__(self, key=None, parent=None, children=[]):
        if key is None:
            key = '%s:%s' % (self.__class__.__name__, rnd())
        if not parent is None:
            self.key = '%s:%s' % (parent, key)
        else:
            self.key = key
        self.parent = parent
        self.children = children

    def __eq__(self, other):
        return (self.key == other.key)
    
    def __repr__(self):
        return self.key


class DataStore():
    '''Interface with redis datastore'''

    def __init__(self, *args, **kwargs):
        self.redis = Redis(*args, **kwargs)

    def documents(self):
        '''Lists keys for each document'''
        return self.redis.smembers('documents')

    def threads(self):
        '''Lists keys for each thread'''
        return self.redis.smembers('threads')

    def revisions(self):
        '''Lists keys for each submitted revision'''
        return self.redis.smembers('revisions')

    def users(self):
        '''Lists keys for each user'''
        return self.redis.smembers('users')

    def get(self, key):
        '''Retrieves a document, revision or user'''
        if not self.redis.exits(key):
            raise KeyError('No object with key: %s' % key)
        # retrieve object attributes from datastore
        attrs = self.redis.hgetall(key)
        # parse into corresponding object
        return parse(attrs)

    def put(self, data):
        '''Writes out a document, revision or user'''
        # determine if object has an allowed class type
        obj_type = data.__class__.__name__
        if not obj_type in DATA_TYPES:
            raise ValueError('Object type not allowed: %s' % obj_type)
        # add object key to corresponding index set
        index_name = obj_type.lower() + 's'
        self.redis.sadd(index_name, data.key)
        # write out dict representation of object
        return self.redis.hmset(data.key, data.__dict__)

    # def to_json(self):
    #     '''returns a JSON serializable dictionary'''
    #     dic = {}
    #     for key, val in self.__dict__.items():
    #         try:
    #             dic[key] = [v.to_json() for v in val]
    #         except (AttributeError, TypeError):
    #             dic[key] = val
    #     return dic


class Document(DataModel):
    def __init__(self, name=None, children=[], key=None):
        DataModel.__init__(self, key=key, children=children)
        self.name = name

    # def topics(self):
    #     topics = set()
    #     for t in threads:
    #         topics.add(t.topics)
    #     return topics

    # def add_thread(self, text, author, topics, created=None):
    #     rev = Revision(text, author, created=created, thread=self)
    #     thread = Thread(text, rev, topics, document=self) 
    #     self.threads.append(thread)
    #     return thread
        
class Thread(DataModel):
    def __init__(self, root=None, topics=[], 
                 parent=None, children=[], key=None):
        DataModel.__init__(self, key=key, parent=parent, children=children)
        self.root = root
        self.topics = topics

    # def to_json(self):
    #     dic = Model.to_json(self)
    #     dic['root'] = dic['root'].to_json()
    #     if 'document' in dic:
    #         dic['document'] = str(dic['document'])
    #     return dic

class Revision(DataModel):
    def __init__(self, text=None, author=None, created=None, 
                 up=0, down=0, parent=None, children=[], key=None):
        DataModel.__init__(self, key=key, parent=parent, children=children)
        self.text = text
        self.author = author
        self.created = created if created else time.strftime(TIME_FORMAT)
        self.up = 0
        self.down = 0

    # def __repr__(self):
    #     return self.text + '\nUp: %s' % self.up \
    #                      + '\nDown: %s' % self.down \
    
    # def add_fork(self, text, author, created=None):
    #     '''Creates a fork from the current revision'''
    #     revision = Revision(text, author, created, thread=self.thread)
    #     self.children.append(revision)
    #     return revision

    # def descendants(self):
    #     '''Returns all descendants of the revision'''
    #     revs = [self]
    #     for r in self.children:
    #         revs += r.descendants()
    #     return revs

    # def to_json(self):
    #     dic = Model.to_json(self)
    #     dic['author'] = str(dic['author'])
    #     if 'thread' in dic:
    #         dic['thread'] = str(dic['thread'])
    #     return dic


class User(DataModel):
    def __init__(self, handle=None, name=None, location=None, bio=None, created=None, 
                 authored=[], up_voted=[], down_voted=[], key=None):
        Model.__init__(key=key)
        self.handle = handle
        self.name = name
        self.location = location
        self.bio = bio
        self.created = created if created else time.strftime(TIME_FORMAT)
        self.authored = []
        self.up_voted = []
        self.down_voted = []

    # def __repr__(self):
    #     return self.handle + \
    #         '\nKey: %s\n' % self.key + \
    #         '\nHandle: %s\n' % self.handle + \
    #         '\nCreated: %s' % ('\n '.join(self.created)) + \
    #         '\nUp: %s' % ('\n '.join(self.up_voted)) + \
    #         '\nDown: %s' % ('\n '.join(self.down_voted))
           
    # def _counts(self, document):
    #     '''returns number of allocated votes within specified document'''
    #     count = lambda v,d: len([r for r in v if r.document == d])
    #     up = count(self.up_voted, document)
    #     down = count(self.down_voted, document)
    #     return up, down

    # def vote(self, revision, vote):
    #     assert(vote == 1 or vote == 0)
    #     up, down = self._counts(revision.document)
    #     if vote == 1 & (up <= User.MAX_UP_VOTES):
    #         self.up_voted.append(revision)
    #         revision.up += 1
    #         return 1
    #     if vote == 0 & (down <= User.MAX_DOWN_VOTES):
    #         self.down_voted.append(revision)
    #         revision.down += 1
    #         return 1
    #     return 0

