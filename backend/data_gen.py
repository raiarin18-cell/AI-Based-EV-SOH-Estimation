"""
Battery Telemetry & Degradation Synthesizer
============================================
Simulates realistic lithium-ion battery cycling telemetry and capacity degradation
trajectories matching NASA Ames Battery Aging Dataset (B0005, B0006, B0018)
and Oxford Battery Degradation Dataset characteristics.

Key Electrochemical Phenomena Modeled:
1. SEI Layer Growth (Square root of cycle time dependence)
2. Arrhenius Thermal Acceleration (High temp oxidation & sub-zero lithium plating)
3. C-Rate Fast-Charge Stress & Mechanical Particle Cracking
4. Depth of Discharge (DOD) Non-Linear Fatigue (Wöhler power-law)
5. Knee-Point Transition (Accelerated aging after active material loss)
6. Dynamic Joule Heating & Internal Resistance ($R_i$) Growth
7. Post-rest Capacity Regeneration (Relaxation-induced capacity rebound)
"""

import math
import random
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


class BatteryDataSynthesizer:
    """
    Synthesizes cycle-level features and high-frequency in-cycle telemetry
    for electric vehicle lithium-ion battery cells/packs.
    """

    def __init__(
        self,
        nominal_capacity_ah: float = 2.50,
        nominal_voltage: float = 3.70,
        cutoff_voltage_lower: float = 2.80,
        cutoff_voltage_upper: float = 4.20,
        initial_internal_resistance: float = 0.045,  # 45 mOhm
        eol_threshold_soh: float = 80.0,            # 80% SoH is automotive EOL
        random_seed: Optional[int] = 42,
    ):
        self.c_nominal = nominal_capacity_ah
        self.v_nom = nominal_voltage
        self.v_min = cutoff_voltage_lower
        self.v_max = cutoff_voltage_upper
        self.r_initial = initial_internal_resistance
        self.eol_soh = eol_threshold_soh
        
        if random_seed is not None:
            np.random.seed(random_seed)
            random.seed(random_seed)

    def calculate_arrhenius_factor(self, temp_celsius: float) -> float:
        """
        Computes Arrhenius aging acceleration factor based on temperature.
        Optimal window: 20°C - 25°C.
        High Temp (>35°C): Accelerates SEI formation and electrolyte decomposition.
        Low Temp (<10°C): Plating risk during charging dramatically accelerates aging.
        """
        t_kelvin = temp_celsius + 273.15
        t_ref_kelvin = 298.15  # 25°C reference
        gas_constant = 8.314   # J / (mol * K)
        activation_energy = 31500.0  # J / mol for SEI growth

        # Standard Arrhenius equation for high temp degradation
        arrhenius_base = math.exp((activation_energy / gas_constant) * (1 / t_ref_kelvin - 1 / t_kelvin))
        
        # Cold charging penalty (Lithium plating below 15°C)
        cold_penalty = 1.0
        if temp_celsius < 15.0:
            cold_penalty += 0.08 * (15.0 - temp_celsius) ** 1.4

        return arrhenius_base * cold_penalty

    def calculate_c_rate_factor(self, c_rate: float) -> float:
        """
        High charging current (e.g. 2C - 3C DC Fast Charging) generates local
        overpotentials, mechanical stress in cathode particles, and thermal gradients.
        """
        if c_rate <= 1.0:
            return 1.0
        return 1.0 + 0.35 * ((c_rate - 1.0) ** 1.35)

    def calculate_dod_factor(self, dod: float) -> float:
        """
        Depth of Discharge (DOD) mechanical fatigue factor (Wöhler-type model).
        Cycling from 100% to 0% (DOD=1.0) causes much faster degradation than
        shallow cycling (e.g., DOD=0.4 - 0.6).
        """
        clamped_dod = max(0.1, min(1.0, dod))
        return (clamped_dod / 0.8) ** 1.45

    def generate_battery_lifespan_cycles(
        self,
        num_cycles: int = 800,
        ambient_temp_mean: float = 25.0,
        c_rate_mean: float = 1.0,
        dod_mean: float = 0.8,
        knee_point_cycle: int = 550,
        add_anomalies: bool = False,
    ) -> pd.DataFrame:
        """
        Generates cycle-by-cycle summary telemetry for a single battery cell across its lifespan.
        Includes cycle capacity fade, resistance rise, temperatures, and SoH.
        """
        records = []
        current_capacity = self.c_nominal
        current_resistance = self.r_initial

        for cycle in range(1, num_cycles + 1):
            # Dynamic conditions with realistic daily variance
            cycle_temp = ambient_temp_mean + np.random.normal(0, 1.8)
            cycle_c_rate = max(0.5, c_rate_mean + np.random.normal(0, 0.12))
            cycle_dod = max(0.2, min(1.0, dod_mean + np.random.normal(0, 0.04)))

            # Electrochemical stress multipliers
            temp_factor = self.calculate_arrhenius_factor(cycle_temp)
            c_factor = self.calculate_c_rate_factor(cycle_c_rate)
            dod_factor = self.calculate_dod_factor(cycle_dod)

            # 1. Base SEI growth degradation rate (proportional to 1 / (2 * sqrt(cycle)))
            sei_rate = 0.00038 / (math.sqrt(cycle) + 3.0)
            
            # 2. Linear cyclic fatigue degradation
            linear_rate = 0.00018

            # 3. Knee-point non-linear cliff (Loss of active material / pore clogging)
            knee_rate = 0.0
            if cycle > knee_point_cycle:
                cycles_past_knee = cycle - knee_point_cycle
                knee_rate = 0.00045 * (1.0 + 0.012 * cycles_past_knee)

            total_fade = (sei_rate + linear_rate + knee_rate) * temp_factor * c_factor * dod_factor
            
            # NASA dataset feature: Capacity regeneration rebound after prolonged resting
            regeneration = 0.0
            if cycle % 45 == 0 and random.random() < 0.65:
                regeneration = np.random.uniform(0.004, 0.012)

            current_capacity = max(0.9, current_capacity - total_fade + regeneration)
            
            # Internal resistance increases inversely with capacity fade
            resistance_growth = (total_fade * 0.038) + np.random.normal(0.00003, 0.00001)
            current_resistance = min(0.35, current_resistance + resistance_growth)

            # Derived SoH (%)
            soh_percent = (current_capacity / self.c_nominal) * 100.0

            # Dynamic discharge voltage drop based on load and internal resistance
            peak_current = cycle_c_rate * self.c_nominal
            v_ir_drop = peak_current * current_resistance
            v_drop = 0.45 + v_ir_drop + np.random.normal(0, 0.015)

            # Cycle durations (CC-CV charging and discharge)
            charge_duration_min = max(25.0, (60.0 / cycle_c_rate) * (current_capacity / self.c_nominal) * 1.1 + np.random.normal(0, 1.5))
            discharge_duration_min = max(20.0, (60.0 / cycle_c_rate) * (current_capacity / self.c_nominal) * cycle_dod + np.random.normal(0, 1.2))

            # Operational temperatures
            avg_discharge_temp = cycle_temp + (peak_current ** 2) * current_resistance * 18.0 + np.random.normal(0, 0.6)
            max_discharge_temp = avg_discharge_temp + np.random.uniform(2.5, 6.0)

            # Coulombic efficiency (typically 98.8% to 99.8%)
            energy_efficiency = max(88.0, min(99.6, 99.4 - (0.012 * (100.0 - soh_percent)) + np.random.normal(0, 0.2)))

            # Anomaly injection for testing BMS safeguards
            is_anomaly = 0
            anomaly_type = "NORMAL"
            if add_anomalies and cycle in [180, 420]:
                if cycle == 180:
                    # Simulated internal micro-short: sudden resistance jump & thermal spike
                    avg_discharge_temp += 22.0
                    max_discharge_temp += 34.0
                    current_resistance *= 1.45
                    is_anomaly = 1
                    anomaly_type = "THERMAL_RUNAWAY_RISK"
                elif cycle == 420:
                    # Simulated rapid capacity drop / cell degradation cliff
                    current_capacity -= 0.15
                    soh_percent = (current_capacity / self.c_nominal) * 100.0
                    is_anomaly = 1
                    anomaly_type = "RAPID_CAPACITY_DROP"

            records.append({
                "cycle_index": cycle,
                "capacity_ah": round(float(current_capacity), 4),
                "soh_percent": round(float(soh_percent), 2),
                "internal_resistance_ohm": round(float(current_resistance), 5),
                "ambient_temp_c": round(float(cycle_temp), 2),
                "avg_discharge_temp_c": round(float(avg_discharge_temp), 2),
                "max_discharge_temp_c": round(float(max_discharge_temp), 2),
                "voltage_drop_v": round(float(v_drop), 4),
                "c_rate": round(float(cycle_c_rate), 2),
                "depth_of_discharge": round(float(cycle_dod), 2),
                "charge_duration_min": round(float(charge_duration_min), 1),
                "discharge_duration_min": round(float(discharge_duration_min), 1),
                "energy_efficiency_pct": round(float(energy_efficiency), 2),
                "is_anomaly": is_anomaly,
                "anomaly_type": anomaly_type,
            })

        df = pd.DataFrame(records)
        
        # Calculate Remaining Useful Life (RUL) in remaining cycles until SoH <= 80%
        eol_matches = df[df["soh_percent"] <= self.eol_soh]
        eol_cycle = eol_matches["cycle_index"].iloc[0] if not eol_matches.empty else num_cycles + 150
        df["rul_cycles"] = df["cycle_index"].apply(lambda c: max(0, int(eol_cycle - c)))
        # Convert RUL to estimated kilometers (assuming average EV range 450 km per 100% full equivalent cycle)
        df["rul_km"] = df["rul_cycles"].apply(lambda r: round(r * 450.0 * dod_mean, 1))

        return df

    def generate_detailed_telemetry_stream(
        self,
        cycle_number: int = 120,
        soh_percent: float = 93.5,
        ambient_temp: float = 24.0,
        c_rate: float = 1.0,
        time_steps: int = 120,
    ) -> List[Dict[str, float]]:
        """
        Generates high-frequency sub-cycle telemetry stream (Voltage, Current, Temp, SoC, Ri)
        simulating an active driving/discharge session for live dashboard streaming.
        """
        stream = []
        actual_capacity = self.c_nominal * (soh_percent / 100.0)
        ri = self.r_initial * (1.0 + (100.0 - soh_percent) * 0.022)
        
        current_soc = 98.0
        cell_temp = ambient_temp + 1.5

        for t in range(time_steps):
            # Profile: Dynamic vehicle driving cycle with acceleration pulses and regenerative braking
            if t < 15:
                # Idle / startup
                load_current = 0.5 + np.random.normal(0, 0.1)
            elif 15 <= t < 40:
                # Cruising at 60 km/h
                load_current = (1.2 * c_rate * actual_capacity) + np.random.normal(0, 0.3)
            elif 40 <= t < 55:
                # Hard acceleration pulse
                load_current = (2.8 * c_rate * actual_capacity) + np.random.normal(0, 0.4)
            elif 55 <= t < 70:
                # Regenerative braking (negative current charging battery)
                load_current = -1.2 * c_rate * actual_capacity + np.random.normal(0, 0.2)
            elif 70 <= t < 105:
                # Highway cruising with random traffic variations
                load_current = (1.6 * c_rate * actual_capacity) + np.random.normal(0, 0.4)
            else:
                # Deceleration and parking idle
                load_current = 0.2 + np.random.normal(0, 0.05)

            # SoC depletion calculation (integrating current over time)
            delta_soc = (load_current * (1.0 / 3600.0) / actual_capacity) * 100.0
            current_soc = max(5.0, min(100.0, current_soc - delta_soc))

            # Open Circuit Voltage (OCV) curve estimation for NMC chemistry
            soc_fraction = current_soc / 100.0
            ocv = (
                3.40
                + 0.55 * soc_fraction
                + 0.15 * math.log(max(0.005, soc_fraction))
                - 0.08 * math.log(max(0.005, 1.01 - soc_fraction))
            )
            ocv = max(3.0, min(4.20, ocv))

            # Terminal voltage under load: V_terminal = OCV - I * R_i
            v_terminal = ocv - (load_current * ri) + np.random.normal(0, 0.005)
            v_terminal = max(self.v_min, min(self.v_max + 0.05, v_terminal))

            # Thermal model: Joule heating Q = I^2 * R, and heat dissipation to ambient
            joule_heat = (load_current ** 2) * ri * 0.12
            heat_loss = 0.04 * (cell_temp - ambient_temp)
            cell_temp += joule_heat - heat_loss + np.random.normal(0, 0.04)

            # Automotive pack scaling (96S configuration)
            pack_v = round(v_terminal * 96.0, 1)
            cell_max = round(v_terminal + 0.008 + np.random.uniform(-0.002, 0.003), 4)
            cell_min = round(v_terminal - 0.007 + np.random.uniform(-0.003, 0.002), 4)
            cell_delta_mv = round((cell_max - cell_min) * 1000.0, 1)
            pack_kw = round((pack_v * load_current) / 1000.0, 2)
            coolant_temp = round(ambient_temp + 1.5 + (cell_temp - ambient_temp) * 0.35, 1)

            stream.append({
                "timestamp_sec": t * 10,
                "voltage_v": pack_v,
                "cell_avg_v": round(float(v_terminal), 3),
                "cell_max_v": cell_max,
                "cell_min_v": cell_min,
                "cell_delta_mv": cell_delta_mv,
                "pack_power_kw": pack_kw,
                "current_a": round(float(load_current), 2),
                "temperature_c": round(float(cell_temp), 2),
                "coolant_temp_c": coolant_temp,
                "soc_percent": round(float(current_soc), 2),
                "internal_resistance_mohm": round(float(ri * 1000.0), 2),
            })

        return stream


def generate_fleet_training_dataset(num_batteries: int = 40) -> pd.DataFrame:
    """
    Generates training dataset encompassing diverse ambient temperatures,
    charging habits, and driver profiles mimicking real EV fleet telemetry.
    """
    all_dfs = []
    synthesizer = BatteryDataSynthesizer()

    # Temperature regimes: Cold (5-15°C), Moderate (20-28°C), Hot (35-45°C)
    # Driver profiles: Commuter (0.7C, 60% DOD), Taxi/Ride-share (1.8C fast charging, 90% DOD)
    for b_idx in range(num_batteries):
        amb_temp = random.choice([8.0, 15.0, 22.0, 25.0, 32.0, 40.0])
        c_rate = random.choice([0.5, 0.8, 1.2, 1.5, 2.0, 2.5])
        dod = random.choice([0.5, 0.65, 0.80, 0.90, 0.95])
        knee_cycle = int(np.random.normal(520, 60))

        df_batt = synthesizer.generate_battery_lifespan_cycles(
            num_cycles=random.randint(600, 850),
            ambient_temp_mean=amb_temp,
            c_rate_mean=c_rate,
            dod_mean=dod,
            knee_point_cycle=knee_cycle,
            add_anomalies=(b_idx % 8 == 0),
        )
        df_batt["battery_id"] = f"EV-BATT-{b_idx+1:03d}"
        all_dfs.append(df_batt)

    combined_df = pd.concat(all_dfs, ignore_index=True)
    return combined_df


if __name__ == "__main__":
    print("Synthesizing EV Battery Fleet Dataset...")
    fleet_data = generate_fleet_training_dataset(num_batteries=25)
    print(f"Generated {len(fleet_data)} total cycle records across 25 battery packs.")
    print("Sample records:")
    print(fleet_data[["battery_id", "cycle_index", "soh_percent", "capacity_ah", "internal_resistance_ohm", "rul_cycles"]].head(10))
    fleet_data.to_csv("battery_fleet_dataset.csv", index=False)
    print("Saved to battery_fleet_dataset.csv")
