#!/bin/bash
TEST_ID="2.3"

LOG_PRODUCER_A="producer_test_${TEST_ID}_A.log"
LOG_PRODUCER_B="producer_test_${TEST_ID}_B.log"
LOG_CONSUMER_A1="consumer_test_${TEST_ID}_A1.log"
LOG_CONSUMER_A2="consumer_test_${TEST_ID}_A2.log"
LOG_CONSUMER_B1="consumer_test_${TEST_ID}_B1.log"
LOG_CONSUMER_B2="consumer_test_${TEST_ID}_B2.log"

STATS_A_60="stats_${TEST_ID}_A_60s.txt"
STATS_A_180="stats_${TEST_ID}_A_180s.txt"
STATS_B_60="stats_${TEST_ID}_B_60s.txt"
STATS_B_180="stats_${TEST_ID}_B_180s.txt"

run_config_same_group() {
  echo "Resetting environment for Config A..."
  ./reset_env.sh

  TOPIC_NAME="click-events-${TEST_ID}-A"
  echo "Creating topic $TOPIC_NAME with 2 partitions..."
  docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 2 --replication-factor 2

  echo "Applying Config A (same consumer group)..."
  cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp-shared
auto.offset.reset=earliest
EOF

  (cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" > ../$LOG_CONSUMER_A1 2>&1) &
  CONSUMER_A1_PID=$!
  (cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" > ../$LOG_CONSUMER_A2 2>&1) &
  CONSUMER_A2_PID=$!

  (cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER_A 2>&1) &
  PRODUCER_PID=$!

  echo "Config A warm-up: 30s (discarded)..."
  sleep 30
  echo "Config A measurement: 180s..."
  sleep 60
  docker stats --no-stream > $STATS_A_60
  sleep 120
  docker stats --no-stream > $STATS_A_180

  kill $PRODUCER_PID
  wait $PRODUCER_PID
  sleep 10
  kill $CONSUMER_A1_PID
  kill $CONSUMER_A2_PID
  wait $CONSUMER_A1_PID
  wait $CONSUMER_A2_PID
}

run_config_different_groups() {
  echo "Resetting environment for Config B..."
  ./reset_env.sh

  TOPIC_NAME="click-events-${TEST_ID}-B"
  echo "Creating topic $TOPIC_NAME with 2 partitions..."
  docker exec docker-kafka1-1 kafka-topics --create --topic $TOPIC_NAME --bootstrap-server kafka1:29092 --partitions 2 --replication-factor 2

  cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp-A
auto.offset.reset=earliest
EOF
  (cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" > ../$LOG_CONSUMER_B1 2>&1) &
  CONSUMER_B1_PID=$!

  cat <<EOF > ClickStream-Consumer/src/main/resources/consumer.properties
bootstrap.servers=localhost:9092, localhost:9094
key.deserializer=org.apache.kafka.common.serialization.StringDeserializer
value.deserializer=com.utils.JavaDeserializer
group.id=grp-B
auto.offset.reset=earliest
EOF
  (cd ClickStream-Consumer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksConsumer" -Dtopic.name="$TOPIC_NAME" > ../$LOG_CONSUMER_B2 2>&1) &
  CONSUMER_B2_PID=$!

  (cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 -Dtopic.name="$TOPIC_NAME" > ../$LOG_PRODUCER_B 2>&1) &
  PRODUCER_PID=$!

  echo "Config B warm-up: 30s (discarded)..."
  sleep 30
  echo "Config B measurement: 180s..."
  sleep 60
  docker stats --no-stream > $STATS_B_60
  sleep 120
  docker stats --no-stream > $STATS_B_180

  kill $PRODUCER_PID
  wait $PRODUCER_PID
  sleep 10
  kill $CONSUMER_B1_PID
  kill $CONSUMER_B2_PID
  wait $CONSUMER_B1_PID
  wait $CONSUMER_B2_PID
}

run_config_same_group
run_config_different_groups

echo "Test Complete."
