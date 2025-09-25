#!/bin/sh

if [ ! -d ~/docker ]; then
  echo "Please run setup-docker.sh first."
  exit 1
fi

cp -R configs/docker/homepage ~/docker/homepage

cd ~/docker/homepage
docker-compose up -d