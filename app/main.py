from typing import List
from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.core.database import Base, engine, get_db
from app.models.climate import ClimateData
from app.schemas.climate import ClimateDataResponse

# Cria as tabelas no PostgreSQL ao subir a aplicação
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Dashboard Climático e Logístico API",
    description="API para ingestão e monitoramento de dados de exportação de frutas",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "API online e conectada ao banco de dados."}

@app.get("/api/climate", response_model=List[ClimateDataResponse])
def get_climate_records(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    records = db.query(ClimateData).order_by(ClimateData.recorded_at.desc()).offset(skip).limit(limit).all()
    return records