import React, { useState, useEffect } from "react";
import Head from "next/head";
import { Zap, Wifi, WifiOff } from "lucide-react";
import {
  fetchLatestTelemetry,
  fetchTelemetryStream,
  BMSTelemetryState,
  TelemetryPoint,
} from "../services/api";
import { MetricsCards } from "../components/MetricsCards";
import { TelemetryCharts } from "../components/TelemetryCharts";
import { DegradationSimulation } from "../components/DegradationSimulation";
import { AnomalyAlertBanner } from "../components/AnomalyAlertBanner";
import { ExportDiagnostics } from "../components/ExportDiagnostics";

export default function Dashboard() {
  const [telemetry, setTelemetry] = useState<BMSTelemetryState | null>(null);
  const [telemetryStream, setTelemetryStream] = useState<TelemetryPoint[]>([]);
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(true);

  // Poll real-time telemetry from FastAPI backend
  useEffect(() => {
    let isMounted = true;

    const loadData = async () => {
      try {
        const latest = await fetchLatestTelemetry();
        if (isMounted) {
          setTelemetry(latest);
          setIsOnline(true);
        }

        const stream = await fetchTelemetryStream(50, latest.ambient_temp_c);
        if (isMounted) {
          setTelemetryStream(stream);
          setLoading(false);
        }
      } catch (err) {
        console.error("Telemetry fetch error:", err);
        if (isMounted) {
          setIsOnline(false);
          // If offline and first load, provide realistic demo fallback
          if (!telemetry) {
            setTelemetry({
              battery_id: "EV-PACK-NX75-402",
              chemistry: "Lithium Nickel Manganese Cobalt",
              nominal_capacity_ah: 200.0,
              nominal_voltage_v: 375.0,
              current_cycle: 142,
              soc_percent: 84.5,
              voltage_v: 388.4,
              current_a: 42.6,
              temperature_c: 28.3,
              internal_resistance_mohm: 48.2,
              ambient_temp_c: 24.5,
              soh_percent: 96.8,
              rul_cycles: 570,
              rul_km: 205200.0,
              last_updated: new Date().toISOString(),
            } as any);
            setLoading(false);
          }
        }
      }
    };

    loadData();
    const interval = setInterval(loadData, 3500);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <>
      <Head>
        <title>EV Battery State of Health (SoH) AI Prognostics Suite</title>
        <meta
          name="description"
          content="AI-based real-time battery degradation estimation and remaining useful life forecasting for electric vehicles."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <div className="min-h-screen bg-[#090d16] text-gray-100 flex flex-col">
        {/* Top Navigation Bar */}
        <header className="border-b border-gray-800 bg-gray-900/90 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex flex-wrap items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="bg-gradient-to-tr from-emerald-500 to-cyan-500 p-2.5 rounded-xl shadow-lg shadow-emerald-500/20">
              <Zap className="w-6 h-6 text-slate-950 font-bold" />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                EV Battery SoH Prognostics AI
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  v2.0 Active
                </span>
              </h1>
              <p className="text-xs text-gray-400">
                Pack ID:{" "}
                <span className="font-mono text-gray-300">
                  {telemetry?.battery_id || "EV-PACK-NX75-402"}
                </span>{" "}
                | Architecture:{" "}
                <span className="text-cyan-400">Ensemble GBR + Random Forest (R² 0.993)</span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3 mt-3 sm:mt-0">
            {/* Live Connection Pill */}
            <div
              className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg border font-medium ${isOnline
                  ? "bg-emerald-950/60 border-emerald-800/80 text-emerald-300"
                  : "bg-amber-950/60 border-amber-800/80 text-amber-300"
                }`}
            >
              {isOnline ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                  <Wifi className="w-3.5 h-3.5" /> BMS Stream Active
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5" /> Standalone Demo Mode
                </>
              )}
            </div>

            {/* Diagnostic Report Export */}
            <ExportDiagnostics />
          </div>
        </header>

        {/* Anomaly Notification Banner */}
        {telemetry && (
          <div className="max-w-7xl mx-auto w-full px-6 pt-4">
            <AnomalyAlertBanner telemetry={telemetry} />
          </div>
        )}

        {/* Main Dashboard Grid */}
        <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
          {telemetry && <MetricsCards telemetry={telemetry} />}

          <TelemetryCharts data={telemetryStream} />

          <DegradationSimulation
            currentCycle={telemetry?.current_cycle || 142}
            currentSoH={telemetry?.soh_percent || 96.8}
          />
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-800/80 bg-gray-950/40 px-6 py-4 text-center text-xs text-gray-500">
          EV Battery Health AI Platform • NASA Ames & Oxford Battery Prognostics Formulation • Principal Embedded AI & Full-Stack Implementation
        </footer>
      </div>
    </>
  );
}
