#!/bin/bash
TEST_ID="3.2"
LOG_PRODUCER_A="producer_test_${TEST_ID}_A.log"
LOG_PRODUCER_B="producer_test_${TEST_ID}_B.log"
LOG_CONSUMER_A="consumer_test_${TEST_ID}_A.log"
LOG_CONSUMER_B="consumer_test_${TEST_ID}_B.log"

echo "Resetting environment..."
./reset_env.sh

TOPIC_NAME_A="click-events-${TEST_ID}_A"
echo "Creating topic $TOPIC_NAME_A with RF=2..."
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME_A --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 2 --config min.insync.replicas=2

# Find Leader
LEADER_ID=$(docker exec docker-kafka1-1 kafka-topics --describe --topic $TOPIC_NAME_A --bootstrap-server kafka1:29092 | grep "Leader:" | awk -F'Leader: ' '{print $2}' | awk -F'\t' '{print $1}')
echo "Leader for $TOPIC_NAME_A is Broker $LEADER_ID"

if [ "$LEADER_ID" == "2" ]; then
    LEADER_CONTAINER="docker-kafka1-1"
else
    LEADER_CONTAINER="docker-kafka2-1"
fi
echo "Leader Container is $LEADER_CONTAINER"

echo "Applying Config A (High Durability)..."
cat <<EOF > ClickStream-Producer/src/main/resources/producer.properties
acks=all
retries=5
bootstrap.servers=localhost:9092, localhost:9094
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=com.utils.JavaSerializer
batch.size=1000
linger.ms=0
EOF

cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp-3.2-A
auto.offset.reset=earliest
EOF

echo "Starting Consumer A..."
(cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME_A" > ../$LOG_CONSUMER_A 2>&1) &
CONSUMER_PID=$!
echo "Consumer PID: $CONSUMER_PID"

echo "Starting Producer A..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=100 -Dsleep.max=500 -Dtopic.name="$TOPIC_NAME_A" > ../$LOG_PRODUCER_A 2>&1) &
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

echo "Waiting 10s for consumer..."
sleep 10
kill $CONSUMER_PID
wait $CONSUMER_PID

echo "Restarting Cluster for Config B..."
./reset_env.sh

TOPIC_NAME_B="click-events-${TEST_ID}_B"
echo "Creating topic $TOPIC_NAME_B with RF=1..."
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME_B --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 1

# Find Leader
LEADER_ID=$(docker exec docker-kafka1-1 kafka-topics --describe --topic $TOPIC_NAME_B --bootstrap-server kafka1:29092 | grep "Leader:" | awk -F'Leader: ' '{print $2}' | awk -F'\t' '{print $1}')
echo "Leader for $TOPIC_NAME_B is Broker $LEADER_ID"

if [ "$LEADER_ID" == "2" ]; then
    LEADER_CONTAINER="docker-kafka1-1"
else
    LEADER_CONTAINER="docker-kafka2-1"
fi
echo "Leader Container is $LEADER_CONTAINER"

echo "Applying Config B (Low Durability)..."
cat <<EOF > ClickStream-Producer/src/main/resources/producer.properties
acks=1
retries=0
bootstrap.servers=localhost:9092, localhost:9094
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=com.utils.JavaSerializer
batch.size=1000
linger.ms=0
EOF

cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp-3.2-B
auto.offset.reset=earliest
EOF

echo "Starting Consumer B..."
(cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME_B" > ../$LOG_CONSUMER_B 2>&1) &
CONSUMER_PID=$!
echo "Consumer PID: $CONSUMER_PID"

echo "Starting Producer B..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=100 -Dsleep.max=500 -Dtopic.name="$TOPIC_NAME_B" > ../$LOG_PRODUCER_B 2>&1) &
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

echo "Waiting 10s for consumer..."
sleep 10
kill $CONSUMER_PID
wait $CONSUMER_PID

echo "Test Complete."
