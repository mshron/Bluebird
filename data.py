'''Data model for collaborative manifesto maker'''
from random import randrange
import time
import json
import sys
from redis import Redis

# we only allow gets and puts of these types of objects
DATA_TYPES = ['Document', 'Thread', 'Revision', 'User']

# this is how times are stored (chosen to be sortable)
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

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

def get_parent(key):
    '''Returns key for parent of object'''
    return ':'.join(key.split(':')[:-2])

def get_collection(key):
    '''Returns key for collection object is a member of'''
    return ':'.join(key.split(':')[:-1])

def parse(attrs):
    '''Takes a dictionary representation of a DataModel
    instance and returns the corresponding object'''
    obj_type = attrs['type'].split(':')[-1]
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


class DataModel(object):
    '''Base class for DataStore object model. Each DataModel instance
    must have a key property, which indicates its location in the 
    redis backend. Object keys take the format

    key = ParentSet:parent_id:ObjSet:obj_id

    This key encodes its relationship to other objects via

    parent = ParentSet:parent_id
    collection = ParentSet:parent_id:ObjSet
    children = ParentSet:parent_id:ObjSet:obj_id:ChildSet

    :key: 
        Reference to object in dataset. Can be specified
        either as full key or object id.

    :parent:
        Reference to object parent. Overrides ancestors in key and
        collection. 
         
    :collection: 
        Reference to object collection. Implicitly defines parent
        if unspecified and overrides ancestor in key.

    :children: 
        Name of descendant collection, accessible under 
        'key:children'

    :type:
        Explicitly stores type of object so it is passed
        along when serialized.
    '''
    def __init__(self, key=None, parent=None, collection=None, children=None):
        key = key if key else ''
        # if unspecified, generate random object id
        obj_id = key.split(':')[-1] if key.split(':')[-1] else rnd()
        # if unspecified, get collection from key
        collection = collection if collection \
                     else ':'.join(key.split(':')[:-1])
        # if still unspecified, construct it from class name
        collection = collection if collection \
                     else self.__class__.__name__ + 's'
        # if parent is specified, it overrides that of collection and key
        if parent:
            # strip collection to last field
            collection = collection.split(':')[-1]
            key = '%s:%s:%s' % (parent, collection, obj_id)
        else:
            key = '%s:%s' % (collection, obj_id)
        # ensure parent of children is key
        children = '%s:%s' % (key, children.split(':')[-1]) if children else ''    
        self.key = key
        self.parent = parent
        self.collection = collection
        self.children = children

    def __eq__(self, other):
        return (self.key == other.key)
    
    def __repr__(self):
        return self.key


class DataSet(object):
    '''BaseClass for sets of object references'''
    def __init__(self, key=None, members=()):
        self.key = key if key else ''
        self.members = members

    def __eq__(self, other):
        return (self.key == other.key)

    def __nonzero__(self):
        return bool(self.key)
    
    def __repr__(self):
        return self.key


class DataStore(object):
    '''Interface with redis datastore'''

    def __init__(self, *args, **kwargs):
        self.redis = Redis(*args, **kwargs)

    def list(self, key):
        '''Returns a DataSet containing references in collection 
        under key'''
        members = self.redis.smembers(key)
        return DataSet(key=key, members=members)

    def get(self, key):
        '''Retrieves a DataModel object'''
        # retrieve object attributes from datastore
        attrs = self.redis.hgetall(key)
        # parse into corresponding object
        obj_type = attrs.pop('type')
        obj = globals()[obj_type](**attrs)
        return obj

    def put(self, data):
        '''Writes out a DataModel object'''
        # add object reference to sibling set
        self.redis.sadd(data.collection, data.key)
        # write out dict representation of object
        return self.redis.hmset(data.key, data.__dict__)

class Document(DataModel):
    def __init__(self, name='', collection='Documents', 
                 children='Threads', **kwargs):
        super(Document, self).__init__(collection=collection, 
                                       children=children, **kwargs)
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
    def __init__(self, root=None, parent=None, topics='Topics',
                 collection='Threads', children='Revisions', **kwargs):
        super(Thread, self).__init__(parent=parent, collection=collection, 
                                     children=children, **kwargs)
        self.root = root
        topics = topics.split(':')[-1] if topics else 'Topics'
        self.topics = '%s:%s' % (self.key, 'Topics')

    # def to_json(self):
    #     dic = Model.to_json(self)
    #     dic['root'] = dic['root'].to_json()
    #     if 'document' in dic:
    #         dic['document'] = str(dic['document'])
    #     return dic

class Revision(DataModel):
    def __init__(self, text=None, author=None, created=None, up=0, down=0,
                 parent=None, collection='Revisions', children='Forks', **kwargs):
        super(Revision, self).__init__(parent=parent, collection=collection, 
                                       children=children, **kwargs)
        self.text = text
        self.author = author
        self.created = created if created else time.strftime(TIME_FORMAT)
        self.up = up
        self.down = down

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
    def __init__(self, handle=None, name=None, created=None, 
                 location=None, bio=None, 
                 collection='Users', authored='Authored', 
                 up_voted='UpVotes', down_voted='DownVotes', **kwargs):
        super(User, self).__init__(collection=collection, **kwargs)
        self.handle = handle
        self.name = name
        self.location = location
        self.bio = bio
        self.created = created if created else time.strftime(TIME_FORMAT)
        self.authored = '%s:%s' % (self.key, authored.split(':')[-1])
        self.up_voted = '%s:%s' % (self.key, up_voted.split(':')[-1])
        self.down_voted = '%s:%s' % (self.key, down_voted.split(':')[-1])

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

