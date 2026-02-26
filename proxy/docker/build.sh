#!/bin/bash

LOCAL_TAG=simple-proxy:latest
REMOTE_TAG=894608133151.dkr.ecr.eu-central-1.amazonaws.com/job-prospector/$LOCAL_TAG

docker build -t $LOCAL_TAG .
docker tag $LOCAL_TAG $REMOTE_TAG
docker push $REMOTE_TAG
