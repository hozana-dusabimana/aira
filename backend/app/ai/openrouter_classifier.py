"""OpenRouter vision-model accident classifier.

Sends the uploaded photo to a vision LLM via OpenRouter and asks whether it
shows a road traffic accident. This is an OPTIONAL, clearly-labelled classifier:
it is used only when ``OPENROUTER_ENABLED`` is true and an ``OPENROUTER_API_KEY``
is configured; otherwise :func:`predict_accident_prob` returns ``None`` and the
caller falls back to our self-trained CNN / rules.

Privacy note: enabling this sends the uploaded image to OpenRouter (a third-party
provider). Keep it off unless that is acceptable for your data.
"""
from __future__ import annotations

import base64
import json
import logging
import re
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

_PROMPT = (
    "You are the image classifier for a road-accident reporting app. Look at the "
    "photo and decide if it shows a REAL road traffic accident: a vehicle "
    "collision or crash with visible damage/wreckage. Anything else — an intact "
    "car, ordinary traffic, a fire, people, objects, scenery — is NOT an "
    "accident. Reply with ONLY compact JSON, no prose: "
    '{"accident": true or false, "confidence": a number from 0 to 1}.'
)


def _extract_json(text: str) -> Optional[dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def predict_accident_prob(image_bytes: bytes) -> Optional[float]:
    """Return P(accident) in [0,1] from the OpenRouter vision model, or ``None``.

    ``None`` means disabled/unavailable/failed — caller should fall back.
    """
    if not getattr(settings, "OPENROUTER_ENABLED", False):
        return None
    api_key = getattr(settings, "OPENROUTER_API_KEY", "") or ""
    if not api_key:
        logger.info("OPENROUTER_ENABLED but no OPENROUTER_API_KEY; falling back.")
        return None
    try:
        import httpx

        b64 = base64.b64encode(image_bytes).decode("ascii")
        model = getattr(settings, "OPENROUTER_MODEL",
                        "meta-llama/llama-3.2-11b-vision-instruct:free")
        payload = {
            "model": model,
            "temperature": 0,
            "max_tokens": 60,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }],
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # OpenRouter recommends these; harmless if ignored.
            "HTTP-Referer": "https://aira.isiri.rw",
            "X-Title": "AIRA",
        }
        timeout = float(getattr(settings, "OPENROUTER_TIMEOUT", 30))
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(_ENDPOINT, headers=headers, json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = _extract_json(content)
        if data is None:
            logger.warning("OpenRouter returned unparseable content: %r", content[:120])
            return None
        is_accident = bool(data.get("accident"))
        conf = data.get("confidence")
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.9 if is_accident else 0.9
        conf = max(0.0, min(1.0, conf))
        # Convert to P(accident): confidence is the model's certainty in its label.
        prob = conf if is_accident else (1.0 - conf)
        logger.info("OpenRouter (%s): accident=%s conf=%.2f -> P(accident)=%.2f",
                    model, is_accident, conf, prob)
        return float(prob)
    except Exception as exc:  # noqa: BLE001 - any failure => fall back
        logger.warning("OpenRouter classify failed (%s); falling back.", exc)
        return None
