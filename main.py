from typing import Union
from fastapi import FastAPI
import os,json
from fastapi.middleware.cors import CORSMiddleware
from invoice import routes as open_ai_route

app = FastAPI(title='Invoice_Parser', version='1.0.0')
app.include_router(open_ai_route.router, prefix="/api/V1/invoice_parser")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Status": "Alive"}