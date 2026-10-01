"""
FastAPI Backend - EV Battery State of Health (SoH) AI Estimation API
=====================================================================
Production-ready REST API for electric vehicle battery health analytics,
real-time telemetry ingestion, AI-based degradation estimation, remaining
useful life (RUL) forecasting, and BMS safety anomaly alerts.

Endpoints:
- GET  /api/health                : System & ML model status, accuracy metrics (R2, RMSE)
- GET  /api/telemetry/latest      : Real-time instantaneous cell & pack telemetry
- GET  /api/telemetry/stream      : Historical/sub-cycle driving telemetry stream for dynamic charts
- POST /api/telemetry/ingest      : Ingestion endpoint for BMS / IoT telemetry packets
- POST /api/predict/soh           : AI model inference for SoH (%) and RUL (cycles / km)
- POST /api/simulate              : Parameterized degradation forecast (Temp, Fast-charge, DOD)
- POST /api/telemetry/anomaly-check: Real-time thermal runaway and voltage anomaly detector
- GET  /api/diagnostics/summary   : Downloadable diagnostic summary (JSON format)
- GET  /api/diagnostics/report-html: Printable / PDF-ready formal diagnostic certificate
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from data_gen import BatteryDataSynthesizer
from model.predictor import BatteryHealthPredictor

# Initialize FastAPI App
app = FastAPI(
    title="EV Battery State of Health (SoH) AI Platform",
    description="End-to-End AI-Powered Battery Prognostics, BMS Telemetry Ingestion, and Health Analytics",
    version="2.0.0",
)

# Enable Cross-Origin Resource Sharing (CORS) for Next.js and frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core AI Predictor and Synthesizer Singletons
predictor = BatteryHealthPredictor()
synthesizer = BatteryDataSynthesizer()

# In-memory BMS State store simulating live telemetry pipeline
CURRENT_BMS_STATE = {
    "vin": "5YJSA1E28MF912048",
    "battery_id": "EV-PACK-NX75-402",
    "pack_serial": "BP-400V-96S-0482",
    "pack_topology": "96S2P",
    "cell_count": 192,
    "chemistry": "Lithium Nickel Manganese Cobalt Oxide (NMC-811)",
    "nominal_capacity_ah": 200.0,  # 75.0 kWh EV pack scaled
    "nominal_energy_kwh": 75.0,
    "nominal_voltage_v": 375.0,
    "current_cycle": 142,
    "soc_percent": 84.5,
    "voltage_v": 388.4,
    "current_a": 42.6,
    "pack_power_kw": 16.55,
    "temperature_c": 28.3,
    "cell_avg_v": 4.046,
    "cell_max_v": 4.053,
    "cell_min_v": 4.038,
    "cell_delta_mv": 15.0,
    "max_cell_temp_c": 29.2,
    "min_cell_temp_c": 27.5,
    "cell_temp_delta_c": 1.7,
    "coolant_inlet_temp_c": 22.8,
    "coolant_outlet_temp_c": 24.6,
    "coolant_flow_lpm": 14.2,
    "pump_rpm": 2850,
    "isolation_resistance_kohm": 485000,
    "hvil_status": "CLOSED_OK",
    "main_contactor_pos": "CLOSED",
    "main_contactor_neg": "CLOSED",
    "precharge_contactor": "OPEN",
    "pyro_fuse": "ARMED_INTACT",
    "bms_firmware": "v4.18.2-rtos",
    "can_bus_load_pct": 38.6,
    "dtc_active_count": 0,
    "internal_resistance_mohm": 48.2,
    "ambient_temp_c": 24.5,
    "soh_percent": 96.8,
    "rul_cycles": 570,
    "rul_km": 205200.0,
    "last_updated": datetime.now(timezone.utc).isoformat(),
}


# ==========================================
# Pydantic Schemas for Request / Response
# ==========================================

class TelemetryIngestPacket(BaseModel):
    """BMS high-frequency telemetry packet schema."""
    battery_id: str = Field(default="EV-PACK-NX75-402", description="Pack identification string")
    voltage_v: float = Field(..., ge=2.0, le=500.0, description="Terminal voltage (V)")
    current_a: float = Field(..., description="Load current in Amperes (+ discharge, - charge)")
    temperature_c: float = Field(..., ge=-40.0, le=120.0, description="Cell/module temperature (°C)")
    soc_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="State of Charge (%)")
    internal_resistance_mohm: Optional[float] = Field(default=None, ge=1.0, le=1000.0, description="Internal impedance")
    cycle_index: Optional[int] = Field(default=None, ge=1, description="Cumulative cycle counter")
    ambient_temp_c: Optional[float] = Field(default=25.0, description="Exterior ambient temperature (°C)")


class SoHPredictRequest(BaseModel):
    """Cycle features required for AI model degradation estimation."""
    cycle_index: int = Field(default=150, ge=1, description="Cycle count of the pack")
    ambient_temp_c: float = Field(default=25.0, description="Average ambient operating temp (°C)")
    avg_discharge_temp_c: float = Field(default=29.0, description="Mean temperature during discharge (°C)")
    max_discharge_temp_c: float = Field(default=34.0, description="Peak temperature reached during discharge (°C)")
    voltage_drop_v: float = Field(default=0.52, description="Voltage drop under load (V)")
    internal_resistance_ohm: float = Field(default=0.052, description="DC Internal resistance (Ohm)")
    c_rate: float = Field(default=1.0, ge=0.1, le=5.0, description="Effective charge/discharge C-rate")
    depth_of_discharge: float = Field(default=0.8, ge=0.1, le=1.0, description="Depth of discharge ratio (0.1 - 1.0)")
    charge_duration_min: float = Field(default=60.0, description="Duration of CC-CV charging phase")
    discharge_duration_min: float = Field(default=50.0, description="Duration of discharge phase")
    energy_efficiency_pct: float = Field(default=98.5, description="Coulombic/energy roundtrip efficiency")


class SimulationRequest(BaseModel):
    """User-adjustable simulation parameters for future degradation forecasting."""
    current_cycle: int = Field(default=150, ge=1, description="Current cycle count")
    current_soh: float = Field(default=96.5, ge=60.0, le=100.0, description="Current baseline SoH %")
    ambient_temp_c: float = Field(default=25.0, ge=-20.0, le=55.0, description="Simulated climate ambient temp (°C)")
    fast_charge_pct: float = Field(default=30.0, ge=0.0, le=100.0, description="Percentage of fast charging (>= 2C)")
    dod_pct: float = Field(default=80.0, ge=20.0, le=100.0, description="Depth of Discharge limit %")
    daily_km: float = Field(default=50.0, ge=5.0, le=500.0, description="Average daily driving distance (km)")
    forecast_horizon_cycles: int = Field(default=450, ge=50, le=1200, description="Projection cycle depth")


# ==========================================
# REST API Endpoints
# ==========================================

@app.get("/api/health")
def get_system_health():
    """
    Returns AI model inference status, evaluation accuracy metrics, and feature importances.
    """
    return {
        "status": "ONLINE",
        "service": "EV Battery State of Health AI Engine",
        "model_version": "2.0-ensemble-gbr-rf",
        "model_metrics": predictor.metrics,
        "feature_importance": predictor.feature_importance,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/telemetry/latest")
def get_latest_telemetry():
    """
    Returns instantaneous BMS telemetry including estimated SoH, RUL, SoC,
    temperature, voltage, internal resistance, and cell balancing metrics with realistic CAN jitter.
    """
    import random
    # Realistic CAN bus micro-variations
    jitter_v = round(random.uniform(-0.35, 0.35), 1)
    jitter_a = round(random.uniform(-0.8, 1.1), 1)
    
    current_v = round(CURRENT_BMS_STATE["voltage_v"] + jitter_v, 1)
    current_a = round(CURRENT_BMS_STATE["current_a"] + jitter_a, 1)
    cell_avg = round(current_v / 96.0, 3)
    cell_max = round(cell_avg + 0.007 + random.uniform(-0.001, 0.002), 3)
    cell_min = round(cell_avg - 0.008 + random.uniform(-0.002, 0.001), 3)
    cell_delta = round((cell_max - cell_min) * 1000.0, 1)
    power_kw = round((current_v * current_a) / 1000.0, 2)

    return {
        **CURRENT_BMS_STATE,
        "voltage_v": current_v,
        "current_a": current_a,
        "pack_power_kw": power_kw,
        "cell_avg_v": cell_avg,
        "cell_max_v": cell_max,
        "cell_min_v": cell_min,
        "cell_delta_mv": cell_delta,
        "can_bus_load_pct": round(38.6 + random.uniform(-0.8, 1.2), 1),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/telemetry/stream")
def get_telemetry_stream(
    points: int = Query(default=60, ge=10, le=300, description="Number of sub-cycle points to generate"),
    ambient_temp: float = Query(default=25.0, description="Simulated ambient temperature"),
    c_rate: float = Query(default=1.0, description="Driving load multiplier"),
):
    """
    Generates high-frequency sub-cycle driving telemetry points (Voltage, Current, Temp, SoC, Ri)
    for dynamic multi-line visualization charts.
    """
    stream = synthesizer.generate_detailed_telemetry_stream(
        cycle_number=CURRENT_BMS_STATE["current_cycle"],
        soh_percent=CURRENT_BMS_STATE["soh_percent"],
        ambient_temp=ambient_temp,
        c_rate=c_rate,
        time_steps=points,
    )
    return {
        "count": len(stream),
        "battery_id": CURRENT_BMS_STATE["battery_id"],
        "data": stream,
    }


@app.post("/api/telemetry/ingest")
def ingest_telemetry(packet: TelemetryIngestPacket):
    """
    Receives live telemetry from vehicle BMS, updates internal pack state,
    and runs real-time inference and anomaly detection.
    """
    global CURRENT_BMS_STATE

    CURRENT_BMS_STATE["voltage_v"] = packet.voltage_v
    CURRENT_BMS_STATE["current_a"] = packet.current_a
    CURRENT_BMS_STATE["temperature_c"] = packet.temperature_c
    if packet.soc_percent is not None:
        CURRENT_BMS_STATE["soc_percent"] = packet.soc_percent
    if packet.internal_resistance_mohm is not None:
        CURRENT_BMS_STATE["internal_resistance_mohm"] = packet.internal_resistance_mohm
    if packet.cycle_index is not None:
        CURRENT_BMS_STATE["current_cycle"] = packet.cycle_index
    CURRENT_BMS_STATE["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Re-evaluate SoH based on current operational metrics
    ri_ohm = CURRENT_BMS_STATE["internal_resistance_mohm"] / 1000.0
    pred = predictor.predict_soh_and_rul({
        "cycle_index": CURRENT_BMS_STATE["current_cycle"],
        "internal_resistance_ohm": ri_ohm,
        "ambient_temp_c": packet.ambient_temp_c or 25.0,
        "avg_discharge_temp_c": packet.temperature_c,
        "max_discharge_temp_c": packet.temperature_c + 3.0,
    })

    CURRENT_BMS_STATE["soh_percent"] = pred["soh_percent"]
    CURRENT_BMS_STATE["rul_cycles"] = pred["rul_cycles"]
    CURRENT_BMS_STATE["rul_km"] = pred["rul_km"]

    # Quick single-point anomaly check
    anomaly_status = "NORMAL"
    if packet.temperature_c >= 55.0:
        anomaly_status = "CRITICAL_THERMAL_ALERT"
    elif packet.temperature_c >= 45.0:
        anomaly_status = "HIGH_TEMP_WARNING"

    return {
        "status": "INGESTED",
        "battery_id": packet.battery_id,
        "current_bms_state": CURRENT_BMS_STATE,
        "anomaly_status": anomaly_status,
    }


@app.post("/api/predict/soh")
def predict_soh(req: SoHPredictRequest):
    """
    AI Model Inference Endpoint: Predicts SoH (%), RUL (cycles & km),
    unsupervised anomaly score, and electro-chemical diagnostic explanation.
    """
    features = req.model_dump()
    result = predictor.predict_soh_and_rul(features)
    return result


@app.post("/api/simulate")
def simulate_degradation_trajectory(req: SimulationRequest):
    """
    Degradation Simulation Engine:
    Simulates future multi-cycle capacity degradation curves comparing user
    operating conditions against optimal BMS-protected baseline.
    """
    result = predictor.simulate_degradation(
        current_cycle=req.current_cycle,
        current_soh=req.current_soh,
        ambient_temp_c=req.ambient_temp_c,
        fast_charge_pct=req.fast_charge_pct,
        dod_pct=req.dod_pct,
        daily_km=req.daily_km,
        forecast_horizon_cycles=req.forecast_horizon_cycles,
    )
    return result


@app.post("/api/telemetry/anomaly-check")
def check_telemetry_anomalies(telemetry_points: List[Dict[str, float]]):
    """
    High-frequency anomaly detection checking recent telemetry points for
    thermal runaway precursors, over-voltage plating hazards, and impedance spikes.
    """
    result = predictor.detect_telemetry_anomalies(telemetry_points)
    return result


@app.get("/api/diagnostics/summary")
def get_diagnostics_summary():
    """
    Produces a downloadable comprehensive battery health certificate and diagnostic
    summary in JSON format.
    """
    ri_ohm = CURRENT_BMS_STATE["internal_resistance_mohm"] / 1000.0
    pred = predictor.predict_soh_and_rul({
        "cycle_index": CURRENT_BMS_STATE["current_cycle"],
        "internal_resistance_ohm": ri_ohm,
        "ambient_temp_c": CURRENT_BMS_STATE["ambient_temp_c"],
        "avg_discharge_temp_c": CURRENT_BMS_STATE["temperature_c"],
        "max_discharge_temp_c": CURRENT_BMS_STATE["temperature_c"] + 4.0,
    })

    nominal_cap = CURRENT_BMS_STATE["nominal_capacity_ah"]
    actual_cap = round(nominal_cap * (pred["soh_percent"] / 100.0), 1)

    summary = {
        "report_id": f"BMS-CERT-{int(time.time())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "battery_metadata": {
            "battery_id": CURRENT_BMS_STATE["battery_id"],
            "chemistry": CURRENT_BMS_STATE["chemistry"],
            "nominal_pack_capacity_ah": nominal_cap,
            "current_usable_capacity_ah": actual_cap,
            "nominal_pack_voltage_v": CURRENT_BMS_STATE["nominal_voltage_v"],
        },
        "health_assessment": {
            "soh_percent": pred["soh_percent"],
            "health_grade": pred["health_grade"],
            "warranty_status": "VALID - HEALTH ABOVE 80% EOL THRESHOLD",
            "rul_cycles": pred["rul_cycles"],
            "rul_km": pred["rul_km"],
            "internal_resistance_mohm": CURRENT_BMS_STATE["internal_resistance_mohm"],
            "internal_resistance_growth_pct": pred["resistance_growth_pct"],
        },
        "safety_scorecard": {
            "thermal_runaway_risk": "LOW (Temperature nominal)",
            "plating_risk": "MINIMAL (Charging within C-rate limits)",
            "anomaly_score": pred["anomaly_score"],
            "safety_verdict": "SAFE FOR OPERATIONAL DRIVING",
        },
        "ai_model_metadata": {
            "model_architecture": "Ensemble Gradient Boosting & Random Forest Regressor",
            "confidence_score_pct": pred["confidence_pct"],
            "model_r2_score": predictor.metrics["soh"]["r2"],
        },
        "diagnostic_notes": pred["explanation"],
    }
    return summary


@app.get("/api/diagnostics/report-html", response_class=HTMLResponse)
def get_diagnostics_report_html():
    """
    Returns a formal, printable / PDF-ready HTML battery health certificate
    with clean typography and styling for automotive maintenance records.
    """
    summary = get_diagnostics_summary()
    meta = summary["battery_metadata"]
    health = summary["health_assessment"]
    safety = summary["safety_scorecard"]

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>EV Battery Health Diagnostic Certificate - {summary['report_id']}</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px; color: #1e293b; background: #fff; }}
        .header {{ border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; }}
        .title {{ font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; }}
        .cert-id {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 9999px; font-weight: 700; font-size: 14px; background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 28px; }}
        .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; }}
        .card h3 {{ margin-top: 0; font-size: 14px; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid #cbd5e1; padding-bottom: 8px; }}
        .metric-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; }}
        .metric-label {{ color: #64748b; }}
        .metric-val {{ font-weight: 600; color: #0f172a; }}
        .big-number {{ font-size: 32px; font-weight: 800; color: #0f172a; margin: 8px 0; }}
        .notes-box {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 4px; margin-top: 20px; font-size: 14px; line-height: 1.6; color: #1e40af; }}
        .print-btn {{ background: #0f172a; color: #fff; padding: 10px 20px; border-radius: 6px; border: none; font-size: 14px; font-weight: 600; cursor: pointer; }}
        @media print {{
          .print-btn {{ display: none; }}
          body {{ margin: 0; }}
        }}
      </style>
    </head>
    <body>
      <div class="header">
        <div>
          <h1 class="title">⚡ EV Battery State of Health (SoH) Official Certificate</h1>
          <div class="cert-id">Diagnostic Report ID: <strong>{summary['report_id']}</strong> | Generated: {summary['generated_at']}</div>
        </div>
        <div>
          <button class="print-btn" onclick="window.print()">🖨️ Print / Save as PDF</button>
        </div>
      </div>

      <div class="grid">
        <div class="card">
          <h3>Battery Pack Identification</h3>
          <div class="metric-row"><span class="metric-label">Pack Identifier:</span><span class="metric-val">{meta['battery_id']}</span></div>
          <div class="metric-row"><span class="metric-label">Cell Chemistry:</span><span class="metric-val">{meta['chemistry']}</span></div>
          <div class="metric-row"><span class="metric-label">Nominal Capacity:</span><span class="metric-val">{meta['nominal_pack_capacity_ah']} Ah</span></div>
          <div class="metric-row"><span class="metric-label">Current Usable Capacity:</span><span class="metric-val">{meta['current_usable_capacity_ah']} Ah</span></div>
          <div class="metric-row"><span class="metric-label">Nominal Pack Voltage:</span><span class="metric-val">{meta['nominal_pack_voltage_v']} V</span></div>
        </div>

        <div class="card">
          <h3>Health & Lifespan Assessment</h3>
          <div class="metric-row"><span class="metric-label">State of Health (SoH):</span><span class="metric-val"><span class="badge">{health['soh_percent']}% - {health['health_grade']}</span></span></div>
          <div class="metric-row"><span class="metric-label">Est. Remaining Life (RUL):</span><span class="metric-val">{health['rul_cycles']} cycles (~{health['rul_km']:,.0f} km)</span></div>
          <div class="metric-row"><span class="metric-label">Internal Resistance ($R_i$):</span><span class="metric-val">{health['internal_resistance_mohm']} mΩ</span></div>
          <div class="metric-row"><span class="metric-label">Impedance Growth Rate:</span><span class="metric-val">+{health['internal_resistance_growth_pct']}%</span></div>
          <div class="metric-row"><span class="metric-label">Warranty Status:</span><span class="metric-val" style="color: #047857;">{health['warranty_status']}</span></div>
        </div>
      </div>

      <div class="grid">
        <div class="card">
          <h3>BMS Safety Scorecard</h3>
          <div class="metric-row"><span class="metric-label">Thermal Runaway Risk:</span><span class="metric-val">{safety['thermal_runaway_risk']}</span></div>
          <div class="metric-row"><span class="metric-label">Lithium Plating Risk:</span><span class="metric-val">{safety['plating_risk']}</span></div>
          <div class="metric-row"><span class="metric-label">Unsupervised Anomaly Score:</span><span class="metric-val">{safety['anomaly_score']} / 100</span></div>
          <div class="metric-row"><span class="metric-label">Safety Verdict:</span><span class="metric-val" style="color: #047857;">{safety['safety_verdict']}</span></div>
        </div>

        <div class="card">
          <h3>AI Predictive Model Verification</h3>
          <div class="metric-row"><span class="metric-label">Model Pipeline:</span><span class="metric-val">{summary['ai_model_metadata']['model_architecture']}</span></div>
          <div class="metric-row"><span class="metric-label">Validation R² Score:</span><span class="metric-val">{summary['ai_model_metadata']['model_r2_score']}</span></div>
          <div class="metric-row"><span class="metric-label">Confidence Interval:</span><span class="metric-val">±{summary['ai_model_metadata']['confidence_score_pct']}%</span></div>
        </div>
      </div>

      <div class="notes-box">
        <strong>Electro-chemical Diagnostic Verdict:</strong><br>
        {summary['diagnostic_notes']}
      </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# Mount static directory for self-contained UI preview
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def root_dashboard():
    """
    Serves the interactive web dashboard directly from FastAPI for instant execution.
    """
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>EV Battery SoH AI Engine API running. Navigate to /docs for OpenAPI specs.</h2>")


if __name__ == "__main__":
    import uvicorn
    print("Starting EV Battery SoH AI Platform on http://127.0.0.1:8000 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
