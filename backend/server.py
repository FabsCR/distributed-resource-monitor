import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Float, String, DateTime,
    MetaData, Table, Boolean, Integer, select, desc
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
DB_URL  = os.getenv("DATABASE_URL")
raw     = os.getenv("CORS_ORIGINS", "")
ORIGINS = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]

# Connection and table definitions
engine = create_engine(DB_URL)
meta   = MetaData()

# Current metrics table
current_metrics = Table(
    "current_metrics", meta,
    Column("hostname",     String, primary_key=True),
    Column("cpu_percent",  Float,  nullable=False),
    Column("ram_total_mb", Float,  nullable=False),
    Column("ram_used_mb",  Float,  nullable=False),
    Column("ram_percent",  Float,  nullable=False),
    Column("temperature",  Float,  nullable=True),
    Column("timestamp",    DateTime, nullable=False),
)

# Log table for heavy tasks
task_status_log = Table(
    "task_status_log", meta,
    Column("id",         Integer, primary_key=True, autoincrement=True),
    Column("hostname",   String,  nullable=False),
    Column("task_name",  String,  nullable=False),
    Column("delivered",  Boolean, nullable=False),
    Column("created_at", DateTime, nullable=False),
)

# Create tables if they don't exist
meta.create_all(engine)
Session = sessionmaker(bind=engine)

# Pydantic model for receiving metrics
class MetricsIn(BaseModel):
    hostname:     str
    cpu_percent:  float
    ram_total_mb: float
    ram_used_mb:  float
    ram_percent:  float
    temperature:  float | None
    timestamp:    float

# FastAPI app and CORS configuration
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint for upserting into current_metrics
@app.post("/metrics")
def receive(m: MetricsIn):
    s = Session()
    try:
        stmt = insert(current_metrics).values(
            hostname     = m.hostname,
            cpu_percent  = m.cpu_percent,
            ram_total_mb = m.ram_total_mb,
            ram_used_mb  = m.ram_used_mb,
            ram_percent  = m.ram_percent,
            temperature  = m.temperature,
            timestamp    = datetime.fromtimestamp(m.timestamp)
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["hostname"],
            set_={
                "cpu_percent":  stmt.excluded.cpu_percent,
                "ram_total_mb": stmt.excluded.ram_total_mb,
                "ram_used_mb":  stmt.excluded.ram_used_mb,
                "ram_percent":  stmt.excluded.ram_percent,
                "temperature":  stmt.excluded.temperature,
                "timestamp":    stmt.excluded.timestamp,
            }
        )
        s.execute(stmt)
        s.commit()
        return {"status": "ok"}
    except Exception as e:
        s.rollback()
        raise HTTPException(500, str(e))
    finally:
        s.close()

# Returns the list of hosts with their current status
@app.get("/metrics")
def list_current_metrics():
    s = Session()
    rows = s.query(current_metrics).all()
    s.close()
    return [
        {
            "hostname":     r.hostname,
            "cpu_percent":  r.cpu_percent,
            "ram_total_mb": r.ram_total_mb,
            "ram_used_mb":  r.ram_used_mb,
            "ram_percent":  r.ram_percent,
            "temperature":  r.temperature,
            "timestamp":    r.timestamp.isoformat(),
        }
        for r in rows
    ]

# Endpoint to retrieve heavy tasks logs
@app.get("/logs")
def read_logs(limit: int = 10):
    s = Session()
    try:
        stmt = (
            select(
                task_status_log.c.hostname,
                task_status_log.c.task_name,
                task_status_log.c.delivered,
                task_status_log.c.created_at,
            )
            .order_by(desc(task_status_log.c.created_at))
            .limit(limit)
        )
        rows = s.execute(stmt).all()
    except Exception as e:
        raise HTTPException(500, str(e))
    finally:
        s.close()

    return [
        {
            "hostname":   h,
            "task_name":  t,
            "delivered":  d,
            "created_at": ct.isoformat(),
        }
        for h, t, d, ct in rows
    ]
