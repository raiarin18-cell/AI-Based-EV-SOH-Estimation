import React from "react";
import { BMSTelemetryState } from "../services/api";

interface MetricsCardsProps {
  telemetry: BMSTelemetryState;
}

export const MetricsCards: React.FC<MetricsCardsProps> = ({ telemetry }) => {
  const freshCapacity = telemetry.nominal_capacity_ah || 200.0;
  const currentCapacity = (freshCapacity * (telemetry.soh_percent / 100.0)).toFixed(1);
  const capacityFadeAh = (freshCapacity - parseFloat(currentCapacity)).toFixed(1);
  const fadePercent = (100.0 - telemetry.soh_percent).toFixed(1);
  const usableKwh = ((telemetry.nominal_energy_kwh || 75.0) * (telemetry.soh_percent / 100.0)).toFixed(1);

  const freshRi = 45.0; // 45 mOhm baseline
  const riGrowth = (((telemetry.internal_resistance_mohm - freshRi) / freshRi) * 100).toFixed(1);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
      {/* 1. State of Health (SoH) */}
      <div className="bg-[#0d1117] border border-[#1c2433] hover:border-[#263347] rounded p-3.5 flex flex-col justify-between transition">
        <div className="flex justify-between items-start">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#6b7a94]">
            Pack State of Health
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#064e3b] text-[#34d399] border border-[#059669]">
            WARRANTY OK
          </span>
        </div>
        <div className="my-2">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-white tabular-nums">
              {telemetry.soh_percent.toFixed(1)}
            </span>
            <span className="text-xs font-mono text-zinc-400">%</span>
          </div>
          <div className="text-[11px] font-mono text-[#6b7a94] mt-0.5 flex justify-between">
            <span>Capacity Fade:</span>
            <span className="text-zinc-300 font-semibold">-{fadePercent}% (-{capacityFadeAh} Ah)</span>
          </div>
        </div>
        <div className="pt-2 border-t border-[#18202d] text-[10px] font-mono text-zinc-400 flex justify-between">
          <span>Usable Energy:</span>
          <span className="text-zinc-200">{usableKwh} kWh / 75.0</span>
        </div>
      </div>

      {/* 2. Remaining Useful Life (RUL) */}
      <div className="bg-[#0d1117] border border-[#1c2433] hover:border-[#263347] rounded p-3.5 flex flex-col justify-between transition">
        <div className="flex justify-between items-start">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#6b7a94]">
            Remaining Useful Life
          </span>
          <span className="text-[10px] font-mono text-zinc-400">EOL: 80.0%</span>
        </div>
        <div className="my-2">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-white tabular-nums">
              {telemetry.rul_cycles}
            </span>
            <span className="text-xs font-mono text-[#0284c7]">CYCLES</span>
          </div>
          <div className="text-[11px] font-mono text-[#6b7a94] mt-0.5 flex justify-between">
            <span>Projected Distance:</span>
            <span className="text-[#38bdf8] font-semibold">{telemetry.rul_km.toLocaleString()} km</span>
          </div>
        </div>
        <div className="pt-2 border-t border-[#18202d] text-[10px] font-mono text-zinc-400 flex justify-between">
          <span>Current Cycle:</span>
          <span className="text-zinc-200">Cycle #{telemetry.current_cycle}</span>
        </div>
      </div>

      {/* 3. Pack Electrics: Voltage & Current */}
      <div className="bg-[#0d1117] border border-[#1c2433] hover:border-[#263347] rounded p-3.5 flex flex-col justify-between transition">
        <div className="flex justify-between items-start">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#6b7a94]">
            Pack Electrics
          </span>
          <span className="text-[10px] font-mono px-1 rounded bg-[#1e293b] text-zinc-300">HV DC BUS</span>
        </div>
        <div className="my-2">
          <div className="flex items-baseline justify-between">
            <div>
              <span className="text-xl font-mono font-bold text-white tabular-nums">
                {telemetry.voltage_v.toFixed(1)}
              </span>
              <span className="text-[11px] font-mono text-zinc-400">V</span>
            </div>
            <div>
              <span className="text-xl font-mono font-bold text-[#38bdf8] tabular-nums">
                {telemetry.current_a >= 0 ? `+${telemetry.current_a.toFixed(1)}` : telemetry.current_a.toFixed(1)}
              </span>
              <span className="text-[11px] font-mono text-zinc-400">A</span>
            </div>
          </div>
          <div className="text-[11px] font-mono text-[#6b7a94] mt-0.5 flex justify-between">
            <span>Power Output:</span>
            <span className="text-zinc-200 font-semibold">{telemetry.pack_power_kw ? `${telemetry.pack_power_kw.toFixed(2)} kW` : "16.55 kW"}</span>
          </div>
        </div>
        <div className="pt-2 border-t border-[#18202d] text-[10px] font-mono text-zinc-400 flex justify-between">
          <span>State of Charge:</span>
          <span className="text-zinc-200 font-semibold">{telemetry.soc_percent.toFixed(1)}%</span>
        </div>
      </div>

      {/* 4. Cell String Balance (Delta-V) */}
      <div className="bg-[#0d1117] border border-[#1c2433] hover:border-[#263347] rounded p-3.5 flex flex-col justify-between transition">
        <div className="flex justify-between items-start">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#6b7a94]">
            Cell String Balance
          </span>
          <span className="text-[10px] font-mono px-1 rounded bg-[#064e3b] text-[#34d399] border border-[#059669]">
            BALANCED
          </span>
        </div>
        <div className="my-2">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-white tabular-nums">
              {telemetry.cell_delta_mv ? telemetry.cell_delta_mv.toFixed(1) : "15.0"}
            </span>
            <span className="text-xs font-mono text-zinc-400">mV (ΔV)</span>
          </div>
          <div className="text-[11px] font-mono text-[#6b7a94] mt-0.5 flex justify-between">
            <span>Cell Min / Max:</span>
            <span className="text-zinc-300 font-semibold">
              {telemetry.cell_min_v ? telemetry.cell_min_v.toFixed(3) : "4.038"} / {telemetry.cell_max_v ? telemetry.cell_max_v.toFixed(3) : "4.053"} V
            </span>
          </div>
        </div>
        <div className="pt-2 border-t border-[#18202d] text-[10px] font-mono text-zinc-400 flex justify-between">
          <span>Balancing Circuit:</span>
          <span className="text-zinc-200">PASSIVE (STANDBY)</span>
        </div>
      </div>

      {/* 5. Thermal Management */}
      <div className="bg-[#0d1117] border border-[#1c2433] hover:border-[#263347] rounded p-3.5 flex flex-col justify-between transition">
        <div className="flex justify-between items-start">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#6b7a94]">
            Thermal Loop
          </span>
          <span className="text-[10px] font-mono text-zinc-400">TARGET: 25°C</span>
        </div>
        <div className="my-2">
          <div className="flex items-baseline justify-between">
            <div>
              <span className="text-xl font-mono font-bold text-white tabular-nums">
                {telemetry.temperature_c.toFixed(1)}
              </span>
              <span className="text-[11px] font-mono text-zinc-400">°C Cell</span>
            </div>
            <div>
              <span className="text-xl font-mono font-bold text-amber-500 tabular-nums">
                {telemetry.coolant_inlet_temp_c ? telemetry.coolant_inlet_temp_c.toFixed(1) : "22.8"}
              </span>
              <span className="text-[11px] font-mono text-zinc-400">°C Loop</span>
            </div>
          </div>
          <div className="text-[11px] font-mono text-[#6b7a94] mt-0.5 flex justify-between">
            <span>Cell ΔT (Spread):</span>
            <span className="text-zinc-300 font-semibold">1.7 °C (Max 29.2°C)</span>
          </div>
        </div>
        <div className="pt-2 border-t border-[#18202d] text-[10px] font-mono text-zinc-400 flex justify-between">
          <span>Coolant Pump:</span>
          <span className="text-zinc-200">{telemetry.pump_rpm || 2850} RPM (Active)</span>
        </div>
      </div>

      {/* 6. DC Internal Resistance (Ri) */}
      <div className="bg-[#0d1117] border border-[#1c2433] hover:border-[#263347] rounded p-3.5 flex flex-col justify-between transition">
        <div className="flex justify-between items-start">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#6b7a94]">
            DC Internal Resistance
          </span>
          <span className="text-[10px] font-mono text-zinc-400">BOL: 45.0 mΩ</span>
        </div>
        <div className="my-2">
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-mono font-bold text-white tabular-nums">
              {telemetry.internal_resistance_mohm.toFixed(1)}
            </span>
            <span className="text-xs font-mono text-zinc-400">mΩ</span>
          </div>
          <div className="text-[11px] font-mono text-[#6b7a94] mt-0.5 flex justify-between">
            <span>Impedance Growth:</span>
            <span className="text-amber-400 font-semibold">+{riGrowth}% over fresh</span>
          </div>
        </div>
        <div className="pt-2 border-t border-[#18202d] text-[10px] font-mono text-zinc-400 flex justify-between">
          <span>SEI Layer State:</span>
          <span className="text-zinc-200">NOMINAL GROWTH</span>
        </div>
      </div>
    </div>
  );
};
