#!/bin/sh

if [ ! -d ~/docker ]; then
  echo "Please run setup-docker.sh first."
  exit 1
fi



cp -R configs/docker/prowlarr ~/docker/prowlarr

cd ~/docker/prowlarr
docker-compose up -d