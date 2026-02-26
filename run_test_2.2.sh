#!/bin/bash
TEST_ID="2.2"
LOG_PRODUCER="producer_test_${TEST_ID}.log"
LOG_CONSUMER_A="consumer_test_${TEST_ID}_A.log"
LOG_CONSUMER_B="consumer_test_${TEST_ID}_B.log"

echo "Resetting environment..."
./reset_env.sh

TOPIC_NAME="click-events-${TEST_ID}"
echo "Creating topic $TOPIC_NAME..."
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 2

echo "Producing Messages (Pre-population)..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER 2>&1) &
PRODUCER_PID=$!
echo "Producer PID: $PRODUCER_PID"
sleep 30
kill $PRODUCER_PID
wait $PRODUCER_PID

echo "Applying Config A (Earliest)..."
cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp-earliest
auto.offset.reset=earliest
EOF

echo "Starting Consumer A..."
(cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" > ../$LOG_CONSUMER_A 2>&1) &
CONSUMER_A_PID=$!
echo "Consumer A PID: $CONSUMER_A_PID"
sleep 30
kill $CONSUMER_A_PID
wait $CONSUMER_A_PID

echo "Applying Config B (Latest)..."
cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp-latest
auto.offset.reset=latest
EOF

echo "Starting Consumer B..."
(cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" > ../$LOG_CONSUMER_B 2>&1) &
CONSUMER_B_PID=$!
echo "Consumer B PID: $CONSUMER_B_PID"
sleep 30
kill $CONSUMER_B_PID
wait $CONSUMER_B_PID

echo "Test Complete."
