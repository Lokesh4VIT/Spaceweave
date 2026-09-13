def spatial_score(width, depth, available_width, available_depth, clearance=10.0):
    if not available_width and not available_depth:
        return 0.5, "Dimensions not provided; spatial fit is neutral."
    if width is None or depth is None:
        return 0.45, "Product dimensions are incomplete; verify dimensions before purchase."
    req_w = width + clearance
    req_d = depth + clearance
    if available_width and req_w > available_width:
        return 0.0, f"Too wide: product {width:.0f} cm + {clearance:.0f} cm clearance exceeds {available_width:.0f} cm available."
    if available_depth and req_d > available_depth:
        return 0.0, f"Too deep: product {depth:.0f} cm + {clearance:.0f} cm clearance exceeds {available_depth:.0f} cm available."
    ratios=[]
    if available_width: ratios.append(req_w/available_width)
    if available_depth: ratios.append(req_d/available_depth)
    utilization=sum(ratios)/len(ratios)
    # Reward good utilization without packing the room wall-to-wall.
    if utilization <= 0.45: score=0.72
    elif utilization <= 0.70: score=0.92
    elif utilization <= 0.88: score=1.0
    else: score=0.86
    return score, f"Fits with clearance; uses about {utilization*100:.0f}% of the supplied available footprint."

def quality_score(rating, reviews):
    r=(rating or 0)/5.0
    volume=min(1.0, (reviews or 0)/5000)
    return 0.75*r + 0.25*volume

def value_score(price, max_budget):
    if not max_budget: return 0.7
    if price > max_budget: return 0.0
    # Best value is not necessarily the cheapest: prefer sensible use of budget.
    utilization=price/max_budget
    return 0.65 + 0.35*min(1.0, utilization/0.8)
