/**
 * EV Battery AI Prognostics API Service
 * =====================================
 * Type-safe client communication layer connecting Next.js frontend
 * to FastAPI AI inference backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface BMSTelemetryState {
  vin: string;
  battery_id: string;
  pack_serial: string;
  pack_topology: string;
  cell_count: number;
  chemistry: string;
  nominal_capacity_ah: number;
  nominal_energy_kwh: number;
  nominal_voltage_v: number;
  current_cycle: number;
  soc_percent: number;
  voltage_v: number;
  current_a: number;
  pack_power_kw: number;
  temperature_c: number;
  cell_avg_v: number;
  cell_max_v: number;
  cell_min_v: number;
  cell_delta_mv: number;
  max_cell_temp_c: number;
  min_cell_temp_c: number;
  cell_temp_delta_c: number;
  coolant_inlet_temp_c: number;
  coolant_outlet_temp_c: number;
  coolant_flow_lpm: number;
  pump_rpm: number;
  isolation_resistance_kohm: number;
  hvil_status: string;
  main_contactor_pos: string;
  main_contactor_neg: string;
  precharge_contactor: string;
  pyro_fuse: string;
  bms_firmware: string;
  can_bus_load_pct: number;
  dtc_active_count: number;
  internal_resistance_mohm: number;
  ambient_temp_c: number;
  soh_percent: number;
  rul_cycles: number;
  rul_km: number;
  last_updated: string;
}

export interface TelemetryPoint {
  timestamp_sec: number;
  voltage_v: number;
  cell_avg_v?: number;
  cell_max_v?: number;
  cell_min_v?: number;
  cell_delta_mv?: number;
  pack_power_kw?: number;
  current_a: number;
  temperature_c: number;
  coolant_temp_c?: number;
  soc_percent: number;
  internal_resistance_mohm: number;
}

export interface SimulationParams {
  current_cycle: number;
  current_soh: number;
  ambient_temp_c: number;
  fast_charge_pct: number;
  dod_pct: number;
  daily_km: number;
  forecast_horizon_cycles?: number;
}

export interface SimulationTrajectoryPoint {
  cycle: number;
  user_soh: number;
  optimal_soh: number;
  eol_threshold: number;
  cumulative_km: number;
}

export interface SimulationResponse {
  forecast_trajectory: SimulationTrajectoryPoint[];
  current_cycle: number;
  projected_eol_cycle: number;
  remaining_cycles_to_eol: number;
  estimated_km_to_eol: number;
  estimated_years_to_eol: number;
  stress_multiplier: number;
  recommendations: string[];
}

export interface SoHPredictionResponse {
  soh_percent: number;
  rul_cycles: number;
  rul_km: number;
  health_grade: string;
  badge_color: string;
  is_anomaly: boolean;
  anomaly_score: number;
  internal_resistance_mohm: number;
  resistance_growth_pct: number;
  confidence_pct: number;
  explanation: string;
}

export async function fetchLatestTelemetry(): Promise<BMSTelemetryState> {
  const res = await fetch(`${API_BASE_URL}/api/telemetry/latest`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch telemetry: ${res.statusText}`);
  return res.json();
}

export async function fetchTelemetryStream(
  points: number = 60,
  ambientTemp: number = 25.0
): Promise<TelemetryPoint[]> {
  const res = await fetch(
    `${API_BASE_URL}/api/telemetry/stream?points=${points}&ambient_temp=${ambientTemp}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Failed to fetch telemetry stream: ${res.statusText}`);
  const json = await res.json();
  return json.data;
}

export async function simulateDegradation(params: SimulationParams): Promise<SimulationResponse> {
  const res = await fetch(`${API_BASE_URL}/api/simulate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error(`Simulation failed: ${res.statusText}`);
  return res.json();
}

export async function predictSoH(features: Record<string, any>): Promise<SoHPredictionResponse> {
  const res = await fetch(`${API_BASE_URL}/api/predict/soh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(features),
  });
  if (!res.ok) throw new Error(`Prediction failed: ${res.statusText}`);
  return res.json();
}

export async function fetchDiagnosticsSummary(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/diagnostics/summary`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch diagnostics: ${res.statusText}`);
  return res.json();
}

export function getDiagnosticReportHtmlUrl(): string {
  return `${API_BASE_URL}/api/diagnostics/report-html`;
}
