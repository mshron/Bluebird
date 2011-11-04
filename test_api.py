# generate some sample objects
import data
doc = data.Document(name='Ponies and Horses')
thread = data.Thread(parent=doc)
rev = data.Revision(text='We need more Ponies', author=user, parent=thread)

# put/post to server
import api