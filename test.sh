#!/usr/bin/env bash
## A testing script, using curl

# set current userid to '0'
succes=`curl -s -X PUT http://127.0.0.1:5000/user/0`

# post a new document with title "Testing Document"
title="Testing Document"
docid=`curl -s -F name="$title" http://127.0.0.1:5000/document/`
echo "Posted Document"
echo "Title: "$title
echo "ID: "$docid
echo ""

# post some new revisions
text="I think we should think about our children, but not our children's children. Because the idea of children having sex is gross" 
topics="education morality jackhandy"
rid1=`curl -s -F text="$text" -F topics="$topics" http://127.0.0.1:5000/document/${docid}/`
echo "Posted Revision"
echo "Text: "$text
echo "Topics: "$topics
echo "ID: "$rid1
echo ""

text="I think we need ponies in every park, rivers of lemonade, and peace between all men." 
topics="animals public_spaces international_affairs"
rid2=`curl -s -F text="$text" -F topics="$topics" http://127.0.0.1:5000/document/${docid}/`
echo "Posted Revision"
echo "Text: "$text
echo "Topics: "$topics
echo "ID: "$rid2
echo ""


text="Better food at schools, higher pay for teachers, and safer neighbourhoods." 
topics="education public_safety"
rid3=`curl -s -F text="$text" -F topics="$topics" http://127.0.0.1:5000/document/${docid}/`
echo "Posted Revision"
echo "Text: "$text
echo "Topics: "$topics
echo "ID: "$rid3
echo ""

# vote for revision 1
curl -s -X PUT http://127.0.0.1:5000/vote/0/${rid1}/0/1
# this should not work, but does
curl -s -X PUT http://127.0.0.1:5000/vote/0/${rid2}/0/2
# this should not work, and does not work
curl -s -X PUT http://127.0.0.1:5000/vote/0/${rid3}/5/3

# query resulting doc
echo "Getting document: $docid"
echo "--"
curl http://127.0.0.1:5000/document/${docid}/
echo "--"
