#!/bin/bash
LOG_FILE="producer_test_1.1_B.log"
STATS_FILE_60="stats_1.1_B_60s.txt"
STATS_FILE_180="stats_1.1_B_180s.txt"

echo "Starting Producer..."
cd ClickStream-Producer && mvn clean compile exec:java -Dexec.mainClass="com.examples.ClicksProducer" -Dsleep.min=1 -Dsleep.max=10 > ../$LOG_FILE 2>&1 &
PID=$!
echo "Producer PID: $PID"

echo "Waiting 60s for first stats..."
sleep 60
docker stats --no-stream > $STATS_FILE_60

echo "Waiting 120s for second stats..."
sleep 120
docker stats --no-stream > $STATS_FILE_180

echo "Stopping Producer..."
kill $PID
wait $PID

echo "Test Complete."
