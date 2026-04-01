#!/bin/bash -ex

LOCAL_TAG=scraper:latest
REMOTE_TAG=894608133151.dkr.ecr.eu-central-1.amazonaws.com/job-prospector/$LOCAL_TAG

cd ..
docker build -t $LOCAL_TAG -f docker/Dockerfile .
docker tag $LOCAL_TAG $REMOTE_TAG
docker push $REMOTE_TAG
