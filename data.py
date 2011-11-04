'''Data model for collaborative manifesto maker'''
from random import randrange
import time
import sys
from redis import Redis

# this is how times are stored (chosen to be sortable)
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def rnd():
    '''Generates a random value for usage in keys'''
    return hex(randrange(0,2**64))[2:]

def obj_id(key):
    '''Returns id of object'''
    return key.split(':')[-1]

def parent(key):
    '''Returns key for parent of object'''
    return ':'.join(key.split(':')[:-2])

def collection(key):
    '''Returns key for collection object is a member of'''
    return ':'.join(key.split(':')[:-1])

# def parse(attrs):
#     '''Takes a dictionary representation of a DataModel
#     instance and returns the corresponding object'''
#     obj_type = attrs['type'].split(':')[-1]
#     if not obj_type in DATA_TYPES:
#         raise ValueError('Illegal type for DataModel instance: %s' % obj_type)
#     # parse lists where necessary
#     for key in LIST_ATTRS[obj_type]:
#         if isinstance(attrs[key], basestring):
#             attrs[key] = attrs[key].strip('[]').split(', ')
#     # get object class
#     Obj = globals()[obj_type]
#     # init new object with specified attributes
#     return Obj(**attrs)

def parse(attrs):
    '''Takes a dictionary representation of a DataModel
    instance and returns the corresponding object'''
    attrs = dict(attrs.items())
    obj_type = attrs.pop('type')
    return globals()[obj_type](**attrs)

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
        Reference to object parent. (only used if key does not
        contain parent)
         
    :collection: 
        Name of object collection (only used if not specified
        in key)

    :children: 
        Name of descendant collection, accessible under 
        'key:children'

    :type:
        Explicitly stores type of object so it is passed
        along when serialized.
    '''
    def __init__(self, key=None, parent=None, collection=None, children=None):
        self.type = self.__class__.__name__
        key = key if key else ''
        # check if length of key path implies parent and collection specified
        if len(key.split(':')) < 3:
            # use collection from key if possible
            if len(key.split(':')) == 2:
                collection = key.split(':')[0]
            # construct collection name from class name
            elif not collection:
                collection = self.__class__.__name__ + 's'
            # if unspecified, generate random object id
            obj_id = key.split(':')[-1] if key.split(':')[-1] else rnd()
            # if parent is specified, prepend it on key
            if parent:
                key = '%s:%s:%s' % (parent, collection, obj_id)
            # otherwise collection name starts key
            else:
                key = '%s:%s' % (collection, obj_id)
        # ensure parent of children is key
        children = '%s:%s' % (key, children.split(':')[-1]) if children else ''    
        self.key = key
        self.children = children

    def __eq__(self, other):
        return (self.key == other.key)
    
    def __repr__(self):
        return self.key


class DataSet(object):
    '''BaseClass for sets of object references'''
    def __init__(self, key=None, members=()):
        self.key = key if key else ''
        self.members = list(members)

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
        attrs = self.redis.hgetall(key)
        return parse(attrs)

    def put(self, data):
        '''Writes out a DataModel object'''
        # add object reference to sibling set
        self.redis.sadd(collection(data.key), data.key)
        # write out dict representation of object
        success = self.redis.hmset(data.key, data.__dict__)
        return data.key if success else success

class Document(DataModel):
    def __init__(self, name='', collection='Documents', 
                 children='Threads', **kwargs):
        super(Document, self).__init__(collection=collection, 
                                       children=children, **kwargs)
        self.name = name

        
class Thread(DataModel):
    def __init__(self, root=None, parent=None, topics='Topics',
                 collection='Threads', children='Revisions', **kwargs):
        super(Thread, self).__init__(parent=parent, collection=collection, 
                                     children=children, **kwargs)
        self.root = root
        topics = topics.split(':')[-1] if topics else 'Topics'
        self.topics = '%s:%s' % (self.key, 'Topics')


class Revision(DataModel):
    def __init__(self, text=None, author=None, created=None, up=0, down=0,
                 parent=None, collection='Revisions', children='Forks', **kwargs):
        super(Revision, self).__init__(parent=parent, collection=collection, 
                                       children=children, **kwargs)
        self.text = text
        self.author = '%s' % author
        self.created = created if created else time.strftime(TIME_FORMAT)
        self.up = up
        self.down = down


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