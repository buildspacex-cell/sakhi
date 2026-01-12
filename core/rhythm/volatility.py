def compute_volatility(vectors):
    """
    Mean absolute deviation of dominant element magnitude.
    """
    if not vectors:
        return 0.0
    dominant_values = [
        max(v.items(), key=lambda x: x[1])[1]
        for v in vectors
    ]
    mean = sum(dominant_values) / len(dominant_values)
    return sum(abs(v - mean) for v in dominant_values) / len(dominant_values)
