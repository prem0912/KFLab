#!/bin/bash -e

sudo mkdir -p /kube_volumes
sudo chown $(whoami):$(id -Gn $(whoami) | cut -d" " -f2) /kube_volumes
mkdir -p /kube_volumes/mysql
mkdir -p /kube_volumes/minio
