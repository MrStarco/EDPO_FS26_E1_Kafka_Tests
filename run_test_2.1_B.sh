#!/bin/bash
TEST_ID="2.1_B"
LOG_PRODUCER="producer_test_${TEST_ID}.log"
LOG_CONSUMER="consumer_test_${TEST_ID}.log"
STATS_FILE_60="stats_${TEST_ID}_60s.txt"
STATS_FILE_180="stats_${TEST_ID}_180s.txt"
LAG_FILE="lag_${TEST_ID}.txt"
GROUP_ID="grp-lag-2-1-b-$(date +%s)"

echo "Resetting environment..."
./reset_env.sh

TOPIC_NAME="click-events-2-1-b-$(date +%s)"
echo "Creating topic $TOPIC_NAME..."
docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 1 --replication-factor 2

echo "Applying Config B (Slow Consumer)..."
# Slow consumer properties
cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp1
auto.offset.reset=earliest
max.poll.interval.ms=60000
EOF
sed -i '' "s/group.id=grp1/group.id=${GROUP_ID}/" ClickStream-Consumer/src/main/resources/consumer.properties

echo "Starting Consumer (Slow)..."
(cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" -Dprocessing.delay=100 > ../$LOG_CONSUMER 2>&1) &
CONSUMER_PID=$!
echo "Consumer PID: $CONSUMER_PID"

echo "Starting Producer (High Load)..."
(cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER 2>&1) &
PRODUCER_PID=$!
echo "Producer PID: $PRODUCER_PID"

echo "Warm-up: 30s (discarded)..."
sleep 30

echo "Monitoring Lag during 180s measurement..."
: > $LAG_FILE
for i in {1..18}; do
    sleep 10
    echo "Time: ${i}0s" >> $LAG_FILE
    docker exec docker-kafka1-1 kafka-consumer-groups --bootstrap-server kafka1:29092 --describe --group $GROUP_ID >> $LAG_FILE 2>&1
    
    if [ $i -eq 6 ]; then
        echo "Collecting stats at 60s..."
        docker stats --no-stream > $STATS_FILE_60
    fi
    if [ $i -eq 18 ]; then
        echo "Collecting stats at 180s..."
        docker stats --no-stream > $STATS_FILE_180
    fi
done

echo "Stopping Producer..."
kill $PRODUCER_PID
wait $PRODUCER_PID

echo "Waiting 10s for consumer to finish..."
sleep 10
echo "Stopping Consumer..."
kill $CONSUMER_PID
wait $CONSUMER_PID

echo "Test Complete."
