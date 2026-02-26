#!/bin/bash
TEST_ID="1.4_B"
LOG_PRODUCER_1="producer_test_${TEST_ID}_1.log"
LOG_PRODUCER_2="producer_test_${TEST_ID}_2.log"
LOG_PRODUCER_3="producer_test_${TEST_ID}_3.log"
LOG_CONSUMER="consumer_test_${TEST_ID}.log"
STATS_FILE_60="stats_${TEST_ID}_60s.txt"
STATS_FILE_180="stats_${TEST_ID}_180s.txt"

echo "Resetting environment..."
./reset_env.sh

TOPIC_NAME="click-events-${TEST_ID}"
echo "Creating topic $TOPIC_NAME..."
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 2

echo "Applying Config B (3 Producers)..."
# Same properties as A
cat <<EOF > ClickStream-Producer/src/main/resources/producer.properties
acks=all
retries=5
bootstrap.servers=localhost:9092, localhost:9094
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=com.utils.JavaSerializer
batch.size=16384
linger.ms=0
EOF

echo "Starting Consumer..."
(cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" > ../$LOG_CONSUMER 2>&1) &
CONSUMER_PID=$!
echo "Consumer PID: $CONSUMER_PID"

echo "Starting Producer 1..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER_1 2>&1) &
PRODUCER_PID_1=$!
echo "Producer 1 PID: $PRODUCER_PID_1"

echo "Starting Producer 2..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER_2 2>&1) &
PRODUCER_PID_2=$!
echo "Producer 2 PID: $PRODUCER_PID_2"

echo "Starting Producer 3..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER_3 2>&1) &
PRODUCER_PID_3=$!
echo "Producer 3 PID: $PRODUCER_PID_3"

echo "Waiting 60s for first stats..."
sleep 60
docker stats --no-stream > $STATS_FILE_60

echo "Waiting 120s for second stats..."
sleep 120
docker stats --no-stream > $STATS_FILE_180

echo "Stopping Producers..."
kill $PRODUCER_PID_1
kill $PRODUCER_PID_2
kill $PRODUCER_PID_3
wait $PRODUCER_PID_1
wait $PRODUCER_PID_2
wait $PRODUCER_PID_3

echo "Waiting 10s for consumer to finish..."
sleep 10
echo "Stopping Consumer..."
kill $CONSUMER_PID
wait $CONSUMER_PID

echo "Test Complete."
