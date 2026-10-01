import React, { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";
import { Activity, Pause, Play } from "lucide-react";
import { TelemetryPoint } from "../services/api";

interface TelemetryChartsProps {
  data: TelemetryPoint[];
}

export const TelemetryCharts: React.FC<TelemetryChartsProps> = ({ data }) => {
  const [channel, setChannel] = useState<"VI" | "DELTA" | "THERMAL">("VI");
  const [frozen, setFrozen] = useState<boolean>(false);
  const [frozenBuffer, setFrozenBuffer] = useState<TelemetryPoint[]>([]);

  const toggleFreeze = () => {
    if (!frozen) {
      setFrozenBuffer([...data]);
      setFrozen(true);
    } else {
      setFrozen(false);
    }
  };

  const activeData = frozen ? frozenBuffer : data;

  return (
    <div className="bg-[#0d1117] border border-[#1c2433] rounded p-4">
      <div className="flex flex-wrap items-center justify-between pb-3 mb-3 border-b border-[#18202d] gap-2">
        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono font-bold text-zinc-200 uppercase tracking-wide flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-[#38bdf8]" /> Real-Time Telemetry Oscillogram
          </span>
          <span className="text-[10px] font-mono text-[#6b7a94] border-l border-[#1f283a] pl-3 hidden sm:inline">
            Sub-Cycle Drive Profile (Urban Dynamometer + Acceleration Pulses + Regen)
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Channel Selector */}
          <div className="flex items-center bg-[#090c12] p-0.5 rounded border border-[#1b2332] text-[11px] font-mono">
            <button
              onClick={() => setChannel("VI")}
              className={`px-2.5 py-1 rounded transition ${channel === "VI"
                ? "bg-[#162030] text-white font-medium"
                : "text-[#6b7a94] hover:text-white"
                }`}
            >
              CH1: Voltage / Current
            </button>
            <button
              onClick={() => setChannel("DELTA")}
              className={`px-2.5 py-1 rounded transition ${channel === "DELTA"
                ? "bg-[#162030] text-white font-medium"
                : "text-[#6b7a94] hover:text-white"
                }`}
            >
              CH2: Cell Dispersion (ΔV)
            </button>
            <button
              onClick={() => setChannel("THERMAL")}
              className={`px-2.5 py-1 rounded transition ${channel === "THERMAL"
                ? "bg-[#162030] text-white font-medium"
                : "text-[#6b7a94] hover:text-white"
                }`}
            >
              CH3: Thermal & Impedance
            </button>
          </div>

          {/* Freeze / Live Buffer Button */}
          <button
            onClick={toggleFreeze}
            className={`px-2.5 py-1 rounded border text-[11px] font-mono flex items-center gap-1.5 transition ${frozen
              ? "bg-[#064e3b] text-[#34d399] border-[#059669]"
              : "bg-[#141b26] hover:bg-[#1c2636] border-[#222e42] text-zinc-300"
              }`}
          >
            {frozen ? (
              <>
                <Play className="w-3 h-3" /> Resume Buffer
              </>
            ) : (
              <>
                <Pause className="w-3 h-3" /> Freeze Buffer
              </>
            )}
          </button>
        </div>
      </div>

      {/* Scope Container */}
      <div className="bg-[#090c12] border border-[#18202d] rounded p-3 h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={activeData} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#141c28" />
            <XAxis
              dataKey="timestamp_sec"
              tickFormatter={(t) => `${t}s`}
              stroke="#64748b"
              tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
            />

            {channel === "VI" && (
              <>
                <YAxis
                  yAxisId="left"
                  domain={["auto", "auto"]}
                  stroke="#38bdf8"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  unit="V"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={["auto", "auto"]}
                  stroke="#10b981"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  unit="A"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0b0f17",
                    borderColor: "#263447",
                    borderRadius: "4px",
                    fontSize: "11px",
                    fontFamily: "JetBrains Mono",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "JetBrains Mono", paddingTop: "6px" }} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="voltage_v"
                  name="Pack Voltage (V)"
                  stroke="#38bdf8"
                  strokeWidth={1.8}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="current_a"
                  name="Load Current (A)"
                  stroke="#10b981"
                  strokeWidth={1.8}
                  dot={false}
                />
              </>
            )}

            {channel === "DELTA" && (
              <>
                <YAxis
                  yAxisId="left"
                  domain={["auto", "auto"]}
                  stroke="#f59e0b"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  unit="V"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={["auto", "auto"]}
                  stroke="#ef4444"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  unit="mV"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0b0f17",
                    borderColor: "#263447",
                    borderRadius: "4px",
                    fontSize: "11px",
                    fontFamily: "JetBrains Mono",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "JetBrains Mono", paddingTop: "6px" }} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="cell_max_v"
                  name="Cell Max (V)"
                  stroke="#f59e0b"
                  strokeWidth={1.6}
                  dot={false}
                />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="cell_min_v"
                  name="Cell Min (V)"
                  stroke="#0284c7"
                  strokeWidth={1.6}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="cell_delta_mv"
                  name="Dispersion ΔV (mV)"
                  stroke="#ef4444"
                  strokeWidth={1.6}
                  strokeDasharray="3 3"
                  dot={false}
                />
              </>
            )}

            {channel === "THERMAL" && (
              <>
                <YAxis
                  yAxisId="left"
                  domain={["auto", "auto"]}
                  stroke="#f59e0b"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  unit="°C"
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  domain={["auto", "auto"]}
                  stroke="#a855f7"
                  tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }}
                  unit="mΩ"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0b0f17",
                    borderColor: "#263447",
                    borderRadius: "4px",
                    fontSize: "11px",
                    fontFamily: "JetBrains Mono",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "JetBrains Mono", paddingTop: "6px" }} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="temperature_c"
                  name="Cell Temperature (°C)"
                  stroke="#f59e0b"
                  strokeWidth={1.8}
                  dot={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="internal_resistance_mohm"
                  name="Impedance Ri (mΩ)"
                  stroke="#a855f7"
                  strokeWidth={1.8}
                  dot={false}
                />
              </>
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Scope Footer Readout */}
      <div className="mt-2.5 pt-2 border-t border-[#18202d] flex flex-wrap items-center justify-between text-[11px] font-mono text-[#6b7a94]">
        <div className="flex items-center gap-4">
          <span>Timebase: <strong className="text-zinc-300">10.0s / div</strong></span>
          <span>Sample Rate: <strong className="text-zinc-300">100 ms (A/D 16-bit)</strong></span>
          <span>Trigger: <strong className="text-zinc-300">AUTO (Load ±5A)</strong></span>
        </div>
        <div className="flex items-center gap-4">
          <span>Status: <strong className={frozen ? "text-amber-500" : "text-emerald-500"}></strong></span>
        </div>
      </div>
    </div>
  );
};
