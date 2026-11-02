import json
import os
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WAREHOUSE = os.path.join(ROOT, "data", "warehouse")
PROCESSED = os.path.join(ROOT, "data", "processed")

MODELS = ["first_touch", "last_touch", "linear", "time_decay", "position_based"]

app = FastAPI(
    title="Customer 360 & Marketing Attribution API",
    description="Read-only API over the Customer 360 and multi-touch attribution marts.",
    version="1.0.0",
)


@lru_cache(maxsize=None)
def _load(folder: str, name: str) -> pd.DataFrame:
    path = os.path.join(folder, name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{name} not found. Run `python run_pipeline.py` first.")
    return pd.read_csv(path)


def _records(df: pd.DataFrame) -> list:
    return json.loads(df.to_json(orient="records"))


def _customers() -> pd.DataFrame:
    return _load(WAREHOUSE, "dim_customers_360.csv")


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}


@app.get("/customers", tags=["Customer 360"])
def list_customers(
    segment: str | None = Query(None),
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    df = _customers()
    if segment:
        df = df[df["rfm_segment"].str.lower() == segment.lower()]
    return {"total": int(len(df)), "limit": limit, "offset": offset,
            "data": _records(df.iloc[offset: offset + limit])}


@app.get("/customers/{customer_id}", tags=["Customer 360"])
def get_customer(customer_id: str):
    df = _customers()
    row = df[df["canonical_customer_id"] == customer_id]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Customer '{customer_id}' not found")
    return _records(row)[0]


@app.get("/customers/{customer_id}/identities", tags=["Identity Resolution"])
def get_customer_identities(customer_id: str):
    df = _load(PROCESSED, "int_identity_mapping.csv")
    rows = df[df["canonical_customer_id"] == customer_id]
    if rows.empty:
        raise HTTPException(status_code=404, detail=f"No identities for '{customer_id}'")
    return {"customer_id": customer_id, "linked_nodes": int(len(rows)), "identities": _records(rows)}


@app.get("/segments", tags=["Customer 360"])
def segments():
    return _records(_load(WAREHOUSE, "fct_customer_rfm_segments.csv"))


@app.get("/attribution", tags=["Attribution"])
def attribution(model: str = Query("time_decay")):
    if model not in MODELS:
        raise HTTPException(status_code=422, detail=f"model must be one of {MODELS}")
    df = _load(WAREHOUSE, "agg_campaign_performance_roi.csv")
    cols = ["channel_name", "total_spend_usd", f"revenue_{model}", f"conversions_{model}", f"roas_{model}"]
    return {"model": model, "total_attributed_revenue": round(float(df[f"revenue_{model}"].sum()), 2),
            "channels": _records(df[cols])}


@app.get("/campaigns", tags=["Campaign ROI"])
def campaigns():
    return _records(_load(WAREHOUSE, "agg_campaign_performance_roi.csv"))


@app.get("/campaigns/{channel_name}", tags=["Campaign ROI"])
def campaign(channel_name: str):
    df = _load(WAREHOUSE, "agg_campaign_performance_roi.csv")
    row = df[df["channel_name"].str.lower() == channel_name.lower()]
    if row.empty:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_name}' not found")
    return _records(row)[0]


@app.get("/budget/recommendations", tags=["Budget Optimizer"])
def budget_recommendations():
    df = _load(WAREHOUSE, "agg_budget_reallocation_recommendations.csv")
    return {"total_current_budget": round(float(df["total_spend_usd"].sum()), 2),
            "total_recommended_budget": round(float(df["recommended_budget_usd"].sum()), 2),
            "net_projected_revenue_lift": round(float(df["revenue_lift_usd"].sum()), 2),
            "channels": _records(df)}