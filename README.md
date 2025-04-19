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

## 4. Prepare Python Environment
1. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 6. Configure the `.env` File
Create a `.env` file in the project root with these entries:
```dotenv
# Celery broker (Redis URL)
BROKER_URL=redis://<YOUR_LOCAL_IP>:6379/0
```
>[!WARNING]
> Replace `<YOUR_LOCAL_IP>` with your Mac’s LAN IP (e.g. `10.40.6.206`).


## 7. Launch Celery Workers
On each machine run from the project root:
```bash
source venv/bin/activate
celery -A tasks worker --loglevel=info --concurrency=1 --hostname=worker@%h
```

## 8. Enqueue Tasks with the Producer
On the central server, run:
```bash
source venv/bin/activate
python producer.py
```



## Team Members
- [Fabian Fernandez](https://github.com/FabsCR)
- [Josue Matamoros](https://github.com/JosueMatamoros)
- [Andres Esquivel](https://github.com/AndresEsquivelG)