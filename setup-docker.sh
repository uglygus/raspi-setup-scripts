#!/bin/sh


sudo apt update
sudo apt upgrade -y
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common



curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh


sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl status docker

sudo usermod -aG docker $USER


mkdir -p ~/docker
