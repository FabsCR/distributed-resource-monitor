# Distributed Resource Monitor
This is the first project for the Operating Systems course.

It implements a distributed system composed of multiple nodes that cooperate to execute tasks while being automatically monitored in real-time. The system dynamically distributes workloads based on the current usage of each node's resources (CPU, memory, storage, and network) to ensure efficient and balanced task execution.

> [!TIP]
> These instructions are for configuring the server on **macOS**

## macOS Server Configuration

### 1. Install Redis with Homebrew
```bash
brew update
brew install redis
```

### 2. Start Redis as a service
```bash
brew services start redis
```

### 3. Verify Redis connection
```bash
redis-cli ping
# Expected response:
# PONG
```

### 4. Install Docker
```bash 
   brew install --cask docker
   open /Applications/Docker.app
```

### 5. Run MinIO container
```bash
docker run -d --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=<YOUR_USER>" \
  -e "MINIO_ROOT_PASSWORD=<YOUR_8_CHARACTERS_PASSWORD>" \
  -v ~/minio/data:/data \
  minio/minio server /data --console-address ":9001"
```

## 6. Prepare Python Environment
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 7. Configure the `.env` File
Create a `.env` file in the project root with these entries:
```dotenv
# Celery broker (Redis URL)
BROKER_URL=redis://<YOUR_LOCAL_IP>:6379/0
MINIO_ROOT_USER=<YOUR_USER>
MINIO_ROOT_PASSWORD=<YOUR_PASSWORD>
```
>[!WARNING]
> Replace `<YOUR_LOCAL_IP>` with your Mac’s LAN IP (e.g. `10.40.6.206`).
> Replace `<YOUR_USER>` whit the user that you configure in docker 
> Replace `<YOUR_PASSWORD>` whit the password that you use in your docker configuration 

## 8. Launch Postgres server  
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## 9. Launch Celery Workers

### macOS

#### Metrics Worker (with Beat)
```bash
source venv/bin/activate
celery -A tasks worker --queues=metrics --concurrency=1 --hostname="$(whoami)@%h" -B --loglevel=info
```

#### Heavy Worker
```bash
source venv/bin/activate
celery -A tasks worker --queues=heavy --concurrency=1 --hostname="$(whoami)@%h" --loglevel=info
```

---

### Windows

> **Note:** On Windows, it’s recommended to use the `solo` pool because the default `prefork` pool may not work properly.

#### Metrics Worker (with Beat)
```powershell
# Activate your virtual environment first
celery -A tasks worker -P solo --queues=metrics --concurrency=1 --hostname="metrics@%h" -B --loglevel=info
```

#### Heavy Worker
```powershell
# Activate your virtual environment first
celery -A tasks worker -P solo --queues=heavy --concurrency=1 --hostname="heavy@%h" --loglevel=info
```

## 10. Enqueue Tasks with the Producer
On the central server, run:
```bash
source venv/bin/activate
python producer.py
```

## Team Members
- [Fabian Fernandez](https://github.com/FabsCR)
- [Josue Matamoros](https://github.com/JosueMatamoros)
- [Andres Esquivel](https://github.com/AndresEsquivelG)