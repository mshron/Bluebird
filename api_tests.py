import unittest
import json
import api
import data


class ApiTestCases(unittest.TestCase):
    def setUp(self):
        api.app.debug = True
        self.app = api.app.test_client()
        # generate some sample objects
        self.user = data.User(handle='ginuwine', 
                              name='Ginuwine', 
                              location='US', 
                              bio='Come ride my pony')
        self.doc = data.Document(name='Ponies and Horses')
        self.thread = data.Thread(parent=self.doc)
        self.rev = data.Revision(text='We need more Ponies', 
                                 author=self.user, 
                                 parent=self.thread)

    def put_obj(self, obj):
        url = '/api/%s' % '/'.join(obj.key.split(':'))
        r_put = self.app.put(path=url,
                             data=json.dumps(obj.__dict__), 
                             content_type='application/json')
        self.assertEqual(r_put.status_code, 200,
                         'PUT request on URL=%s returned status: %s' 
                         % (url, r_put.status))
        self.assertEqual(obj.key, r_put.data,
                         'Key returned by server not equal to key requested in url:\n'
                         + '  request: %s\n' % obj.key
                         + '  returned: %s' % r_put.data)

    def post_obj(self, obj):
        url = '/api/%s' % '/'.join(data.collection(obj.key).split(':'))
        r_post = self.app.post(path=url,
                               data=json.dumps(obj.__dict__), 
                               content_type='application/json')
        self.assertEqual(r_post.status_code, 200,
                         'POST request on URL=%s returned status: %s' 
                         % (url, r_post.status))
        self.assertNotEqual(obj.key, r_post.data)

    def get_obj(self, obj):
        url = '/api/%s' % '/'.join(obj.key.split(':'))
        r_get = self.app.get(path=url)
        self.assertEqual(r_get.status_code, 200,
                         'GET request on URL=%s returned status: %s' 
                         % (url, r_get.status))
        attrs = json.loads(r_get.data)
        self.assertEqual(obj.key, attrs['key'],
                         'Key returned by server not equal to key requested in url:\n'
                         + '  request: %s\n' % obj.key
                         + '  returned: %s' % attrs['key'])
    
    def test_doc(self):
        self.put_obj(self.doc)
        self.post_obj(self.doc)
        self.get_obj(self.doc)

    def test_thread(self):
        self.put_obj(self.thread)
        self.post_obj(self.thread)
        self.get_obj(self.thread)

    def test_rev(self):
        self.put_obj(self.rev)
        self.post_obj(self.rev)
        self.get_obj(self.rev)

    def test_user(self):
        self.put_obj(self.user)
        self.post_obj(self.user)
        self.get_obj(self.user)

if __name__ == '__main__':
    unittest.main()