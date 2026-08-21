# Pod Templates

Ready-to-use pod configurations for common services.

## Databases

### PostgreSQL

```yaml
- name: postgres
  image: postgres:16
  servicePorts: [5432]
  vars:
    POSTGRES_USER: appuser
    POSTGRES_PASSWORD: changeme
    POSTGRES_DB: appdb
    PGDATA: /var/lib/postgresql/data/pgdata
  volumes:
    - name: postgres-data
      size: 10Gi
      mountPath: /var/lib/postgresql/data  # data dir goes in the pgdata subdirectory via PGDATA
```

**Connect from other pods:**
```yaml
vars:
  DATABASE_URL: postgresql://appuser:changeme@postgres.pod:5432/appdb
```

### MySQL

```yaml
- name: mysql
  image: mysql:8
  servicePorts: [3306]
  vars:
    MYSQL_ROOT_PASSWORD: rootpassword
    MYSQL_DATABASE: appdb
    MYSQL_USER: appuser
    MYSQL_PASSWORD: changeme
  volumes:
    - name: mysql-data
      size: 10Gi
      mountPath: /var/lib/mysql
```

**Connect:**
```yaml
vars:
  DATABASE_URL: mysql://appuser:changeme@mysql.pod:3306/appdb
```

### MongoDB

```yaml
- name: mongodb
  image: mongo:7
  servicePorts: [27017]
  vars:
    MONGO_INITDB_ROOT_USERNAME: admin
    MONGO_INITDB_ROOT_PASSWORD: changeme
  volumes:
    - name: mongo-data
      size: 10Gi
      mountPath: /data/db
```

**Connect:**
```yaml
vars:
  MONGODB_URI: mongodb://admin:changeme@mongodb.pod:27017
```

### Redis

```yaml
- name: redis
  image: redis:7-alpine
  servicePorts: [6379]
  command: redis-server --appendonly yes
  volumes:
    - name: redis-data
      size: 1Gi
      mountPath: /data
```

**Connect:**
```yaml
vars:
  REDIS_URL: redis://redis.pod:6379
```

### Redis with Password

```yaml
- name: redis
  image: redis:7-alpine
  servicePorts: [6379]
  command: redis-server --appendonly yes --requirepass mypassword
  volumes:
    - name: redis-data
      size: 1Gi
      mountPath: /data
```

**Connect:**
```yaml
vars:
  REDIS_URL: redis://:mypassword@redis.pod:6379
```

## Vector Databases

### Qdrant

```yaml
- name: qdrant
  image: qdrant/qdrant:latest
  servicePorts: [6333, 6334]
  volumes:
    - name: qdrant-data
      size: 5Gi
      mountPath: /qdrant/storage
```

**Connect:**
```yaml
vars:
  QDRANT_URL: http://qdrant.pod:6333
  QDRANT_GRPC_URL: http://qdrant.pod:6334
```

### Weaviate

```yaml
- name: weaviate
  image: semitechnologies/weaviate:latest
  servicePorts: [8080]
  vars:
    QUERY_DEFAULTS_LIMIT: "25"
    AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: "true"
    PERSISTENCE_DATA_PATH: /var/lib/weaviate
  volumes:
    - name: weaviate-data
      size: 5Gi
      mountPath: /var/lib/weaviate
```

**Connect:**
```yaml
vars:
  WEAVIATE_URL: http://weaviate.pod:8080
```

### Milvus (Standalone)

```yaml
- name: milvus
  image: milvusdb/milvus:latest
  servicePorts: [19530, 9091]
  command: milvus run standalone
  vars:
    ETCD_ENDPOINTS: etcd.pod:2379
  volumes:
    - name: milvus-data
      size: 10Gi
      mountPath: /var/lib/milvus

- name: etcd
  image: quay.io/coreos/etcd:v3.5.5
  servicePorts: [2379, 2380]
  command: etcd --advertise-client-urls=http://0.0.0.0:2379 --listen-client-urls=http://0.0.0.0:2379
```

### ChromaDB

```yaml
- name: chroma
  image: chromadb/chroma:latest
  servicePorts: [8000]
  vars:
    IS_PERSISTENT: "TRUE"
    PERSIST_DIRECTORY: /chroma/data
  volumes:
    - name: chroma-data
      size: 5Gi
      mountPath: /chroma/data
```

**Connect:**
```yaml
vars:
  CHROMA_URL: http://chroma.pod:8000
```

## AI/ML Services

### Ollama

```yaml
- name: ollama
  image: ollama/ollama:latest
  servicePorts: [11434]
  useGPU: true
  command: ollama serve
  volumes:
    - name: ollama-models
      size: 50Gi
      mountPath: /root/.ollama
```

**Connect:**
```yaml
vars:
  OLLAMA_HOST: http://ollama.pod:11434
```

### vLLM

```yaml
- name: vllm
  image: vllm/vllm-openai:latest
  servicePorts: [8000]
  useGPU: true
  command: python -m vllm.entrypoints.openai.api_server --model mistralai/Mistral-7B-Instruct-v0.2
  vars:
    HF_TOKEN: your-huggingface-token
```

**Connect:**
```yaml
vars:
  VLLM_URL: http://vllm.pod:8000/v1
```

### Text Generation Inference (TGI)

```yaml
- name: tgi
  image: ghcr.io/huggingface/text-generation-inference:latest
  servicePorts: [80]
  useGPU: true
  vars:
    MODEL_ID: mistralai/Mistral-7B-Instruct-v0.2
    HF_TOKEN: your-huggingface-token
```

**Connect:**
```yaml
vars:
  TGI_URL: http://tgi.pod:80
```

## Message Queues

### RabbitMQ

```yaml
- name: rabbitmq
  image: rabbitmq:3-management
  servicePorts: [5672, 15672]
  vars:
    RABBITMQ_DEFAULT_USER: admin
    RABBITMQ_DEFAULT_PASS: changeme
  volumes:
    - name: rabbitmq-data
      size: 2Gi
      mountPath: /var/lib/rabbitmq
```

**Connect:**
```yaml
vars:
  AMQP_URL: amqp://admin:changeme@rabbitmq.pod:5672
  RABBITMQ_MANAGEMENT_URL: http://rabbitmq.pod:15672
```

### NATS

```yaml
- name: nats
  image: nats:latest
  servicePorts: [4222, 8222]
  command: -js
  volumes:
    - name: nats-data
      size: 1Gi
      mountPath: /data
```

**Connect:**
```yaml
vars:
  NATS_URL: nats://nats.pod:4222
```

## Web Servers & Proxies

### Nginx

```yaml
- name: nginx
  image: nginx:alpine
  path: /
  servicePorts: [80]
```

### Caddy

```yaml
- name: caddy
  image: caddy:2-alpine
  path: /
  servicePorts: [80, 443]
```

### Traefik

```yaml
- name: traefik
  image: traefik:v3.0
  path: /
  servicePorts: [80, 8080]
  command: --api.insecure=true --providers.docker=false
```

## Application Runtimes

### Node.js

```yaml
- name: node-app
  image: node:20-alpine
  path: /
  servicePorts: [3000]
  vars:
    NODE_ENV: production
    PORT: "3000"
  command: node server.js
```

### Python (FastAPI/Flask)

```yaml
- name: python-app
  image: python:3.12-slim
  path: /
  servicePorts: [8000]
  command: gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### Go

```yaml
- name: go-app
  image: golang:1.22-alpine
  path: /
  servicePorts: [8080]
  command: ./main
```

### Java (Spring Boot)

```yaml
- name: java-app
  image: eclipse-temurin:21-jre
  path: /
  servicePorts: [8080]
  vars:
    JAVA_OPTS: -Xmx512m
  command: java -jar app.jar
```

## Search Engines

### Elasticsearch

```yaml
- name: elasticsearch
  image: elasticsearch:8.12.0
  servicePorts: [9200, 9300]
  vars:
    discovery.type: single-node
    xpack.security.enabled: "false"
    ES_JAVA_OPTS: -Xms512m -Xmx512m
  volumes:
    - name: es-data
      size: 10Gi
      mountPath: /usr/share/elasticsearch/data
```

**Connect:**
```yaml
vars:
  ELASTICSEARCH_URL: http://elasticsearch.pod:9200
```

### Meilisearch

```yaml
- name: meilisearch
  image: getmeili/meilisearch:latest
  servicePorts: [7700]
  vars:
    MEILI_MASTER_KEY: changeme
  volumes:
    - name: meili-data
      size: 5Gi
      mountPath: /meili_data
```

**Connect:**
```yaml
vars:
  MEILISEARCH_URL: http://meilisearch.pod:7700
  MEILISEARCH_KEY: changeme
```

## Caching

### Memcached

```yaml
- name: memcached
  image: memcached:alpine
  servicePorts: [11211]
  command: memcached -m 256
```

**Connect:**
```yaml
vars:
  MEMCACHED_URL: memcached.pod:11211
```

## Monitoring

### Prometheus

```yaml
- name: prometheus
  image: prom/prometheus:latest
  servicePorts: [9090]
  volumes:
    - name: prometheus-data
      size: 5Gi
      mountPath: /prometheus
```

### Grafana

```yaml
- name: grafana
  image: grafana/grafana:latest
  path: /grafana
  servicePorts: [3000]
  vars:
    GF_SECURITY_ADMIN_PASSWORD: admin
  volumes:
    - name: grafana-data
      size: 1Gi
      mountPath: /var/lib/grafana
```

## Complete Stack Examples

### MERN Stack

```yaml
application:
  name: mern-app
  pods:
    - name: frontend
      image: my-react-app:latest
      path: /
      servicePorts: [3000]
      vars:
        REACT_APP_API_URL: http://api.pod:5000

    - name: api
      image: my-express-api:latest
      path: /api
      servicePorts: [5000]
      vars:
        MONGODB_URI: mongodb://admin:changeme@mongodb.pod:27017/appdb
        JWT_SECRET: your-jwt-secret

    - name: mongodb
      image: mongo:7
      servicePorts: [27017]
      vars:
        MONGO_INITDB_ROOT_USERNAME: admin
        MONGO_INITDB_ROOT_PASSWORD: changeme
      volumes:
        - name: mongo-data
          size: 10Gi
          mountPath: /data/db
```

### RAG Application

```yaml
application:
  name: rag-app
  pods:
    - name: app
      image: my-rag-app:latest
      path: /
      servicePorts: [8000]
      vars:
        OLLAMA_URL: http://ollama.pod:11434
        QDRANT_URL: http://qdrant.pod:6333
        REDIS_URL: redis://redis.pod:6379
      secrets:
        - name: openai-key
          data: sk-your-openai-key
          fileName: openai.key
          mountPath: /var/secrets

    - name: ollama
      image: ollama/ollama:latest
      servicePorts: [11434]
      useGPU: true
      command: ollama serve
      volumes:
        - name: ollama-models
          size: 50Gi
          mountPath: /root/.ollama

    - name: qdrant
      image: qdrant/qdrant:latest
      servicePorts: [6333]
      volumes:
        - name: qdrant-data
          size: 10Gi
          mountPath: /qdrant/storage

    - name: redis
      image: redis:7-alpine
      servicePorts: [6379]
      command: redis-server --appendonly yes
      volumes:
        - name: redis-data
          size: 1Gi
          mountPath: /data
```

### LangChain + Streamlit

```yaml
application:
  name: langchain-demo
  pods:
    - name: app
      image: my-langchain-app:latest
      path: /
      servicePorts: [8501]
      vars:
        OLLAMA_BASE_URL: http://ollama.pod:11434
        CHROMA_URL: http://chroma.pod:8000
      secrets:
        - name: openai-key
          data: sk-your-key
          fileName: api_key
          mountPath: /app/secrets
      command: streamlit run app.py --server.port=8501 --server.address=0.0.0.0

    - name: ollama
      image: ollama/ollama:latest
      servicePorts: [11434]
      useGPU: true

    - name: chroma
      image: chromadb/chroma:latest
      servicePorts: [8000]
      vars:
        IS_PERSISTENT: "TRUE"
      volumes:
        - name: chroma-data
          size: 5Gi
          mountPath: /chroma/data
```
