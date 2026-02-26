#!/bin/bash
TEST_ID="1.4_A"
LOG_PRODUCER="producer_test_${TEST_ID}.log"
LOG_CONSUMER="consumer_test_${TEST_ID}.log"
STATS_FILE_60="stats_${TEST_ID}_60s.txt"
STATS_FILE_180="stats_${TEST_ID}_180s.txt"

echo "Resetting environment..."
./reset_env.sh

TOPIC_NAME="click-events-${TEST_ID}"
echo "Creating topic $TOPIC_NAME..."
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 2

echo "Applying Config A (1 Producer)..."
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
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER 2>&1) &
PRODUCER_PID=$!
echo "Producer PID: $PRODUCER_PID"

echo "Waiting 60s for first stats..."
sleep 60
docker stats --no-stream > $STATS_FILE_60

echo "Waiting 120s for second stats..."
sleep 120
docker stats --no-stream > $STATS_FILE_180

echo "Stopping Producer..."
kill $PRODUCER_PID
wait $PRODUCER_PID

echo "Waiting 10s for consumer to finish..."
sleep 10
echo "Stopping Consumer..."
kill $CONSUMER_PID
wait $CONSUMER_PID

echo "Test Complete."
