#!/bin/bash
# AWS EC2 Free Tier Deployment Script for BioAttend AI
# This script installs Docker and starts the application stack

# 1. Update and install Docker
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "dt [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update
sudo apt-get install -y docker-ce docker-compose

# 2. Add current user to docker group
sudo usermod -aG docker ${USER}

# 3. Increase Swap Space (CRITICAL for 1GB RAM Free Tier)
# This prevents InsightFace from crashing the server
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 4. Clone and Start (User will need to do this part manually)
echo "-------------------------------------------------------"
echo "EC2 Environment Ready!"
echo "Next steps:"
echo "1. Clone your repo: git clone <your-repo-url>"
echo "2. CD into it: cd ojt4"
echo "3. Run: docker-compose up -d"
echo "-------------------------------------------------------"
