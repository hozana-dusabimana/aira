"""Generates structured incident descriptions from analyzer output."""
from __future__ import annotations

from app.ai.image_analyzer import AnalysisResult


def generate_description(result: AnalysisResult) -> str:
    """Return a human-readable, officer-friendly summary."""
    lines = [
        f"AI-generated incident summary",
        f"- Scene: {result.scene_label}",
        f"- Likely incident type: {result.incident_type or 'unspecified'}",
        f"- Estimated severity: {result.severity_level}",
        f"- Confidence: {round(result.confidence_score * 100)}%",
    ]
    if result.detected_objects:
        objs = ", ".join(
            f"{o.get('label', 'object')} ({int(round(o.get('confidence', 0) * 100))}%)"
            for o in result.detected_objects[:6]
        )
        lines.append(f"- Detected objects: {objs}")
    if result.caption:
        lines.append(f"- Caption: {result.caption.strip()}")
    return "\n".join(lines)
