#!/bin/bash
TEST_ID="3.1"
LOG_PRODUCER_A="producer_test_${TEST_ID}_A.log"
LOG_PRODUCER_B="producer_test_${TEST_ID}_B.log"

echo "Resetting environment..."
./reset_env.sh

TOPIC_NAME="click-events-${TEST_ID}"
echo "Creating topic $TOPIC_NAME..."
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 2

# Find Leader
LEADER_ID=$(docker exec docker-kafka1-1 kafka-topics --describe --topic $TOPIC_NAME --bootstrap-server kafka1:29092 | grep "Leader:" | awk -F'Leader: ' '{print $2}' | awk -F'\t' '{print $1}')
echo "Leader for $TOPIC_NAME is Broker $LEADER_ID"

if [ "$LEADER_ID" == "2" ]; then
    LEADER_CONTAINER="docker-kafka1-1"
else
    LEADER_CONTAINER="docker-kafka2-1"
fi
echo "Leader Container is $LEADER_CONTAINER"

echo "Applying Config A (Resilient)..."
cat <<EOF > ClickStream-Producer/src/main/resources/producer.properties
acks=all
retries=5
bootstrap.servers=localhost:9092, localhost:9094
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=com.utils.JavaSerializer
batch.size=1000
linger.ms=0
EOF

echo "Starting Producer A..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=500 -Dsleep.max=1000 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER_A 2>&1) &
PRODUCER_PID=$!
echo "Producer PID: $PRODUCER_PID"

echo "Running for 30s..."
sleep 30

echo "Killing Leader Broker $LEADER_CONTAINER..."
docker stop $LEADER_CONTAINER

echo "Running for another 30s..."
sleep 30

echo "Stopping Producer..."
kill $PRODUCER_PID
wait $PRODUCER_PID

echo "Restarting Cluster for Config B..."
./reset_env.sh
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 2

# Find Leader again (might be different)
LEADER_ID=$(docker exec docker-kafka1-1 kafka-topics --describe --topic $TOPIC_NAME --bootstrap-server kafka1:29092 | grep "Leader:" | awk -F'Leader: ' '{print $2}' | awk -F'\t' '{print $1}')
echo "Leader for $TOPIC_NAME is Broker $LEADER_ID"

if [ "$LEADER_ID" == "2" ]; then
    LEADER_CONTAINER="docker-kafka1-1"
else
    LEADER_CONTAINER="docker-kafka2-1"
fi
echo "Leader Container is $LEADER_CONTAINER"

echo "Applying Config B (Fragile)..."
cat <<EOF > ClickStream-Producer/src/main/resources/producer.properties
acks=1
retries=0
bootstrap.servers=localhost:9092, localhost:9094
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=com.utils.JavaSerializer
batch.size=1000
linger.ms=0
EOF

echo "Starting Producer B..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=500 -Dsleep.max=1000 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER_B 2>&1) &
PRODUCER_PID=$!
echo "Producer PID: $PRODUCER_PID"

echo "Running for 30s..."
sleep 30

echo "Killing Leader Broker $LEADER_CONTAINER..."
docker stop $LEADER_CONTAINER

echo "Running for another 30s..."
sleep 30

echo "Stopping Producer..."
kill $PRODUCER_PID
wait $PRODUCER_PID

echo "Test Complete."
