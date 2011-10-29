#!/usr/bin/env bash
## A testing script, using curl

curl -X PUT http://127.0.0.1:5000/user/0
docid=`curl -F name="Testing Document" http://127.0.0.1:5000/document/`
echo "Document: "$docid
rid=`curl -F text="I think we should think about our children, but not our children's children. Because the idea of children having sex is gross" -F topics="education morality jackhandy" http://127.0.0.1:5000/document/${docid}/`
echo "Request: "$rid
curl -X PUT http://127.0.0.1:5000/vote/0/${rid}/1/0
curl http://127.0.0.1:5000/document/${docid}/
