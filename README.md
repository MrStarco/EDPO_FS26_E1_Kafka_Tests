# Lab02Part3 - Multiple Brokers & External Controller

This lab demonstrates a Kafka cluster setup with a dedicated **External Controller** and **Multiple Brokers**. The goal is to experiment with fault tolerance and leader election. This lab builds upon This lab builds upon [Lab02Part1](https://github.com/scs-edpo/lab02Part1-kafka-producer-consumer) and [Lab02Part2](https://github.com/scs-edpo/lab02Part2-kafka-EyeTracking). Only new concepts are introduced. 

## Infrastructure

The infrastructure consists of three Docker services defined in [docker/docker-compose.yml](docker/docker-compose.yml):

1.  **controller**: A dedicated node responsible for cluster metadata and leadership election.
2.  **kafka1**: Broker node.
3.  **kafka2**: Another broker node.

The **Controller** and **Brokers** are configured as follow:

| Parameter | Applies To | Description |
| :--- | :--- | :--- |
| `KAFKA_NODE_ID` | All | A unique integer identifier for each node in the cluster (Controller: 1, Brokers: 2 & 3). |
| `KAFKA_PROCESS_ROLES` | All | Specifies the role of the node. The controller is set to `controller`, and brokers are set to `broker`. |
| `KAFKA_LISTENERS` | All | Defines the ports the node listens on. <br>• **Controller**: Listens on port 9093 (`CONTROLLER`).<br>• **Brokers**: Listen on port 2909x (`INTERNAL`) and 909x (`EXTERNAL`). |
| `KAFKA_CONTROLLER_QUORUM_VOTERS` | All | The connection string for the voting controller nodes (`1@controller:9093`). |
| `KAFKA_CONTROLLER_LISTENER_NAMES` | All | Defines which listener name is used for controller communication (`CONTROLLER`). |
| `KAFKA_ADVERTISED_LISTENERS` | Brokers | The addresses clients and other brokers use to connect.<br>• `INTERNAL`: Maps to the Docker service name (e.g., `kafka1:29092`) for inter-broker replication.<br>• `EXTERNAL`: Maps to `localhost:9092/9094` for external clients (e.g., the Java Producer). |
| `KAFKA_LISTENER_SECURITY_PROTOCOL_MAP` | Brokers | Maps listener names to security protocols. We map `INTERNAL`, `EXTERNAL`, and `CONTROLLER` to `PLAINTEXT`. |
| `KAFKA_INTER_BROKER_LISTENER_NAME` | Brokers | Specifies that `INTERNAL` is the listener used for data replication between brokers. |
| `KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR` | Brokers | Set to `2`. Ensures that consumer group offsets are replicated across both brokers for high availability. |
| `KAFKA_DEFAULT_REPLICATION_FACTOR` | Brokers | Set to `2`. Ensures that any new topic created without explicit settings is replicated across both brokers. |


## Components

### 1. ClickStream-Producer

*   **Class**: [`com.examples.ClicksProducer`](ClickStream-Producer/src/main/java/com/examples/ClicksProducer.java)
*   **Behavior and Implementation Details**:

    *   **Cluster Connection**: The producer connects to both brokers as defined in [`producer.properties`](ClickStream-Producer/src/main/resources/producer.properties):
        ```properties
        bootstrap.servers=localhost:9092, localhost:9094
        ```
        This ensures that if one broker is down on startup, the client can try the other.

    *   **Fault Tolerance Settings**:
        The [`producer.properties`](ClickStream-Producer/src/main/resources/producer.properties) are tuned for high resilience to handle broker failures:
        *   `retries=5`: If the leader is not available (e.g., during an election), the producer will retry sending.
        *   `acks=all`: The leader will wait for the full set of in-sync replicas to acknowledge the record.

    *   **Topic Creation with Replication**:
        Inside `createTopic()`, we explicitly set the replication factor to `2`. This ensures that every partition has a copy on both `kafka1` and `kafka2`.
        ```java
        // NewTopic(String name, int numPartitions, short replicationFactor)
        NewTopic newTopic = new NewTopic(topicName, numPartitions, (short) 2);
        ```
        
    *   **Cluster State Monitoring (Debug Feature)**:
        The main loop includes a check to print metadata whenever the partition leadership or in sync replicates change. This allows you to visually confirm failover in real-time:
        ```java
        Node leader = partitionInfo.leader();
        List<Node> isr = partitionInfo.isr();

        // Convert List<Node> to int[] for printing
        int[] inSyncReplicas = isr.stream().mapToInt(Node::id).toArray();
        String currentIsrString = Arrays.toString(inSyncReplicas);
        // ...

        // Check if Leader OR ISR has changed
        if ((leader != null && leader.id() != previousLeaderId) || !currentIsrString.equals(previousIsrString)) {
              
              int leaderId = (leader != null) ? leader.id() : -1;
              System.out.println("Current Leader: " + leaderId+ " host: "+leader.host()+ " port: "+leader.port());
              System.out.println("In Sync Replicates: " + currentIsrString);
        ```

### 2. ClickStream-Consumer
*   **Class**: `com.examples.ClicksConsumer`
*   **Behavior**:
    *   Consumes events from `click-events` topic.
    *   Prints received values and partition information.
*   **Code Changes**:
    *   [ClicksConsumer.java](ClickStream-Consumer/src/main/java/com/examples/ClicksConsumer.java): Identical to Lab02Part2.
    *   [consumer.properties](ClickStream-Consumer/src/main/resources/consumer.properties): Updated to include both brokers in the bootstrap configuration:
        ```properties
        bootstrap.servers=localhost:9092, localhost:9094
        ```


## Tutorial: Leader Election in Action


Follow these steps to observe leader election in action:

1.  Navigate to the docker directory:
    ```sh
    cd docker
    ```
2.  Start the cluster:
    ```sh
    docker compose up --build
    ```
    *Wait until all services are healthy and running.*

3.  **Start Consumer**: Run [`ClickStream-Consumer`](ClickStream-Consumer/).
4.  **Start Producer**: Run [`ClickStream-Producer`](ClickStream-Producer/).
    *   Observe the console output. You will see the current **Leader** (e.g., ID 2 or 3) and the **ISR (In-Sync Replicas)** list (e.g., `[2, 3]`).
5.  **Kill the Leader Broker**:
    *   Identify which broker is the leader (e.g., if Leader is 2, it corresponds to `kafka1`).
    *   Stop that container:
        ```sh
        docker stop docker-kafka1-1
        # or find the name via `docker ps`
        ```
6.  **Observe Failover**:
    *   The Producer output should show the **Leader** switching to the remaining broker (e.g., ID 3).
    *   The **ISR** list will shrink to `[3]`.


7.  **Your Turn:**
    *   Try different values for `retries` (e.g., `0` instead of `5`) in [`producer.properties`](ClickStream-Producer/src/main/resources/producer.properties).
    *  Try shorter sleep times between generated clicks in [`ClicksProducer.java`](ClickStream-Producer/src/main/java/com/examples/ClicksProducer.java) (e.g., `Thread.sleep(150)` instead of `Thread.sleep(getRandomNumber(500, 5000))`).
    *   Kill the leader broker during production and compare the produced event IDs vs. the consumed event IDs.
    *   **What do you notice about message loss?  Under which configuration(s) do you observe gaps in the consumed sequence?**
    * Try different values for `acks` (e.g., `0`, `1`, `all`) in [`producer.properties`](ClickStream-Producer/src/main/resources/producer.properties).
    *   Try using a callback with `send()` in [`ClicksProducer.java`](ClickStream-Producer/src/main/java/com/examples/ClicksProducer.java) instead of “send and forget”:

        ```java
        producer.send(
            new ProducerRecord<String, Clicks>(
                topic,      // topic
                clickEvent  // value
            ),
            (metadata, exception) -> {
                if (exception != null) {
                    System.err.println("Error sending message: " + exception.getMessage());
                }
            }
        );
        ```
    *   Kill the leader broker during production.
    *   **Under which configuration(s) is/are message loss silent ?**







