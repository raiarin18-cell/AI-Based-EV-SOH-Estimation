import React, { useState } from "react";
import { ShieldAlert, X } from "lucide-react";
import { BMSTelemetryState } from "../services/api";

interface AnomalyAlertBannerProps {
  telemetry: BMSTelemetryState;
}

export const AnomalyAlertBanner: React.FC<AnomalyAlertBannerProps> = ({ telemetry }) => {
  const [dismissed, setDismissed] = useState<boolean>(false);

  let hasFault = false;
  let faultSeverity = "NORMAL";
  let faultTitle = "";
  let faultDesc = "";

  if (telemetry.temperature_c >= 55.0) {
    hasFault = true;
    faultSeverity = "CRITICAL";
    faultTitle = "CRITICAL THERMAL RUNAWAY HAZARD";
    faultDesc = `Cell core temperature reached ${telemetry.temperature_c.toFixed(1)}°C. BMS automatic coolant valve bypass engaged.`;
  } else if (telemetry.temperature_c >= 45.0) {
    hasFault = true;
    faultSeverity = "WARNING";
    faultTitle = "HIGH TEMPERATURE STRESS WARNING";
    faultDesc = `Pack temperature ${telemetry.temperature_c.toFixed(1)}°C exceeds optimal threshold. Derating peak discharge current.`;
  } else if (telemetry.internal_resistance_mohm >= 100.0) {
    hasFault = true;
    faultSeverity = "WARNING";
    faultTitle = "IMPEDANCE SPIKE WARNING";
    faultDesc = `DC internal resistance reached ${telemetry.internal_resistance_mohm.toFixed(1)} mΩ. Physical cell interconnect check advised.`;
  }

  if (!hasFault || dismissed) return null;

  return (
    <div
      className={`px-4 py-2 border-b flex items-center justify-between font-mono text-xs transition ${
        faultSeverity === "CRITICAL"
          ? "border-rose-600/40 bg-rose-950/80 text-rose-200"
          : "border-amber-600/40 bg-amber-950/80 text-amber-200"
      }`}
    >
      <div className="flex items-center gap-2.5">
        <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0" />
        <span className="font-bold">{faultTitle}:</span>
        <span>{faultDesc}</span>
      </div>
      <button
        onClick={() => setDismissed(true)}
        className="px-2 py-0.5 rounded bg-black/40 hover:bg-black/60 text-[10px] uppercase font-bold text-zinc-300 transition"
      >
        Acknowledge
      </button>
    </div>
  );
};
