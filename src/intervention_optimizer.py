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
        avail = resources_available.get(r_type, 0) # Fallback 0 (Section 34)
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
            {"intervention_id": "I01", "intervention_name": "Redistribute Doctors", "target_component": "workforce", "resource_type": "doctors", "unit": "person", "cost_per_unit": 50000000, "max_units": 20, "impact_type": "recalculate"},
            {"intervention_id": "I02", "intervention_name": "Redistribute Nurses", "target_component": "workforce", "resource_type": "nurses", "unit": "person", "cost_per_unit": 40000000, "max_units": 30, "impact_type": "recalculate"},
            {"intervention_id": "I03", "intervention_name": "Redistribute Midwives", "target_component": "workforce", "resource_type": "midwives", "unit": "person", "cost_per_unit": 40000000, "max_units": 20, "impact_type": "recalculate"},
            {"intervention_id": "I04", "intervention_name": "Add Beds", "target_component": "facility", "resource_type": "beds", "unit": "bed", "cost_per_unit": 250000000, "max_units": 100, "impact_type": "recalculate"},
            {"intervention_id": "I05", "intervention_name": "Add Facility", "target_component": "facility", "resource_type": "facilities", "unit": "facility", "cost_per_unit": 1000000000, "max_units": 5, "impact_type": "recalculate"}
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
        res_type = row["resource_type"]
        
        # Check budget limit strictly (Section 33 & 35)
        if budget < cost_unit:
            continue
            
        qty = min(max_u, int(budget // cost_unit))
        
        # Check resource constraint strictly (Section 34)
        avail = resources_available.get(res_type, 0)
        qty = min(qty, avail)
        
        if qty <= 0:
            continue
            
        cost = qty * cost_unit
        
        # Map quantity to resources used and deltas
        used_res = {res_type: qty}
        deltas = {}
        
        if res_type == "doctors":
            deltas["doctors"] = qty
        elif res_type == "nurses":
            deltas["nurses"] = qty
        elif res_type == "midwives":
            deltas["midwives"] = qty
        elif res_type == "beds":
            deltas["beds"] = qty
        elif res_type == "facilities":
            deltas["faskes"] = qty
            deltas["beds"] = qty * 10  # Built facility includes bed units
            used_res["beds"] = qty * 10
            
        # Feasibility check
        feasibility = get_feasibility_status(cost, budget, used_res, resources_available)
        if feasibility == "NOT_FEASIBLE":
            continue
            
        # Run simulation
        sim_res = simulate_intervention(df_features, district, deltas, config)
        improvement = sim_res["improvement_percent"]
        projected_gap = sim_res["after_gap"]
        
        # Alignment check (Section 39)
        aligned = False
        if primary_rc == "WORKFORCE_SHORTAGE" and i_id in ["I01", "I02", "I03"]:
            aligned = True
        elif primary_rc == "FACILITY_SHORTAGE" and i_id in ["I04", "I05"]:
            aligned = True
        elif primary_rc == "ACCESS_BARRIERS" and i_id == "I04":
            aligned = True
        elif primary_rc in ["MULTI_FACTOR", "HIGH_DEMAND", "DISEASE_BURDEN"] and i_id == "I05":
            aligned = True
            
        # Cost efficiency score = gap_reduction / cost * 1e9 (Section 39)
        cost_eff = (improvement / cost) * 1e9 if cost > 0 else 0.0
        align_multiplier = 2.0 if aligned else 1.0
        opt_score = cost_eff * align_multiplier
        
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
