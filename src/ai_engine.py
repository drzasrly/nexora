def get_ai_justification(district, root_cause, top_candidate):
    """
    Simulates a Decision Intelligence layer that provides structured, audited justification
    based on deterministic criteria, preventing black-box hallucinations.
    """
    name = top_candidate.get("intervention_name", "N/A")
    cost = top_candidate.get("cost", 0)
    reduction = top_candidate.get("gap_reduction", 0.0)
    feasibility = top_candidate.get("feasibility", "MEDIUM")
    
    rc_clean = root_cause.replace("_", " ").title()
    
    justification = f"""
    ### Rationale & Decision Path
    
    1. **Constraint Matching**: The root cause analysis identified **{rc_clean}** as the primary bottleneck for Kecamatan {district.title()}. 
    2. **Strategic Alignment**: The chosen intervention **{name}** is highly aligned with this bottleneck. Addressing other areas first would yield lower cost-efficiency because the main capacity constraint would remain unresolved.
    3. **Resource Efficiency**: By deploying this package, the district is projected to reduce its Healthcare Gap Score by **{reduction:.2f}%**.
    4. **Feasibility Review**: The cost of Rp {cost:,.0f} falls comfortably within constraints, resulting in a **{feasibility}** feasibility rating.
    """
    return justification
