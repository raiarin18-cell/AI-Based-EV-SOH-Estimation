"""
Battery State of Health (SoH) & RUL Model Training Pipeline
============================================================
Trains machine learning models (Gradient Boosting & Random Forest) to estimate:
1. Battery State of Health (SoH %) from operational cycle telemetry.
2. Remaining Useful Life (RUL in cycles) until 80% EOL threshold.
3. Anomaly detection model for thermal runaway & rapid capacity cliff risks.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, IsolationForest
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import StandardScaler

# Ensure pathing works whether run from root or backend/model
import sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from data_gen import generate_fleet_training_dataset


FEATURE_COLUMNS = [
    "cycle_index",
    "ambient_temp_c",
    "avg_discharge_temp_c",
    "max_discharge_temp_c",
    "voltage_drop_v",
    "internal_resistance_ohm",
    "c_rate",
    "depth_of_discharge",
    "charge_duration_min",
    "discharge_duration_min",
    "energy_efficiency_pct",
]


def train_soh_and_rul_models(
    dataset_csv_path: str = "battery_fleet_dataset.csv",
    save_dir: str = CURRENT_DIR,
) -> Dict[str, Any]:
    """
    Loads or synthesizes fleet battery dataset, trains regression models for SoH and RUL,
    evaluates validation metrics, and serializes artifacts.
    """
    if os.path.exists(dataset_csv_path):
        print(f"Loading existing battery dataset from: {dataset_csv_path}")
        df = pd.read_csv(dataset_csv_path)
    else:
        print("Dataset not found. Synthesizing new fleet dataset...")
        df = generate_fleet_training_dataset(num_batteries=30)
        df.to_csv(dataset_csv_path, index=False)

    print(f"Training dataset size: {len(df)} samples across {df['battery_id'].nunique()} batteries.")

    X = df[FEATURE_COLUMNS]
    y_soh = df["soh_percent"]
    y_rul = df["rul_cycles"]

    # 80/20 train/test split representing telemetry cycle stream sampling across the fleet
    X_train, X_test, y_soh_train, y_soh_test, y_rul_train, y_rul_test = train_test_split(
        X, y_soh, y_rul, test_size=0.20, random_state=42
    )

    print(f"Train samples: {len(X_train)} | Test samples: {len(X_test)}")

    # Feature Scaling
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 1. SoH Model: Gradient Boosting Regressor
    print("Training State of Health (SoH) Gradient Boosting model...")
    soh_model = GradientBoostingRegressor(
        n_estimators=180,
        learning_rate=0.08,
        max_depth=5,
        subsample=0.85,
        random_state=42,
    )
    soh_model.fit(X_train_scaled, y_soh_train)

    # Evaluate SoH Model
    soh_preds = soh_model.predict(X_test_scaled)
    soh_r2 = r2_score(y_soh_test, soh_preds)
    soh_rmse = np.sqrt(mean_squared_error(y_soh_test, soh_preds))
    soh_mae = mean_absolute_error(y_soh_test, soh_preds)

    print(f"--- SoH Evaluation ---")
    print(f"R² Score: {soh_r2:.4f}")
    print(f"RMSE:     {soh_rmse:.3f}%")
    print(f"MAE:      {soh_mae:.3f}%")

    # 2. RUL Model: Random Forest Regressor
    print("Training Remaining Useful Life (RUL) Random Forest model...")
    rul_model = RandomForestRegressor(
        n_estimators=120,
        max_depth=12,
        min_samples_split=4,
        n_jobs=-1,
        random_state=42,
    )
    rul_model.fit(X_train_scaled, y_rul_train)

    # Evaluate RUL Model
    rul_preds = rul_model.predict(X_test_scaled)
    rul_r2 = r2_score(y_rul_test, rul_preds)
    rul_rmse = np.sqrt(mean_squared_error(y_rul_test, rul_preds))
    rul_mae = mean_absolute_error(y_rul_test, rul_preds)

    print(f"--- RUL Evaluation ---")
    print(f"R² Score: {rul_r2:.4f}")
    print(f"RMSE:     {rul_rmse:.2f} cycles")
    print(f"MAE:      {rul_mae:.2f} cycles")

    # 3. Anomaly Detection: Isolation Forest
    print("Fitting Isolation Forest for Unsupervised Anomaly Detection...")
    iso_forest = IsolationForest(
        n_estimators=100,
        contamination=0.03,
        random_state=42,
    )
    # Fit on normal operational data
    normal_mask = (df.loc[X_train.index, "is_anomaly"] == 0).to_numpy()
    normal_data = X_train_scaled[normal_mask]
    iso_forest.fit(normal_data)

    # Feature Importance extraction
    importances = dict(zip(FEATURE_COLUMNS, soh_model.feature_importances_))
    sorted_importances = dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    artifacts = {
        "soh_model": soh_model,
        "rul_model": rul_model,
        "isolation_forest": iso_forest,
        "scaler": scaler,
        "feature_columns": FEATURE_COLUMNS,
        "metrics": {
            "soh": {"r2": round(soh_r2, 4), "rmse": round(soh_rmse, 4), "mae": round(soh_mae, 4)},
            "rul": {"r2": round(rul_r2, 4), "rmse": round(rul_rmse, 2), "mae": round(rul_mae, 2)},
        },
        "feature_importance": sorted_importances,
    }

    model_filepath = os.path.join(save_dir, "soh_model_artifacts.joblib")
    joblib.dump(artifacts, model_filepath)
    print(f"Model artifacts successfully serialized to: {model_filepath}")

    # Also save metrics JSON for API query
    metrics_path = os.path.join(save_dir, "model_metrics.json")
    with open(metrics_path, "w") as f:
        json.dump({
            "metrics": artifacts["metrics"],
            "feature_importance": sorted_importances,
            "feature_columns": FEATURE_COLUMNS,
        }, f, indent=2)

    return artifacts


if __name__ == "__main__":
    train_soh_and_rul_models()
