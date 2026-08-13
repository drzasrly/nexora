import os
import pandas as pd
from src.simulation_engine import simulate_intervention

def get_feasibility_status(cost, budget, resources_used, resources_available):
    """
    Determines qualitative feasibility.
    """
    if cost > budget:
        return "NOT_FEASIBLE"
    
    for r_type, qty in resources_used.items():
        avail = resources_available.get(r_type, 999)
        if qty > avail:
            return "NOT_FEASIBLE"
            
    if cost > 0.8 * budget:
        return "MEDIUM"
        
    return "HIGH"

def optimize_interventions(df_features, district, budget, resources_available, config):
    """
    Evaluates different intervention paths, simulates their outcomes,
    and returns a sorted ranking list of candidate options.
    """
    # Load interventions database
    interventions_path = "data/processed/interventions.csv"
    if not os.path.exists(interventions_path):
        interventions_df = pd.DataFrame([
            {"intervention_id": "I01", "intervention_name": "Redistribute Healthcare Workers", "target_component": "workforce", "unit": "person", "cost_per_unit": 50000000, "max_units": 20, "impact_per_unit": 0.015},
            {"intervention_id": "I02", "intervention_name": "Add Healthcare Workers", "target_component": "workforce", "unit": "person", "cost_per_unit": 150000000, "max_units": 30, "impact_per_unit": 0.02},
            {"intervention_id": "I03", "intervention_name": "Add Facility Capacity", "target_component": "facility", "unit": "bed", "cost_per_unit": 250000000, "max_units": 15, "impact_per_unit": 0.04},
            {"intervention_id": "I04", "intervention_name": "Improve Accessibility", "target_component": "accessibility", "unit": "road_km", "cost_per_unit": 500000000, "max_units": 5, "impact_per_unit": 0.05},
            {"intervention_id": "I05", "intervention_name": "Combined Intervention", "target_component": "combined", "unit": "package", "cost_per_unit": 750000000, "max_units": 4, "impact_per_unit": 0.08}
        ])
    else:
        interventions_df = pd.read_csv(interventions_path)
        
    # Get district row to find its primary root cause
    root_cause_path = "data/processed/root_cause_analysis.csv"
    primary_rc = "WORKFORCE_SHORTAGE"
    if os.path.exists(root_cause_path):
        df_rca = pd.read_csv(root_cause_path)
        dist_row = df_rca[df_rca["kecamatan"].str.strip().str.upper() == district.strip().upper()]
        if not dist_row.empty:
            primary_rc = dist_row.iloc[0].get("primary_root_cause", "WORKFORCE_SHORTAGE")
            
    candidates = []
    
    for idx, row in interventions_df.iterrows():
        i_id = row["intervention_id"]
        i_name = row["intervention_name"]
        cost_unit = int(row["cost_per_unit"])
        max_u = int(row["max_units"])
        
        # Check budget limit strictly (Perbaikan 7)
        if budget < cost_unit:
            continue
            
        qty = min(max_u, int(budget // cost_unit))
        if qty <= 0:
            continue
            
        cost = qty * cost_unit
        
        # Map quantity to resources used and deltas
        used_res = {}
        deltas = {}
        
        if i_id == "I01": # Redistribute Doctors
            used_res["doctors"] = qty
            deltas["doctors"] = qty
        elif i_id == "I02": # Add Nurses
            used_res["nurses"] = qty
            deltas["perawat"] = qty
        elif i_id == "I03": # Add Bed Capacity
            used_res["beds"] = qty
            deltas["beds"] = qty
            deltas["faskes"] = max(1, int(qty / 5))
        elif i_id == "I04": # Accessibility
            deltas["accessibility_offset"] = 0.0
        elif i_id == "I05": # Combined Package
            used_res["doctors"] = qty * 2
            used_res["nurses"] = qty * 4
            used_res["beds"] = qty * 10
            
            deltas["doctors"] = qty * 2
            deltas["perawat"] = qty * 4
            deltas["beds"] = qty * 10
            deltas["faskes"] = 1
            deltas["accessibility_offset"] = 0.0
            
        # Resource availability check
        is_feasible = True
        for r_type, req_qty in used_res.items():
            avail = resources_available.get(r_type, 999)
            if req_qty > avail:
                is_feasible = False
                break
                
        if not is_feasible:
            continue
            
        # Feasibility check
        feasibility = get_feasibility_status(cost, budget, used_res, resources_available)
        if feasibility == "NOT_FEASIBLE":
            continue
            
        # Run simulation
        sim_res = simulate_intervention(df_features, district, deltas, config)
        improvement = sim_res["improvement_percent"]
        projected_gap = sim_res["after_gap"]
        
        # Alignment check (Perbaikan 8)
        aligned = False
        if primary_rc == "WORKFORCE_SHORTAGE" and i_id in ["I01", "I02"]:
            aligned = True
        elif primary_rc == "FACILITY_SHORTAGE" and i_id == "I03":
            aligned = True
        elif primary_rc == "ACCESS_BARRIERS" and i_id == "I04":
            aligned = True
        elif primary_rc in ["MULTI_FACTOR", "HIGH_DEMAND"] and i_id == "I05":
            aligned = True
            
        feas_coeff = 1.0 if feasibility == "HIGH" else (0.5 if feasibility == "MEDIUM" else 0.0)
        align_coeff = 2.0 if aligned else 1.0
        opt_score = improvement * align_coeff * feas_coeff
        
        candidates.append({
            "intervention_id": i_id,
            "intervention_name": i_name,
            "quantity": qty,
            "unit": row["unit"],
            "cost": cost,
            "projected_gap": projected_gap,
            "gap_reduction": improvement,
            "feasibility": feasibility,
            "alignment": "HIGH" if aligned else "LOW",
            "score": opt_score,
            "resources_used": used_res
        })
        
    # Sort candidates by optimizer score descending
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    return candidates
