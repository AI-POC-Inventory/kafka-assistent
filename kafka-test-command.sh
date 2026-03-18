bin/kafka-topics.sh \
--create \
--topic test-topic-1 \
--bootstrap-server $(curl -s http://checkip.amazonaws.com):9092 \
--partitions 1 \
--replication-factor 1 || true

bin/kafka-topics.sh --list --bootstrap-server $(curl -s http://checkip.amazonaws.com):9092

bin/kafka-storage.sh format -t =$(bin/kafka-storage.sh random-uuid) -c config/kraft/server.properties

gcloud run deploy kafka-mcp --source . --region asia-south1 --allow-unauthenticated --set-env-vars KAFKA_BROKER=13.223.75.210:9092