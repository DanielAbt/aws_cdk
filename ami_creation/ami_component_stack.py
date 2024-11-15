from textwrap import dedent

from aws_cdk import aws_imagebuilder as imagebuilder


class AmiComponentStack:
    def __init__(
        self,
        scope,
    ):
        self.scope = scope

    def testing_component(self, properties):
        if properties["environment"] == "Production":
            env = "-p"
        else:
            env = ""

        bucket_script = properties["s3.bucket.name"]

        return imagebuilder.CfnComponent(
            self.scope,
            "MachineComponent",
            name="MachineComponent",
            description="Custom setup for AMI",
            platform="Linux",
            version=properties["ami.component.version"],
            tags={
                "python_version": "3.8",
                "component": "custom_component",
            },
            data=dedent(
                """
name: MachineComponent
description: Custom setup 
schemaVersion: 1.0
phases:
  - name: build
    steps:
      - name: customSetup
        action: ExecuteBash
        inputs:
          commands:
            - |
                #!/bin/bash -xe

                # Create necessary directories
                mkdir -p /home/ubuntu/Downloads
                mkdir -p /home/ubuntu/tmp
                mkdir -p /home/ubuntu/.local
                mkdir -p /home/ubuntu/.config
                mkdir -p /usr/local/bin

                sudo chown -R ubuntu:ubuntu /home/ubuntu/

                # Update and install packages
                sudo apt-get -y update
                sudo apt-get -y -f install build-essential \
                  curl \
                  emacs \
                  htop \
                  mc \
                  multitail \
                  tree \
                  vim \
                  rpl \
                  cython \
                  desktop-file-utils \
                  netcat \
                  libgomp1 \
                  xdg-utils \
                  xvfb \
                  zstd \
                  ca-certificates \
                  rsync \
                  grsync \
                  tar \
                  jq

                # Install awscli2
                cd /home/ubuntu/Downloads
                curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                unzip awscliv2.zip
                ./aws/install -i /usr/local/aws-cli -b /usr/local/bin
                
                aws configure list
                # Set default AWS region
                mkdir -p /home/ubuntu/.aws
                echo "[default]" > /home/ubuntu/.aws/config
                echo "region=us-east-1" >> /home/ubuntu/.aws/config

                # Install Docker Engine
                sudo apt-get remove docker docker-engine docker.io containerd runc > /dev/null || true
                curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor \
                  -o /usr/share/keyrings/docker-archive-keyring.gpg
                echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
                  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
                  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
                
                sudo apt-get update
                sudo apt-get -y install docker-ce docker-ce-cli \
                  containerd.io \
                  gnupg \
                  lsb-release
                
                sudo systemctl enable docker
                sudo /lib/systemd/systemd-sysv-install enable docker
                sudo chmod 666 /var/run/docker.sock
                sudo gpasswd -a ubuntu docker
                newgrp docker

                # Install python3.8 dependences
                sudo apt-get install -y -f python3-pip \
                  python3-tk \
                  gcc \
                  make \
                  openssl \
                  libffi-dev \
                  libgdbm-dev \
                  libsqlite3-dev \
                  libssl-dev \
                  zlib1g-dev

                python3.8 -mpip install --upgrade pip
                sudo apt-get -y install ufw \
                  libsystemd-dev \
                  hibagent \
                  language-selector-gnome \
                  command-not-found \
                  cloud-init \
                  ec2-hibinit-agent

                # # Set link from /usr/bin/python3 to /user/local/bin/python3
                ln -s /usr/bin/python3 /usr/local/bin/python3

                # # Set link from /usr/bin/python3.8 to /user/local/bin/python3.8
                ln -s /usr/bin/python3.8 /usr/local/bin/python3.8
            
                # Install cloudwatch Agent
                cd /home/ubuntu/Downloads
                wget https://s3.us-east-1.amazonaws.com/amazoncloudwatch-agent-us-east-1/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
                dpkg -i -E ./amazon-cloudwatch-agent.deb
                sudo systemctl restart amazon-cloudwatch-agent
"""
            ),
        )

    