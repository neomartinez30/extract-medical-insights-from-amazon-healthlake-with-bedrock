from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import boto3
import json
import pandas as pd
from app_fhir import (
    get_database_list,
    get_tables,
    get_patient_id,
    db_summary,
    struct_summary,
    summary_llm,
    query_llm
)

app = FastAPI(title="FHIR Data Access API")

# Pydantic models for request/response validation
class SummaryRequest(BaseModel):
    database: str
    tables: List[str]
    patient_id: str
    prompt_template: str
    model: str = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
    summary_model: str = "us.anthropic.claude-3-sonnet-20240229-v1:0"

class ChatRequest(BaseModel):
    question: str
    context: str
    model: str = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"

class DatabaseInfo(BaseModel):
    databases: List[str]
    tables: Optional[Dict[str, List[str]]] = None
    patient_ids: Optional[List[str]] = None

# API Routes
@app.get("/api/v1/databases", response_model=DatabaseInfo)
async def get_databases():
    """Get list of available databases"""
    try:
        databases = get_database_list('AwsDataCatalog')
        return DatabaseInfo(databases=databases)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/databases/{database}/tables", response_model=DatabaseInfo)
async def get_database_tables(database: str):
    """Get tables for a specific database"""
    try:
        tables = get_tables(database)
        return DatabaseInfo(databases=[database], tables={database: tables})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/databases/{database}/patients", response_model=DatabaseInfo)
async def get_patients(database: str):
    """Get patient IDs from the database"""
    try:
        sql = '''SELECT id FROM healthlake_db.patient;'''
        params = {'db': database, 'model': "us.anthropic.claude-3-5-sonnet-20240620-v1:0"}
        patient_ids = get_patient_id(sql, params)
        return DatabaseInfo(databases=[database], patient_ids=patient_ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/summary")
async def get_patient_summary(request: SummaryRequest):
    """Get consolidated and FHIR section summaries for a patient"""
    try:
        params = {
            'table': request.tables,
            'db': request.database,
            'model': request.model,
            'summary-model': request.summary_model,
            'id': request.patient_id,
            'template': request.prompt_template
        }
        
        # Get summaries using existing functions
        summary, fhir_tables = db_summary([request.tables[0], params])
        
        return {
            "consolidated_summary": summary,
            "fhir_section_summary": fhir_tables
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
async def chat_with_summary(request: ChatRequest):
    """Chat with the medical summary"""
    try:
        system_prompt = "You are a medical expert."
        prompts = f'''Here is a medical record:
<record>
{request.context}
</record>

Review the medical record thoroughly.
Provide an answer to the question if available in the medical record.
Do not include or reference quoted content verbatim in the answer.
If the question cannot be answered by the document, say so.

Question: {request.question}?'''

        params = {'model': request.model}
        response = summary_llm(prompts, params, system_prompt, None)
        
        return {
            "response": response
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
