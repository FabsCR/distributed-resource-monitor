import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Float, String, DateTime, MetaData, Table
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()
DB_URL  = os.getenv("DATABASE_URL")
raw = os.getenv("CORS_ORIGINS", "")
ORIGINS = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


# 1) Conexión y definición de la tabla “current_metrics”
engine = create_engine(DB_URL)
meta = MetaData()

current_metrics = Table(
    "current_metrics", meta,
    Column("hostname",     String,   primary_key=True),
    Column("cpu_percent",  Float,    nullable=False),
    Column("ram_total_mb", Float,    nullable=False),
    Column("ram_used_mb",  Float,    nullable=False),
    Column("ram_percent",  Float,    nullable=False),
    Column("temperature",  Float,    nullable=True),
    Column("timestamp",    DateTime, nullable=False),
)

meta.create_all(engine)
Session = sessionmaker(bind=engine)

# 2) Modelo Pydantic acorde al payload
class MetricsIn(BaseModel):
    hostname:     str
    cpu_percent:  float
    ram_total_mb: float
    ram_used_mb:  float
    ram_percent:  float
    temperature:  float | None
    timestamp:    float

# 3) FastAPI + CORS
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4) Endpoint que hace UPSERT
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
        # ON CONFLICT DO UPDATE para hostname
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

# 5) Devuelve la lista de hosts con su estado actual
@app.get("/metrics")
def list_current_metrics():
    """
    Retorna un array con un objeto por cada hostname,
    conteniendo las últimas métricas.
    """
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
