#!/bin/bash

set -e

KAFKA_VERSION="3.7.0"
SCALA_VERSION="2.13"
INSTALL_DIR="/opt/kafka"

echo "Updating system..."
sudo apt update -y

echo "Installing Java..."
sudo apt install openjdk-17-jdk wget -y

echo "Getting EC2 public IP..."
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)

echo "Public IP: $PUBLIC_IP"

echo "Downloading Kafka..."
wget https://downloads.apache.org/kafka/$KAFKA_VERSION/kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz

echo "Extracting Kafka..."
tar -xzf kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz

sudo mv kafka_${SCALA_VERSION}-${KAFKA_VERSION} $INSTALL_DIR

cd $INSTALL_DIR

echo "Generating cluster ID..."
CLUSTER_ID=$(bin/kafka-storage.sh random-uuid)

echo "Cluster ID: $CLUSTER_ID"

echo "Creating KRaft configuration..."

sudo tee config/kraft/server.properties > /dev/null <<EOF
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@$PUBLIC_IP:9093

listeners=PLAINTEXT://:9092,CONTROLLER://:9093
advertised.listeners=PLAINTEXT://$PUBLIC_IP:9092

listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT

log.dirs=/tmp/kraft-combined-logs
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
EOF

echo "Formatting storage..."

bin/kafka-storage.sh format -t $CLUSTER_ID -c config/kraft/server.properties

echo "Starting Kafka..."

nohup bin/kafka-server-start.sh config/kraft/server.properties > kafka.log 2>&1 &

sleep 10

echo "Kafka Started!"

echo "Testing topic creation..."

bin/kafka-topics.sh \
--create \
--topic test-topic \
--bootstrap-server $PUBLIC_IP:9092 \
--partitions 1 \
--replication-factor 1 || true

echo ""
echo "Kafka running at:"
echo "$PUBLIC_IP:9092"