import os
import pandas as pd

def generate_recommendation_report(district, root_cause, top_candidate, budget, file_path="outputs/reports/recommendation_report.md"):
    """
    Synthesizes the recommendation details and exports a markdown report file.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Calculate confidence based on feasibility and alignment
    feasibility = top_candidate.get("feasibility", "MEDIUM")
    alignment = top_candidate.get("alignment", "LOW")
    
    if feasibility == "HIGH" and alignment == "HIGH":
        confidence = "HIGH"
    elif feasibility in ["HIGH", "MEDIUM"] and alignment in ["HIGH", "LOW"]:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
        
    cost = top_candidate.get("cost", 0)
    qty = top_candidate.get("quantity", 0)
    unit = top_candidate.get("unit", "units")
    name = top_candidate.get("intervention_name", "N/A")
    gap_reduction = top_candidate.get("gap_reduction", 0.0)
    projected_gap = top_candidate.get("projected_gap", 0.0)
    
    # Format resources used
    res_details = []
    for res_name, amount in top_candidate.get("resources_used", {}).items():
        res_details.append(f"+{amount} {res_name.title()}")
    res_str = ", ".join(res_details) if res_details else f"+{qty} {unit}"

    report_content = f"""# HEAL-CITY Recommendation Report

## Executive Summary
- **Target District**: Kecamatan {district.title()}
- **Priority Classification**: CRITICAL
- **Primary Root Cause**: {root_cause.replace('_', ' ').title()}
- **Recommended Intervention**: {name}
- **Proposed Budget**: Rp {budget:,.0f}

---

## Detailed Plan & Resource Allocation
- **Action**: Allocate {qty} {unit}(s) for {name}.
- **Required Resources**: {res_str}
- **Estimated Cost**: Rp {cost:,.0f} (Feasibility: {feasibility})
- **Confidence Level**: **{confidence}**

---

## Projected Outcomes & Impact
- **Original Gap Score**: {projected_gap + gap_reduction:.2f}
- **Simulated Gap Score**: {projected_gap:.2f}
- **Gap Reduction Impact**: **{gap_reduction:.2f}%**

---

## Strategic Justification (Why this was chosen)
The primary root cause identified in Kecamatan {district.title()} is **{root_cause.replace('_', ' ').title()}**. 
The intervention **"{name}"** directly addresses this bottleneck. 
By focusing capital and manpower on this specific constraint, the system maximizes resource efficiency and ensures the highest possible drop in health service gaps while keeping costs within the allocated budget.
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    return {
        "district": district,
        "root_cause": root_cause,
        "recommended_action": name,
        "cost": cost,
        "resources": res_str,
        "projected_gap": projected_gap,
        "improvement": gap_reduction,
        "feasibility": feasibility,
        "confidence": confidence,
        "report_path": file_path
    }
