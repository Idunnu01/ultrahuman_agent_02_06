"""
Metrics service for processing Ultrahuman Ring data and user lifestyle events
"""

import os
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple
import uuid

import requests
import numpy as np
import pandas as pd  # noqa: F401
from sqlalchemy import func  # ✅ used in get_available_metrics_for_user

from app.models import User, Metric, SystemLog, Conversation
from utils.database import db, bulk_insert_metrics
from utils.cache import MetricsCache, cache_user_data
from utils.stats_utils import StatisticalValidator, RobustStatistics
from enhanced_nlp_parser import EnhancedHealthQueryParser, ParsedQuery
from enhanced_metric_lookup import EnhancedMetricLookup

logger = logging.getLogger(__name__)

# --------- Intent patterns & metric synonyms ---------

METRIC_SYNONYMS: Dict[str, List[str]] = {
    "hrv": ["hrv", "heart rate variability", "variability"],
    "heart_rate": ["heart rate", "resting heart rate", "rhr", "pulse"],
    "sleep_score": ["sleep score", "sleep quality", "sleep efficiency", "sleep"],
    "temperature": ["temperature", "body temperature", "skin temp", "temp"],
    "recovery": ["recovery", "recovery score", "readiness"],
    "stress": ["stress", "stress index"],
    "activity": ["activity", "activity score", "movement", "active minutes"],
    "steps": ["steps", "step count"],
    "vo2_max": ["vo2", "vo2 max", "vo₂max"],
    "average_glucose": ["average glucose", "glucose average", "blood sugar average"],
    "glucose_variability": ["glucose variability", "glycemic variability", "gv"],
    "time_in_target": ["time in target", "time in range"],
    "metabolic_score": ["metabolic score"],
    "hba1c": ["hba1c", "a1c"],
}

INTENT_PATTERNS = {
    "correlation": re.compile(r"\b(correlation|correlate|relationship|link|associated|between.*and)\b", re.I),
    "trend": re.compile(r"\b(trend|trending|over the last|past\s+\d+\s*(days?|weeks?)|improving|worsening|stable)\b", re.I),
    "health_advice": re.compile(r"\b(how do i|how can i|how to|what should i|should i|ways to|tips for|advice|help|improve|increase|decrease|lower|reduce|boost|raise)\b", re.I),
    "general_health": re.compile(r"\b(heart rate|blood pressure|sleep|stress|weight|exercise|diet|nutrition|recovery|hrv|temperature|anxiety|breathing|meditation|wellness|health)\b", re.I),
    "pattern": re.compile(r"\b(pattern|time[- ]of[- ]day|weekly|weekday|association)\b", re.I),
    "anomaly": re.compile(r"\b(anom|anomal|spike|unusually|deviation|outlier|abnormal)\b", re.I),
    "intervention": re.compile(r"\b(improved|improving|effect|help(?:ed)?|impact)\b.*\b(magnesium|caffeine|walk|evening|supplement|cutoff)\b", re.I),
    "direct_query": re.compile(r"\b(what was|what is|show me|highest|lowest|average|maximum|minimum|when do|what time)\b", re.I),
}

# Follow-up detection patterns for conversation context
FOLLOW_UP_PATTERNS = [
    # Direct references to previous results
    re.compile(r"\b(what about|how about|and also|also|too)\b", re.I),
    re.compile(r"\b(that|it|this|the result|my last|previous)\b", re.I),
    re.compile(r"\b(more|details|explain|why(?!\s+is)|how(?!\s+is)|show me more)\b", re.I),

    # Comparative follow-ups
    re.compile(r"\b(compared to|versus|vs\.?|against|than)\b", re.I),
    re.compile(r"\b(same for|what if|how does that|does that|does this)\b", re.I),

    # Contextual references
    re.compile(r"\b(over time|trend|pattern|changes?)\b", re.I),
    re.compile(r"\b(other metrics?|anything else|different|another)\b", re.I),
]

# Context-aware question starters
CONTEXT_QUESTIONS = [
    "what about", "how about", "and", "also", "what if", "how does",
    "compared to", "versus", "vs", "same for", "show me", "tell me",
    "more", "details", "explain", "why", "how", "trend", "pattern"
]


def _canonical_metric(term: str) -> Optional[str]:
    t = term.lower().strip()
    for canon, aliases in METRIC_SYNONYMS.items():
        if any(a in t for a in aliases):
            return canon
    return None


def _extract_two_metrics_freeform(message: str) -> List[str]:
    """
    Loosely extract up to two metrics from free text.
    - honors 'between X and Y', 'X & Y', 'X vs Y', 'X with Y' patterns
    - falls back to scanning for synonyms
    """
    msg = message.lower()

    # Try explicit conjunction patterns first
    parts = re.split(r"\b(?:between|vs|versus|with|and|&)\b", msg)
    candidates = [p.strip() for p in parts if p.strip()]

    metrics: List[str] = []
    for c in candidates:
        m = _canonical_metric(c)
        if m and m not in metrics:
            metrics.append(m)
        if len(metrics) == 2:
            return metrics

    # Fallback: scan whole string for known aliases (preserve order)
    for canon, aliases in METRIC_SYNONYMS.items():
        if any(a in msg for a in aliases) and canon not in metrics:
            metrics.append(canon)
            if len(metrics) == 2:
                break
    return metrics[:2]


class MetricsService:
    """Core service for handling all health metrics and lifestyle data"""

    def __init__(self):
        self.ultrahuman_base_url = os.getenv("ULTRAHUMAN_API_BASE", "https://api.ultrahuman.com").rstrip("/")
        self.ultrahuman_api_key = os.getenv("ULTRAHUMAN_API_KEY")
        self.store_minute_series = os.getenv("ULTRAHUMAN_STORE_MINUTE_SERIES", "1") == "1"  # Default to True for real-time

        # Initialize enhanced NLP parser with proven date parsing
        self.nlp_parser = EnhancedHealthQueryParser()

        # Initialize enhanced metric lookup system
        self.enhanced_lookup = EnhancedMetricLookup()

        self.metric_mappings = {
            "heart_rate_variability": "hrv",
            "sleep_score": "sleep_score",
            "resting_heart_rate": "heart_rate",
            "skin_temperature": "temperature",
            "recovery_score": "recovery",
            "stress_index": "stress",
            "activity_score": "activity",
            "readiness_score": "readiness",
        }

        self.lifestyle_event_types = {
            "meal", "supplement", "activity", "stress", "alcohol",
            "caffeine", "sleep_quality", "mood", "symptoms", "travel"
        }

    # --------------------------- helpers ---------------------------

    @staticmethod
    def _resolve_uh_email(user: Optional[User]) -> Optional[str]:
        # Priority order: user-specific email > user ultrahuman_user_id > global fallback
        if user:
            # Check user preferences first
            prefs = getattr(user, "preferences", None) or {}
            if prefs.get("ultrahuman_email"):
                return prefs["ultrahuman_email"]
            if prefs.get("email"):
                return prefs["email"]
            # Use user's ultrahuman_user_id if available
            if hasattr(user, "ultrahuman_user_id") and user.ultrahuman_user_id:
                return user.ultrahuman_user_id

        # Fallback to global setting (for backward compatibility)
        uh_email = os.getenv("UH_EMAIL")
        if uh_email:
            return uh_email

        return None

    def _to_float(self, x):
        try:
            if x is None:
                return None
            if isinstance(x, (int, float)):
                return float(x)
            if isinstance(x, str) and x.strip() != "":
                return float(x)
        except (ValueError, TypeError):
            return None

    # ---------------------------- fetch ----------------------------

    def fetch_ultrahuman_data(
        self, user_id: str, start_date: Union[str, datetime], end_date: Union[str, datetime]
    ) -> Dict:
        try:
            user = User.query.get(user_id)
            if not user:
                return {"error": "User not found", "user_id": user_id}

            api_key = self.ultrahuman_api_key
            if not api_key:
                return {"error": "Missing ULTRAHUMAN_API_KEY", "user_id": user_id}

            uh_email = self._resolve_uh_email(user)
            if not uh_email:
                return {
                    "error": "Missing Ultrahuman email (UH_EMAIL or user preferences or ultrahuman_user_id)",
                    "user_id": user_id,
                }

            start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            if start_dt >= end_dt:
                return {"error": "Invalid date range: start_date must be before end_date", "user_id": user_id}

            s = start_dt.date()
            e = end_dt.date()

            # Partner API per-day
            if "partner.ultrahuman.com" in (self.ultrahuman_base_url or ""):
                headers = {"Authorization": api_key, "Accept": "application/json"}
                day = s
                all_metrics: Dict[str, List[dict]] = {"hrv": [], "sleep": [], "activity": [], "recovery": [], "series": []}
                chunks, errors = 0, []

                while day <= e:
                    try:
                        params = {"email": uh_email, "date": day.isoformat()}
                        resp = self._make_api_request("/metrics", headers, params) or {}
                        normalized = self._map_partner_to_internal(resp)
                        if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                            logger.info(
                                "Partner mapping %s → sleep=%d activity=%d hrv=%d recovery=%d series=%d",
                                day.isoformat(),
                                len(normalized.get("sleep", [])),
                                len(normalized.get("activity", [])),
                                len(normalized.get("hrv", [])),
                                len(normalized.get("recovery", [])),
                                len(normalized.get("series", [])),
                            )
                        for cat in ("sleep", "activity", "hrv", "recovery", "series"):
                            if normalized.get(cat):
                                all_metrics[cat].extend(normalized[cat])

                    except Exception as ex:
                        errors.append({"date": day.isoformat(), "error": str(ex)})
                    finally:
                        chunks += 1
                        day += timedelta(days=1)

                return {
                    "success": True,
                    "user_id": user_id,
                    "date_range": {"start": s.isoformat(), "end": e.isoformat()},
                    "metrics": all_metrics,
                    "total_data_points": sum(len(v) for v in all_metrics.values()),
                    "chunks_processed": chunks,
                    "errors": errors,
                    "completed_at": datetime.utcnow().isoformat(),
                }

            # Legacy (range)
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            start_str, end_str = s.isoformat(), e.isoformat()
            all_metrics: Dict[str, List[dict]] = {"hrv": [], "sleep": [], "activity": [], "recovery": [], "series": []}

            r = self._make_api_request(f"/users/{uh_email}/hrv", headers, {"start_date": start_str, "end_date": end_str})
            if r and isinstance(r, dict) and "data" in r:
                all_metrics["hrv"] = r.get("data") or []

            r = self._make_api_request(f"/users/{uh_email}/sleep", headers, {"start_date": start_str, "end_date": end_str})
            if r and isinstance(r, dict) and "data" in r:
                all_metrics["sleep"] = r.get("data") or []

            r = self._make_api_request(f"/users/{uh_email}/activity", headers, {"start_date": start_str, "end_date": end_str})
            if r and isinstance(r, dict) and "data" in r:
                all_metrics["activity"] = r.get("data") or []

            r = self._make_api_request(f"/users/{uh_email}/recovery", headers, {"start_date": start_str, "end_date": end_str})
            if r and isinstance(r, dict) and "data" in r:
                all_metrics["recovery"] = r.get("data") or []

            return {
                "success": True,
                "user_id": user_id,
                "date_range": {"start": start_str, "end": end_str},
                "metrics": all_metrics,
                "total_data_points": sum(len(v) for v in all_metrics.values()),
            }

        except Exception as e:
            logger.error(f"Ultrahuman API fetch failed for user {user_id}: {str(e)}")
            return {"error": str(e), "user_id": user_id}

    def _make_api_request(self, endpoint: str, headers: Dict, params: Dict) -> Optional[Dict]:
        try:
            url = f"{self.ultrahuman_base_url}{endpoint}"
            if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                logger.info(f"UH GET {url} params={params} hdrs={list(headers.keys())}")
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                logger.info(f"UH 404: {url} {params}")
                return None
            if resp.status_code == 401:
                logger.error("UH 401 Unauthorized - check API key")
                return None
            if resp.status_code == 429:
                logger.warning("UH 429 rate limited")
                return None
            logger.error(f"UH {resp.status_code}: {resp.text[:300]}")
            return None
        except requests.RequestException as e:
            logger.error(f"UH request failed: {str(e)}")
            return None

    # ------------------- partner → internal mapping -------------------
    # (unchanged except for earlier fixes)

    def _map_partner_to_internal(self, response: Dict) -> Dict[str, List[dict]]:
        out = {"sleep": [], "activity": [], "hrv": [], "recovery": [], "series": []}
        if not isinstance(response, dict):
            return out

        payload = response.get("data") or response.get("metrics") or response
        metric_data = payload.get("metric_data") if isinstance(payload, dict) else None
        if not isinstance(metric_data, list):
            return self._map_partner_legacy_like(payload)

        def ts_iso(sec):
            try:
                return datetime.utcfromtimestamp(int(float(sec))).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                return None

        def day_iso(sec):
            try:
                return datetime.utcfromtimestamp(int(float(sec))).strftime("%Y-%m-%d")
            except Exception:
                return None

        def _num(x):
            try:
                return float(x)
            except Exception:
                return None

        recovery_by_day: Dict[str, Dict] = {}

        for item in metric_data:
            if not isinstance(item, dict):
                continue
            typ_raw = item.get("type")
            typ = (typ_raw or "").lower().strip()
            obj = item.get("object") or {}
            day_start = obj.get("day_start_timestamp")
            day_key = day_iso(day_start) if day_start else None

            # SLEEP
            if typ in ("sleep", "sleep_score", "sleep_summary"):
                s = {}
                details = obj.get("details") or {}
                bt_start = details.get("bedtime_start")
                s["bedtime"] = ts_iso(bt_start or day_start)
                sc = obj.get("score")
                if sc is None:
                    ss = obj.get("sleep_score")
                    if isinstance(ss, dict):
                        sc = ss.get("score")
                if sc is not None:
                    s["sleep_score"] = sc
                total_sleep_min = None
                qm = details.get("quick_metrics") or []
                for q in qm:
                    qtype = (q.get("type") or "").lower()
                    if qtype == "total_sleep" and "value" in q:
                        total_sleep_min = float(q["value"]) / 60.0
                        s["total_sleep_time"] = total_sleep_min
                    if qtype in ("sleep_efic", "sleep_efficiency") and "value" in q:
                        s["sleep_efficiency"] = q["value"]
                if "sleep_efficiency" not in s:
                    for summ in details.get("summary") or []:
                        title = (summ.get("title") or "").lower()
                        if title.startswith("sleep efficiency") and "score" in summ:
                            s["sleep_efficiency"] = summ["score"]
                            break
                stages = details.get("sleep_stages") or []
                deep_pct = None
                rem_pct = None
                for st in stages:
                    t = (st.get("type") or "").lower()
                    if t == "deep_sleep":
                        deep_pct = _num(st.get("percentage"))
                    elif t == "rem_sleep":
                        rem_pct = _num(st.get("percentage"))
                if total_sleep_min:
                    if deep_pct is not None:
                        s["deep_sleep_minutes"] = (deep_pct / 100.0) * total_sleep_min
                    if rem_pct is not None:
                        s["rem_sleep_minutes"] = (rem_pct / 100.0) * total_sleep_min
                if any(k in s for k in ("sleep_score", "sleep_efficiency", "total_sleep_time", "deep_sleep_minutes", "rem_sleep_minutes", "bedtime")):
                    out["sleep"].append(s)
                continue

            # TEMPERATURE (both individual readings and daily avg)
            if typ == "temp":
                vals = obj.get("values") or []
                # Store individual temperature readings with timestamps
                for v in vals:
                    if not v or v.get("value") is None or v.get("timestamp") is None:
                        continue
                    ts = ts_iso(v.get("timestamp"))
                    num = _num(v.get("value"))
                    if ts and num is not None:
                        out["series"].append({"metric_type": "temperature", "timestamp": ts, "value": num, "unit": "celsius"})

                # Also calculate daily average
                nums = [_num(v.get("value")) for v in vals if v and v.get("value") is not None]
                if nums and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["skin_temperature"] = float(sum(nums) / len(nums))
                continue

            # HRV (both individual values and daily avg)
            if typ == "hrv":
                # Store individual HRV values with real timestamps
                vals = obj.get("values") or []
                for v in vals:
                    if not v or v.get("value") is None or v.get("timestamp") is None:
                        continue
                    ts = ts_iso(v.get("timestamp"))
                    num = _num(v.get("value"))
                    if ts and num is not None:
                        out["series"].append({"metric_type": "hrv", "timestamp": ts, "value": num, "unit": "ms"})

                # Also store daily average
                avg = _num(obj.get("avg"))
                ts = ts_iso(day_start)
                if avg is not None and ts:
                    out["hrv"].append({"timestamp": ts, "rmssd": avg})
                continue

            # AVG SLEEP HRV
            if typ == "avg_sleep_hrv":
                avg = _num(obj.get("avg"))
                if avg is None:
                    vals = obj.get("values") or []
                    arr = [_num(v.get("value")) for v in vals if v and v.get("value") is not None]
                    if arr:
                        avg = float(sum(arr) / len(arr))
                ts = ts_iso(day_start)
                if avg is not None and ts:
                    out["hrv"].append({"timestamp": ts, "sleep_rmssd": avg})
                continue

            # NIGHT RESTING HR
            if typ in ("night_rhr", "sleep_rhr"):
                avg = _num(obj.get("avg"))
                if avg is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["resting_heart_rate"] = avg
                continue

            # STEPS (both individual counts and daily total)
            if typ == "steps":
                vals = obj.get("values") or []
                # Store individual step counts with timestamps for hourly tracking
                for v in vals:
                    if not v or v.get("value") is None or v.get("timestamp") is None:
                        continue
                    ts = ts_iso(v.get("timestamp"))
                    num = _num(v.get("value"))
                    if ts and num is not None:
                        out["series"].append({"metric_type": "steps", "timestamp": ts, "value": num, "unit": "count"})

                # Also store daily total
                svals = [_num(v.get("value")) for v in vals if v and v.get("value") is not None]
                if svals and day_start:
                    out["activity"].append({"date": day_iso(day_start), "steps": float(sum(svals))})
                continue

            # ACTIVE MINUTES
            if typ == "active_minutes":
                val = _num(obj.get("value"))
                if val is None:
                    vals = obj.get("values") or []
                    arr = [_num(v.get("value")) for v in vals if v and v.get("value") is not None]
                    if arr:
                        val = float(sum(arr))
                if val is not None and day_start:
                    out["activity"].append({"date": day_iso(day_start), "active_minutes": val})
                continue

            # RECOVERY SCORE / INDEX
            if typ in ("recovery", "recovery_index"):
                val = _num(obj.get("score") or obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["recovery_score"] = val
                continue

            # GLUCOSE (daily + series)
            if typ == "glucose":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["average_glucose"] = val
                # Always store glucose readings with timestamps for real-time tracking
                vals = obj.get("values") or []
                for v in vals:
                    if not v or v.get("value") is None or v.get("timestamp") is None:
                        continue
                    ts = ts_iso(v.get("timestamp"))
                    num = _num(v.get("value"))
                    if ts and num is not None:
                        out["series"].append({"metric_type": "glucose", "timestamp": ts, "value": num, "unit": "mg/dL"})
                continue

            if typ == "average_glucose":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["average_glucose"] = val
                continue

            if typ == "glucose_variability":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["glucose_variability"] = val
                continue

            if typ == "metabolic_score":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["metabolic_score"] = val
                continue

            if typ == "hba1c":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["hba1c"] = val
                continue

            if typ == "time_in_target":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["time_in_target"] = val
                continue

            if typ == "movement_index":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["movement_index"] = val
                continue

            if typ == "vo2_max":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["vo2_max"] = val
                continue

            # HEART RATE (both daily avg and minute series)
            if typ == "hr":
                # Store individual HR values with real timestamps
                vals = obj.get("values") or []
                for v in vals:
                    if not v or v.get("value") is None or v.get("timestamp") is None:
                        continue
                    ts = ts_iso(v.get("timestamp"))
                    num = _num(v.get("value"))
                    if ts and num is not None:
                        out["series"].append({"metric_type": "heart_rate", "timestamp": ts, "value": num, "unit": "bpm"})

                # Also store daily average if available
                avg = _num(obj.get("avg"))
                if avg is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["resting_heart_rate"] = avg
                continue

            # MOTION/MOVEMENT (movement index and activity data)
            if typ == "motion":
                # Store individual motion values with timestamps
                vals = obj.get("values") or []
                for v in vals:
                    if not v or v.get("value") is None or v.get("timestamp") is None:
                        continue
                    ts = ts_iso(v.get("timestamp"))
                    num = _num(v.get("value"))
                    if ts and num is not None:
                        out["series"].append({"metric_type": "movement", "timestamp": ts, "value": num, "unit": "index"})

                # Also store daily average for movement index
                avg = _num(obj.get("avg"))
                if avg is not None and day_key:
                    recovery_by_day.setdefault(day_key, {"date": day_key})["movement_daily_avg"] = avg
                continue

        for day_data in recovery_by_day.values():
            if len(day_data) > 1:
                out["recovery"].append(day_data)

        return out

    def _map_partner_legacy_like(self, payload: Dict) -> Dict[str, List[dict]]:
        out = {"sleep": [], "activity": [], "hrv": [], "recovery": [], "series": []}
        if not isinstance(payload, dict):
            return out

        def _as_list(x):
            if not x:
                return []
            return x if isinstance(x, list) else [x]

        sleep_src = _as_list(payload.get("sleep")) or _as_list(payload.get("Sleep Data")) or _as_list(payload.get("sleep_data"))
        move_src = _as_list(payload.get("movement")) or _as_list(payload.get("Movement Data")) or _as_list(payload.get("activity")) or _as_list(payload.get("movement_data"))
        hrv_src = _as_list(payload.get("hrv")) or _as_list(payload.get("HRV")) or _as_list(payload.get("heart_rate_variability"))
        recovery_src = _as_list(payload.get("recovery_index")) or _as_list(payload.get("Recovery Index")) or _as_list(payload.get("recovery"))

        for s in sleep_src:
            if isinstance(s, dict):
                out["sleep"].append(s)
        for a in move_src:
            if isinstance(a, dict):
                out["activity"].append(a)
        for h in hrv_src:
            if isinstance(h, dict):
                out["hrv"].append(h)
        for r in recovery_src:
            if isinstance(r, dict):
                out["recovery"].append(r)

        # Process Sleep graph data (hr_graph, hrv_graph, temp_graph, movement_graph)
        self._extract_sleep_graph_data(metric_data, out)

        return out

    def _extract_sleep_graph_data(self, metric_data: list, out: dict):
        """Extract graph data from Sleep object similar to old graph_data.py"""
        sleep_obj = None
        for item in metric_data:
            if isinstance(item, dict) and item.get("type") == "Sleep":
                sleep_obj = item.get("object", {})
                break

        if not sleep_obj:
            return

        def ts_iso(sec):
            try:
                return datetime.utcfromtimestamp(int(float(sec))).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                return None

        def _num(x):
            try:
                return float(x)
            except Exception:
                return None

        # Extract graph fields similar to old system
        graph_fields = ["hr_graph", "hrv_graph", "temp_graph", "movement_graph"]

        for field in graph_fields:
            graph = sleep_obj.get(field, {})
            if not graph or not graph.get("data"):
                continue

            # Map field name to our metric type
            metric_type_map = {
                "hr_graph": "heart_rate",
                "hrv_graph": "hrv",
                "temp_graph": "temperature",
                "movement_graph": "movement"
            }
            metric_type = metric_type_map.get(field, field.replace("_graph", ""))

            for entry in graph["data"]:
                if not entry or entry.get("value") is None or entry.get("timestamp") is None:
                    continue

                ts = ts_iso(entry["timestamp"])
                num = _num(entry["value"])

                if ts and num is not None:
                    unit_map = {
                        "heart_rate": "bpm",
                        "hrv": "ms",
                        "temperature": "celsius",
                        "movement": "index"
                    }
                    unit = unit_map.get(metric_type, "units")

                    out["series"].append({
                        "metric_type": metric_type,
                        "timestamp": ts,
                        "value": num,
                        "unit": unit,
                        "context": "sleep_graph"
                    })

    # --------------------------- processing ---------------------------

    def process_ultrahuman_data(self, user_id: str, raw_data: Dict) -> Dict:
        try:
            processed_metrics: List[Dict] = []
            processing_stats = {
                "total_raw_points": 0,
                "processed_points": 0,
                "skipped_points": 0,
                "error_points": 0,
                "metrics_processed": [],
            }

            for data_type, data_points in (raw_data.get("metrics") or {}).items():
                if not data_points:
                    continue
                processing_stats["total_raw_points"] += len(data_points)
                processing_stats["metrics_processed"].append(data_type)

                for data_point in data_points:
                    try:
                        if data_type == "hrv":
                            metrics = self._process_hrv_data(user_id, data_point)
                        elif data_type == "sleep":
                            metrics = self._process_sleep_data(user_id, data_point)
                        elif data_type == "activity":
                            metrics = self._process_activity_data(user_id, data_point)
                        elif data_type == "recovery":
                            metrics = self._process_recovery_data(user_id, data_point)
                        elif data_type == "series":
                            metrics = self._process_series_data(user_id, data_point)
                        else:
                            metrics = []
                        if metrics:
                            processed_metrics.extend(metrics)
                            processing_stats["processed_points"] += len(metrics)
                        else:
                            processing_stats["skipped_points"] += 1
                    except Exception as e:
                        logger.warning(f"Failed to process data point: {str(e)}")
                        processing_stats["error_points"] += 1

            if processed_metrics:
                success = bulk_insert_metrics(processed_metrics, upsert_mode="update")
                if success:
                    logger.info(f"Processed {len(processed_metrics)} metrics for user {user_id}")
                    self._update_metrics_cache(user_id, processed_metrics)
                    return {"success": True, "metrics_inserted": len(processed_metrics), "processing_stats": processing_stats}
                else:
                    return {"error": "Database insertion failed"}
            else:
                return {"success": True, "metrics_inserted": 0, "message": "No new metrics to process"}

        except Exception as e:
            logger.error(f"Data processing failed for user {user_id}: {str(e)}")
            return {"error": str(e)}

    # ------------------------ per-type processors ------------------------

    def get_available_metrics_for_user(self, user_id: str, days_back: int = 7) -> Dict:
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)

            metrics_query = db.session.query(
                Metric.metric_type,
                func.count(Metric.id).label('count'),
                func.min(Metric.timestamp).label('earliest'),
                func.max(Metric.timestamp).label('latest')
            ).filter(
                Metric.user_id == user_id,
                Metric.timestamp >= start_time
            ).group_by(Metric.metric_type).all()

            available_metrics = {}
            for metric_type, count, earliest, latest in metrics_query:
                available_metrics[metric_type] = {
                    'count': count,
                    'earliest': earliest.isoformat() if earliest else None,
                    'latest': latest.isoformat() if latest else None,
                    'days_covered': (latest - earliest).days if earliest and latest else 0
                }

            return {
                'user_id': user_id,
                'date_range_requested': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat(),
                    'days': days_back
                },
                'available_metrics': available_metrics,
                'total_metric_types': len(available_metrics)
            }

        except Exception as e:
            logger.error(f"Failed to get available metrics for user {user_id}: {str(e)}")
            return {'error': str(e)}

    def _process_hrv_data(self, user_id: str, data_point: Dict) -> List[Dict]:
        try:
            metrics: List[Dict] = []
            timestamp = self._parse_timestamp(data_point.get("timestamp"))
            if "rmssd" in data_point:
                val = self._to_float(data_point.get("rmssd"))
                if val is not None:
                    metrics.append({
                        "user_id": user_id, "metric_type": "hrv", "value": val,
                        "unit": "ms", "timestamp": timestamp, "source": "ultrahuman",
                        "meta_data": {"raw_data": data_point, "context": "daily"}
                    })
            if "sleep_rmssd" in data_point:
                val = self._to_float(data_point.get("sleep_rmssd"))
                if val is not None:
                    metrics.append({
                        "user_id": user_id, "metric_type": "hrv_sleep", "value": val,
                        "unit": "ms", "timestamp": timestamp, "source": "ultrahuman",
                        "meta_data": {"raw_data": data_point, "context": "sleep_avg"}
                    })
            if "pnn50" in data_point:
                val = self._to_float(data_point.get("pnn50"))
                if val is not None:
                    metrics.append({
                        "user_id": user_id, "metric_type": "hrv_pnn50", "value": val,
                        "unit": "percent", "timestamp": timestamp, "source": "ultrahuman",
                        "meta_data": {"raw_data": data_point}
                    })
            if "stress_index" in data_point:
                val = self._to_float(data_point.get("stress_index"))
                if val is not None:
                    metrics.append({
                        "user_id": user_id, "metric_type": "stress", "value": val,
                        "unit": "index", "timestamp": timestamp, "source": "ultrahuman",
                        "meta_data": {"raw_data": data_point}
                    })
            return metrics
        except Exception as e:
            logger.warning(f"HRV data processing failed: {str(e)}")
            return []

    def _process_sleep_data(self, user_id: str, data_point: Dict) -> List[Dict]:
        try:
            metrics: List[Dict] = []
            timestamp = self._parse_timestamp(data_point.get('bedtime'))
            v = self._to_float(data_point.get('sleep_score'))
            if v is not None:
                metrics.append({
                    'user_id': user_id, 'metric_type': 'sleep_score', 'value': v,
                    'unit': 'score', 'timestamp': timestamp, 'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point,
                                  'total_sleep_time': data_point.get('total_sleep_time'),
                                  'sleep_efficiency': data_point.get('sleep_efficiency'),
                                  'wake_after_sleep_onset': data_point.get('waso')}
                })
            v = self._to_float(data_point.get('sleep_efficiency'))
            if v is not None:
                metrics.append({
                    'user_id': user_id, 'metric_type': 'sleep_efficiency', 'value': v,
                    'unit': 'percent', 'timestamp': timestamp, 'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })
            total_sleep = self._to_float(data_point.get('total_sleep_time'))
            deep_minutes = self._to_float(data_point.get('deep_sleep_minutes'))
            if total_sleep and deep_minutes is not None and total_sleep > 0:
                metrics.append({
                    'user_id': user_id, 'metric_type': 'deep_sleep_percentage',
                    'value': float((deep_minutes / total_sleep) * 100.0),
                    'unit': 'percent', 'timestamp': timestamp, 'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })
            rem_minutes = self._to_float(data_point.get('rem_sleep_minutes'))
            if total_sleep and rem_minutes is not None and total_sleep > 0:
                metrics.append({
                    'user_id': user_id, 'metric_type': 'rem_sleep_percentage',
                    'value': float((rem_minutes / total_sleep) * 100.0),
                    'unit': 'percent', 'timestamp': timestamp, 'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })

            # Enhanced sleep stage analysis - store detailed timing if available
            self._process_sleep_stages_detailed(user_id, data_point, timestamp, metrics)

            # Process sleep timing metrics
            bedtime = self._parse_timestamp(data_point.get('bedtime'))
            if bedtime:
                # Store bedtime as a separate metric for timing analysis
                metrics.append({
                    'user_id': user_id, 'metric_type': 'bedtime', 'value': bedtime.hour + bedtime.minute/60.0,
                    'unit': 'hour_of_day', 'timestamp': bedtime, 'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point, 'bedtime_full': bedtime.isoformat()}
                })

            # Wake up time estimation (bedtime + total sleep time)
            if total_sleep and bedtime:
                try:
                    wake_time = bedtime + timedelta(minutes=total_sleep)
                    metrics.append({
                        'user_id': user_id, 'metric_type': 'wake_time', 'value': wake_time.hour + wake_time.minute/60.0,
                        'unit': 'hour_of_day', 'timestamp': bedtime, 'source': 'ultrahuman',
                        'meta_data': {'raw_data': data_point, 'wake_time_full': wake_time.isoformat()}
                    })
                except Exception:
                    pass  # Skip if calculation fails

            return metrics
        except Exception as e:
            logger.warning(f"Sleep data processing failed: {str(e)}")
            return []

    def _process_activity_data(self, user_id: str, data_point: Dict) -> List[Dict]:
        try:
            metrics = []
            timestamp = self._parse_timestamp(data_point.get('date'))
            v = self._to_float(data_point.get('steps'))
            if v is not None:
                metrics.append({'user_id': user_id, 'metric_type': 'steps', 'value': v,
                                'unit': 'count', 'timestamp': timestamp, 'source': 'ultrahuman',
                                'meta_data': {'raw_data': data_point}})
            v = self._to_float(data_point.get('calories_burned'))
            if v is not None:
                metrics.append({'user_id': user_id, 'metric_type': 'calories_burned', 'value': v,
                                'unit': 'calories', 'timestamp': timestamp, 'source': 'ultrahuman',
                                'meta_data': {'raw_data': data_point}})
            v = self._to_float(data_point.get('active_minutes'))
            if v is not None:
                metrics.append({'user_id': user_id, 'metric_type': 'active_minutes', 'value': v,
                                'unit': 'minutes', 'timestamp': timestamp, 'source': 'ultrahuman',
                                'meta_data': {'raw_data': data_point}})
            return metrics
        except Exception as e:
            logger.warning(f"Activity data processing failed: {str(e)}")
            return []

    def _process_recovery_data(self, user_id: str, data_point: Dict) -> List[Dict]:
        try:
            metrics = []
            timestamp = self._parse_timestamp(data_point.get('date'))

            def add(mt, val, unit):
                v = self._to_float(val)
                if v is not None:
                    metrics.append({
                        'user_id': user_id, 'metric_type': mt, 'value': v,
                        'unit': unit, 'timestamp': timestamp, 'source': 'ultrahuman',
                        'meta_data': {'raw_data': data_point}
                    })

            add('recovery', data_point.get('recovery_score'), 'score')
            add('heart_rate', data_point.get('resting_heart_rate'), 'bpm')
            add('temperature', data_point.get('skin_temperature'), 'celsius')

            add('average_glucose', data_point.get('average_glucose'), 'mg/dL')
            add('glucose_variability', data_point.get('glucose_variability'), 'percent')
            add('metabolic_score', data_point.get('metabolic_score'), 'score')
            add('hba1c', data_point.get('hba1c'), 'percent')
            add('time_in_target', data_point.get('time_in_target'), 'percent')
            add('movement_index', data_point.get('movement_index'), 'index')
            add('vo2_max', data_point.get('vo2_max'), 'ml/kg/min')

            return metrics
        except Exception as e:
            logger.warning(f"Recovery data processing failed: {str(e)}")
            return []

    def _process_series_data(self, user_id: str, data_point: Dict) -> List[Dict]:
        try:
            mt = data_point.get("metric_type")
            ts = self._parse_timestamp(data_point.get("timestamp"))
            val = self._to_float(data_point.get("value"))
            unit = data_point.get("unit") or ("bpm" if mt == "heart_rate_minute" else None)
            if mt and val is not None and ts:
                return [{
                    "user_id": user_id, "metric_type": mt, "value": val,
                    "unit": unit, "timestamp": ts, "source": "ultrahuman",
                    "meta_data": {"raw_data": data_point}
                }]
            return []
        except Exception as e:
            logger.warning(f"Series data processing failed: {str(e)}")
            return []

    # ---------------------- lifestyle & SMS parsing ----------------------

    def log_lifestyle_event(self, user_id: str, event_type: str, details: Dict, timestamp: Optional[datetime] = None) -> Dict:
        try:
            if event_type not in self.lifestyle_event_types:
                return {"error": f"Invalid event type: {event_type}"}
            if timestamp is None:
                timestamp = datetime.utcnow()

            metrics = self._process_lifestyle_event_record(user_id, event_type, details, timestamp)
            if metrics:
                if bulk_insert_metrics(metrics):
                    self._update_metrics_cache(user_id, metrics)
                    return {"success": True, "event_type": event_type, "metrics_created": len(metrics), "timestamp": timestamp.isoformat()}
                return {"error": "Failed to store lifestyle event"}
            return {"error": "Failed to process lifestyle event"}
        except Exception as e:
            logger.error(f"Lifestyle event logging failed: {str(e)}")
            return {"error": str(e)}

    def _process_lifestyle_event_record(self, user_id: str, event_type: str, details: Dict, timestamp: datetime) -> List[Dict]:
        try:
            metrics: List[Dict] = []
            if event_type == "meal":
                # Generic meal timing
                metrics.append({
                    "user_id": user_id, "metric_type": "meal_timing",
                    "value": timestamp.hour + timestamp.minute/60.0, "unit": "hour_of_day",
                    "timestamp": timestamp, "source": "user_input",
                    "meta_data": {"event_type": "meal", "details": details, "parsed_from_sms": details.get("parsed_from_sms", False)}
                })

                # Food-specific tracking
                food_name = details.get("food", "unknown").lower()
                if food_name and food_name != "unknown":
                    food_metric_type = f"{food_name.replace(' ', '_')}_consumption"

                    metrics.append({
                        "user_id": user_id,
                        "metric_type": food_metric_type,
                        "value": 1.0,  # Boolean: consumed
                        "unit": "boolean",
                        "timestamp": timestamp,
                        "source": "user_input",
                        "meta_data": {
                            "event_type": "meal",
                            "food_name": food_name,
                            "details": details,
                            "parsed_from_sms": True
                        }
                    })

                if "estimated_calories" in details:
                    metrics.append({
                        "user_id": user_id, "metric_type": "calorie_intake", "value": float(details["estimated_calories"]),
                        "unit": "calories", "timestamp": timestamp, "source": "user_input",
                        "meta_data": {"event_type": "meal", "details": details}
                    })
            elif event_type == "supplement":
                supplement_name = details.get("name", "unknown").lower()
                dosage_value = self._extract_numeric_dosage(details.get("dosage", "1"))
                dosage_unit = self._extract_dosage_unit(details.get("dosage", ""))

                # Create supplement-specific metric for better querying
                supplement_metric_type = f"{supplement_name}_intake"

                metrics.append({
                    "user_id": user_id,
                    "metric_type": supplement_metric_type,
                    "value": float(dosage_value),
                    "unit": dosage_unit or "dose",
                    "timestamp": timestamp,
                    "source": "user_input",
                    "meta_data": {
                        "event_type": "supplement",
                        "details": details,
                        "supplement_name": supplement_name,
                        "dosage_raw": details.get("dosage", "unknown"),
                        "parsed_from_sms": True
                    }
                })

                # Also create a generic supplement_intake metric for overall tracking
                metrics.append({
                    "user_id": user_id,
                    "metric_type": "supplement_intake",
                    "value": 1.0,
                    "unit": "boolean",
                    "timestamp": timestamp,
                    "source": "user_input",
                    "meta_data": {
                        "event_type": "supplement",
                        "supplement_name": supplement_name,
                        "dosage": details.get("dosage", "unknown")
                    }
                })
            elif event_type == "activity":
                activity_type = details.get("type", "unknown").lower()

                # Activity-specific tracking
                if activity_type and activity_type != "unknown":
                    activity_metric_type = f"{activity_type.replace(' ', '_')}_duration"

                    duration_value = details.get("duration_minutes", 30)  # Default 30 min
                    metrics.append({
                        "user_id": user_id,
                        "metric_type": activity_metric_type,
                        "value": float(duration_value),
                        "unit": "minutes",
                        "timestamp": timestamp,
                        "source": "user_input",
                        "meta_data": {
                            "event_type": "activity",
                            "activity_type": activity_type,
                            "details": details,
                            "parsed_from_sms": True
                        }
                    })

                # Generic exercise duration
                if "duration_minutes" in details:
                    metrics.append({
                        "user_id": user_id, "metric_type": "exercise_duration", "value": float(details["duration_minutes"]),
                        "unit": "minutes", "timestamp": timestamp, "source": "user_input",
                        "meta_data": {"event_type": "activity", "details": details}
                    })

                intensity_map = {"low": 1, "light": 2, "moderate": 3, "high": 4, "vigorous": 5}
                intensity = details.get("intensity", "moderate")
                if intensity in intensity_map:
                    metrics.append({
                        "user_id": user_id, "metric_type": "exercise_intensity", "value": float(intensity_map[intensity]),
                        "unit": "scale_1_5", "timestamp": timestamp, "source": "user_input",
                        "meta_data": {"event_type": "activity", "details": details}
                    })
            elif event_type == "stress":
                stress_map = {"low": 1, "medium": 3, "high": 5}
                level = details.get("level", "medium")
                if level in stress_map:
                    metrics.append({
                        "user_id": user_id, "metric_type": "stress_level", "value": float(stress_map[level]),
                        "unit": "scale_1_5", "timestamp": timestamp, "source": "user_input",
                        "meta_data": {"event_type": "stress", "details": details}
                    })
            elif event_type == "sleep_quality":
                score = details.get("score", 5)
                metrics.append({
                    "user_id": user_id, "metric_type": "sleep_quality_subjective", "value": float(score),
                    "unit": "scale_1_10", "timestamp": timestamp, "source": "user_input",
                    "meta_data": {"event_type": "sleep_quality", "details": details}
                })
            elif event_type == "drink":
                drink_type = details.get("drink_type", "unknown").lower()

                # Drink-specific tracking
                if drink_type and drink_type != "unknown":
                    drink_metric_type = f"{drink_type}_consumption"

                    # Extract amount if provided
                    amount_str = details.get("amount", "1")
                    amount_value = self._extract_numeric_dosage(amount_str)
                    amount_unit = self._extract_volume_unit(amount_str)

                    metrics.append({
                        "user_id": user_id,
                        "metric_type": drink_metric_type,
                        "value": float(amount_value),
                        "unit": amount_unit or "servings",
                        "timestamp": timestamp,
                        "source": "user_input",
                        "meta_data": {
                            "event_type": "drink",
                            "drink_type": drink_type,
                            "details": details,
                            "parsed_from_sms": True
                        }
                    })

                    # If it's caffeine, also create caffeine_intake metric
                    if drink_type in ['coffee', 'tea', 'espresso']:
                        caffeine_amount = self._estimate_caffeine_content(drink_type, amount_value)
                        metrics.append({
                            "user_id": user_id,
                            "metric_type": "caffeine_intake",
                            "value": float(caffeine_amount),
                            "unit": "mg",
                            "timestamp": timestamp,
                            "source": "user_input",
                            "meta_data": {
                                "event_type": "drink",
                                "drink_type": drink_type,
                                "caffeine_source": drink_type,
                                "details": details,
                                "parsed_from_sms": True
                            }
                        })
            return metrics
        except Exception as e:
            logger.error(f"Lifestyle event processing failed: {str(e)}")
            return []

    # ------------------------------ misc ------------------------------

    def _infer_meal_type(self, hour: int) -> str:
        if 5 <= hour <= 10: return "breakfast"
        if 11 <= hour <= 14: return "lunch"
        if 15 <= hour <= 17: return "snack"
        if 18 <= hour <= 22: return "dinner"
        return "late_snack"

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        try:
            if not timestamp_str:
                return datetime.utcnow()
            fmts = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]
            for fmt in fmts:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return datetime.utcnow()
        except Exception as e:
            logger.warning(f"Timestamp parsing failed: {str(e)}")
            return datetime.utcnow()

    def _update_metrics_cache(self, user_id: str, metrics: List[Dict]):
        try:
            by_type: Dict[str, List[Dict]] = {}
            for m in metrics:
                by_type.setdefault(m["metric_type"], []).append(m)
            for mt, lst in by_type.items():
                MetricsCache.cache_recent_metrics(user_id, {mt: lst})
        except Exception as e:
            logger.warning(f"Cache update failed: {str(e)}")

    @cache_user_data(expire_seconds=3600)
    def get_recent_metrics(self, user_id: str, hours: int = 24, metric_types: Optional[List[str]] = None) -> Dict:
        try:
            availability = self.get_available_metrics_for_user(user_id, days_back=hours//24 + 1)
            if 'error' in availability:
                return availability

            available_metric_types = list(availability['available_metrics'].keys())
            if not available_metric_types:
                return {
                    'error': 'No metric data found for this user',
                    'suggestion': 'Check if the Ultrahuman device is connected and syncing data',
                    'user_id': user_id,
                    'hours_requested': hours
                }

            if metric_types:
                missing_metrics = [mt for mt in metric_types if mt not in available_metric_types]
                if missing_metrics:
                    return {
                        'error': f'Requested metrics not available: {missing_metrics}',
                        'available_metrics': available_metric_types,
                        'suggestion': f'Try requesting analysis with available metrics: {available_metric_types}',
                        'user_id': user_id
                    }

            actual_metric_types = metric_types or available_metric_types

            start_time = datetime.utcnow() - timedelta(hours=hours)
            q = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.timestamp >= start_time,
                Metric.metric_type.in_(actual_metric_types)
            )
            rows = q.order_by(Metric.timestamp.desc()).all()

            if not rows:
                return {
                    'error': f'No data found in the last {hours} hours',
                    'available_metrics': available_metric_types,
                    'suggestion': f'Try a longer time period or check data for available metrics',
                    'data_availability': availability['available_metrics']
                }

            data: Dict[str, List[Dict]] = {}
            for r in rows:
                data.setdefault(r.metric_type, []).append({
                    "timestamp": r.timestamp.isoformat(),
                    "value": r.value,
                    "unit": r.unit,
                    "z_score": r.z_score,
                    "anomaly_score": r.anomaly_score,
                    "meta_data": r.meta_data
                })

            response = {
                'data': data,
                'metadata': {
                    'hours_requested': hours,
                    'metrics_found': list(data.keys()),
                    'data_points_total': len(rows),
                    'availability_info': availability['available_metrics']
                }
            }
            if metric_types and set(metric_types) != set(data.keys()):
                response['warning'] = f"Some requested metrics unavailable. Found: {list(data.keys())}"
            return response

        except Exception as e:
            logger.error(f"Failed to get recent metrics for user {user_id}: {str(e)}")
            return {'error': str(e), 'user_id': user_id}

    def process_webhook_data(self, webhook_data: Dict) -> Dict:
        try:
            user_id = webhook_data.get("user_id")
            if not user_id:
                return {"error": "Missing user_id in webhook data"}
            processed = self.process_ultrahuman_data(user_id, webhook_data)
            if processed.get("success"):
                recent = self.get_recent_metrics(user_id, hours=1)
                return {"success": True, "user_id": user_id,
                        "metrics_processed": processed.get("metrics_inserted", 0), "recent_data": recent}
            return {"error": "Failed to process webhook data", "details": processed}
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return {"error": str(e)}

    def get_metric_statistics(self, user_id: str, metric_type: str, days: int = 30) -> Dict:
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            rows = (Metric.query.filter(Metric.user_id == user_id, Metric.metric_type == metric_type,
                                        Metric.timestamp >= start_time).order_by(Metric.timestamp).all())
            if not rows:
                return {"error": "No data found for metric type"}
            values = np.array([r.value for r in rows])
            timestamps = [r.timestamp for r in rows]
            stats = {
                "metric_type": metric_type,
                "sample_size": len(values),
                "date_range": {
                    "start": timestamps[0].isoformat(),
                    "end": timestamps[-1].isoformat(),
                    "duration_days": (timestamps[-1] - timestamps[0]).days,
                },
                "descriptive_stats": {
                    "mean": float(np.mean(values)), "median": float(np.median(values)),
                    "std": float(np.std(values, ddof=1)), "min": float(np.min(values)), "max": float(np.max(values)),
                    "q1": float(np.percentile(values, 25)), "q3": float(np.percentile(values, 75)),
                    "iqr": float(np.percentile(values, 75) - np.percentile(values, 25)),
                },
                "robust_stats": {
                    "mad": RobustStatistics.median_absolute_deviation(values),
                    "iqr_stats": RobustStatistics.interquartile_range(values),
                    "winsorized_mean": RobustStatistics.winsorized_mean(values),
                },
                "data_quality": {
                    "missing_values": 0,
                    "potential_outliers": len(RobustStatistics.interquartile_range(values)["outliers"]),
                    "consistency_score": self._calculate_consistency_score(timestamps),
                },
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get metric statistics: {str(e)}")
            return {"error": str(e)}

    def _calculate_consistency_score(self, timestamps: List[datetime]) -> float:
        try:
            if len(timestamps) < 2:
                return 1.0
            diffs = [(timestamps[i] - timestamps[i-1]).total_seconds() / 3600 for i in range(1, len(timestamps))]
            mean_diff = float(np.mean(diffs))
            std_diff = float(np.std(diffs))
            if mean_diff == 0:
                return 1.0
            cv = std_diff / mean_diff
            return max(0.0, 1.0 - cv)
        except Exception as e:
            logger.warning(f"Consistency score calculation failed: {str(e)}")
            return 0.5

    def validate_metric_data(self, metric_data: Dict) -> Dict:
        try:
            out = {"is_valid": True, "errors": [], "warnings": []}
            for field in ["user_id", "metric_type", "value", "timestamp"]:
                if field not in metric_data:
                    out["errors"].append(f"Missing required field: {field}")
                    out["is_valid"] = False
            if "value" in metric_data:
                try:
                    val = float(metric_data["value"])
                    if np.isnan(val) or np.isinf(val):
                        out["errors"].append("Invalid value: NaN or Inf")
                        out["is_valid"] = False
                except (ValueError, TypeError):
                    out["errors"].append("Value must be numeric")
                    out["is_valid"] = False
            if "timestamp" in metric_data:
                try:
                    ts = metric_data["timestamp"]
                    if isinstance(ts, str):
                        self._parse_timestamp(ts)
                    elif not isinstance(ts, datetime):
                        out["errors"].append("Invalid timestamp format")
                        out["is_valid"] = False
                except Exception:
                    out["errors"].append("Could not parse timestamp")
                    out["is_valid"] = False
            if "metric_type" in metric_data:
                mt = metric_data["metric_type"]
                if not isinstance(mt, str) or not mt.strip():
                    out["errors"].append("Invalid metric type")
                    out["is_valid"] = False
            return out
        except Exception as e:
            logger.error(f"Metric validation failed: {str(e)}")
            return {"is_valid": False, "errors": [f"Validation error: {str(e)}"], "warnings": []}

    # ==================== CONVERSATION MEMORY METHODS ====================

    def process_sms_input_with_context(self, user_id: str, text: str) -> Dict:
        """Process SMS input with conversation context and follow-up detection"""
        try:
            # Get recent conversation history
            recent_conversations = self._get_recent_conversations(user_id, limit=5)

            # Check if this is a follow-up query
            if recent_conversations and self._is_follow_up_query(text, recent_conversations):
                logger.info(f"Follow-up detected for user {user_id}: {text}")
                return self._handle_follow_up_query(user_id, text, recent_conversations)

            # Process as new query
            result = self.process_sms_input(user_id, text)

            # Store the conversation for future context
            self._store_conversation(user_id, text, result)

            return result

        except Exception as e:
            logger.error(f"Context processing failed: {str(e)}")
            # Fallback to regular processing
            return self.process_sms_input(user_id, text)

    def _get_recent_conversations(self, user_id: str, limit: int = 5) -> List[Conversation]:
        """Get recent conversations for context"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=2)  # 2-hour conversation window

            conversations = db.session.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= cutoff_time
            ).order_by(Conversation.created_at.desc()).limit(limit).all()

            return conversations

        except Exception as e:
            logger.warning(f"Failed to get conversation history: {str(e)}")
            return []

    def _is_follow_up_query(self, text: str, recent_conversations: List[Conversation]) -> bool:
        """Detect if current query is a follow-up to previous conversation"""
        if not recent_conversations:
            return False

        text_lower = text.lower().strip()

        # Check for follow-up patterns
        for pattern in FOLLOW_UP_PATTERNS:
            if pattern.search(text_lower):
                return True

        # Check for context-aware starters without main metric/analysis words
        if any(starter in text_lower for starter in CONTEXT_QUESTIONS):
            # If it starts with context words but doesn't have clear new intent
            has_new_intent = any(pattern.search(text_lower) for pattern in INTENT_PATTERNS.values())
            if not has_new_intent:
                return True

        # Check for pronoun references
        pronouns = ["it", "that", "this", "them", "those"]
        if any(pronoun in text_lower.split()[:3] for pronoun in pronouns):
            return True

        return False

    def _handle_follow_up_query(self, user_id: str, text: str, conversations: List[Conversation]) -> Dict:
        """Handle follow-up queries using conversation context"""
        try:
            # Get the most recent conversation for context
            last_conversation = conversations[0] if conversations else None

            if not last_conversation:
                # Fallback to regular processing
                return self.process_sms_input(user_id, text)

            # Build contextual prompt for LLM
            context = self._build_conversation_context(text, conversations)

            # Generate contextual response using LLM
            from services.llm_service import SMSLLMService
            llm_service = SMSLLMService()

            enhanced_response = llm_service.generate_contextual_response(context)

            # Store the follow-up conversation
            follow_up_result = {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "follow_up_response",
                        "message": enhanced_response.content,
                        "context_used": True,
                        "parent_conversation_id": last_conversation.id
                    }]
                }
            }

            # Store this follow-up
            self._store_conversation(
                user_id, text, follow_up_result,
                is_follow_up=True, parent_id=last_conversation.id
            )

            return follow_up_result

        except Exception as e:
            logger.warning(f"Follow-up handling failed: {str(e)}")
            # Fallback to regular processing
            result = self.process_sms_input(user_id, text)
            self._store_conversation(user_id, text, result)
            return result

    def _build_conversation_context(self, current_query: str, conversations: List[Conversation]) -> str:
        """Build context string from conversation history"""
        context_parts = ["Previous conversation context:"]

        # Add recent conversations (in chronological order)
        for conv in reversed(conversations[-3:]):  # Last 3 conversations
            context_parts.append(f"User: {conv.query}")
            context_parts.append(f"Assistant: {conv.response}")

            # Add analysis context if available
            if conv.analysis_data:
                metrics = conv.analysis_data.get('metrics_discussed', [])
                if metrics:
                    context_parts.append(f"Metrics discussed: {', '.join(metrics)}")

        context_parts.append(f"\nCurrent follow-up question: {current_query}")
        context_parts.append("\nPlease provide a contextual response that continues the conversation naturally.")

        return "\n".join(context_parts)

    def _store_conversation(self, user_id: str, query: str, result: Dict,
                          is_follow_up: bool = False, parent_id: Optional[int] = None):
        """Store conversation for future context"""
        try:
            # Generate or reuse session ID
            session_id = self._get_or_create_session_id(user_id)

            # Extract response message
            response_message = ""
            metrics_involved = []
            analysis_data = {}
            query_type = "unknown"

            if result.get("success") and "immediate_insights" in result:
                insights = result["immediate_insights"].get("insights", [])
                if insights:
                    response_message = insights[0].get("message", "")
                    query_type = insights[0].get("type", "unknown")

            # Extract metrics and analysis data if available
            if "analysis_data" in result:
                analysis_data = result["analysis_data"]
                metrics_involved = analysis_data.get("metrics_discussed", [])

            # Create conversation record
            conversation = Conversation(
                user_id=user_id,
                session_id=session_id,
                query=query,
                response=response_message,
                query_type=query_type,
                analysis_data=analysis_data,
                metrics_involved=metrics_involved,
                is_follow_up=is_follow_up,
                parent_conversation_id=parent_id,
                session_expires_at=datetime.utcnow() + timedelta(hours=2)
            )

            db.session.add(conversation)
            db.session.commit()

        except Exception as e:
            logger.warning(f"Failed to store conversation: {str(e)}")
            db.session.rollback()

    def _get_or_create_session_id(self, user_id: str) -> str:
        """Get existing session ID or create new one"""
        try:
            # Check if user has active session (within 30 minutes)
            recent_cutoff = datetime.utcnow() - timedelta(minutes=30)

            recent_conversation = db.session.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= recent_cutoff
            ).order_by(Conversation.created_at.desc()).first()

            if recent_conversation:
                return recent_conversation.session_id
            else:
                # Create new session ID
                return f"session_{user_id}_{uuid.uuid4().hex[:8]}"

        except Exception as e:
            logger.warning(f"Session ID generation failed: {str(e)}")
            return f"session_{user_id}_{uuid.uuid4().hex[:8]}"

    # ==================== NEW: Intent router & handlers ====================

    def process_sms_input(self, user_id: str, message: str) -> Dict:
        """
        Process SMS input and return appropriate response.
        Always routes through intent → structured analysis → LLM summary.
        """
        try:
            text = (message or "").strip()
            if not text:
                return {"success": False, "error": "Empty message"}

            # NEW: Check for conversational messages FIRST
            is_conversational, response = self._is_conversational_message(text)
            if is_conversational:
                return {
                    "success": True,
                    "conversational_response": True,
                    "immediate_insights": {
                        "insights": [{
                            "type": "conversational",
                            "message": response
                        }]
                    }
                }

            msg_lc = text.lower()

            # 1) Lifestyle quick-parse (enhanced to handle multiple events)
            if self._is_lifestyle_event(msg_lc):
                try:
                    # Parse all lifestyle events from the message (handles multi-line)
                    events = self._parse_all_lifestyle_events(text)

                    if events:
                        return self._process_multiple_lifestyle_events(user_id, events)
                    else:
                        return {
                            "success": False,
                            "error": "No valid lifestyle events found",
                            "immediate_insights": {
                                "insights": [{
                                    "type": "lifestyle_error",
                                    "message": "❌ Could not parse lifestyle event. Try: 'meal chicken 7pm' or 'supplement magnesium 400mg'"
                                }]
                            }
                        }

                except Exception as e:
                    logger.error(f"Lifestyle event parsing failed: {str(e)}")
                    return {
                        "success": False,
                        "error": str(e),
                        "immediate_insights": {
                            "insights": [{
                                "type": "lifestyle_error",
                                "message": "❌ Could not parse lifestyle event. Try: 'meal chicken 7pm' or 'supplement magnesium 400mg'"
                            }]
                        }
                    }

            # 2) Check for general health questions (non-data queries)
            if self._is_general_health_question(text):
                logger.info(f"🩺 Detected general health question: {text[:50]}...")
                return self._handle_general_health_question(user_id, text)

            # 3) NEW: Enhanced NLP Processing using your proven date parsing
            parsed_query = self.nlp_parser.parse_query(text)

            # If we have good confidence in NLP parsing, use structured processing
            if parsed_query.confidence > 0.4:  # Higher threshold for confidence
                logger.info(f"NLP parsed: {parsed_query.metric_type} {parsed_query.aggregation} {parsed_query.time_period} (confidence: {parsed_query.confidence:.2f})")
                return self._handle_nlp_parsed_query(user_id, parsed_query)

            # 3) Fallback to legacy intent detection for special cases
            intent = None
            for key, pat in INTENT_PATTERNS.items():
                if pat.search(msg_lc):
                    intent = key
                    break

            # 4) Correlation
            if intent == "correlation" or self._is_correlation_query(msg_lc):
                return self._handle_correlation(user_id, msg_lc)

            # 5) Trend
            if intent == "trend":
                return self._handle_trend(user_id, msg_lc)

            # 6) Pattern
            if intent == "pattern":
                return self._handle_pattern(user_id, msg_lc)

            # 7) Anomaly
            if intent == "anomaly":
                return self._handle_anomaly(user_id, msg_lc)

            # 8) Intervention
            if intent == "intervention":
                return self._handle_intervention(user_id, msg_lc)

            # 9) Check for structured health queries (legacy fallback)
            if self._is_structured_health_query(msg_lc):
                return self._handle_structured_query(user_id, text)

            # 9) Fallback generic with LLM enhancement
            base_message = "I can help with lifestyle tracking and health correlations. Try asking about correlations between your metrics or log events like 'meal chicken 7pm'."
            enhanced_message = self._enhance_message_with_llm(base_message, user_id, "general")

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "general",
                        "message": enhanced_message
                    }]
                }
            }

        except Exception as e:
            logger.error(f"Error processing SMS input: {str(e)}")
            return {"success": False, "error": str(e)}

    def _is_structured_health_query(self, message: str) -> bool:
        """Detect queries that can benefit from function calling (specific metric queries)"""
        structured_patterns = [
            # Statistical queries - COMPREHENSIVE PATTERNS
            r'\b(average|mean|median|min|minimum|max|maximum|highest|lowest|latest)\s+.*\s+(last\s+)?\d+\s+(days?|weeks?|months?)',
            r'\b(average|mean|median|min|minimum|max|maximum|highest|lowest|latest)\s+.*\s+(this\s+)?(week|month|today|yesterday)',
            r'\b(what was|what is|what\'s|show me|tell me)\s+(my\s+)?(average|avg|min|max|highest|lowest|latest)\s+\w+',
            r'\bmy\s+(average|avg|min|max|highest|lowest|latest)\s+\w+',
            r'\bmy\s+\w+\s+(last\s+week|yesterday|this\s+month|over\s+the\s+last|over\s+past)',
            r'\bhow\s+(high|low|good|bad)\s+was\s+my\s+\w+',
            r'\bwhat\'s\s+my\s+(avg|average)\s+\w+\s+(over\s+)?(past|last)\s+\w+',

            # Sleep queries
            r'\bwhen\s+do\s+i\s+(usually\s+)?(enter|go\s+into|start)\s+\w+\s+sleep',
            r'\bhow\s+long\s+do\s+i\s+(usually\s+)?spend\s+in\s+\w+\s+sleep',
            r'\b(deep|light|rem)\s+sleep\s+(analysis|patterns?|breakdown)',

            # Correlation queries
            r'\b(correlation|relationship)\s+between\s+.+\s+and\s+.+',
            r'\b.+\s+(vs|versus)\s+.+\s+(correlation|relationship)',
            r'\bhow\s+(are\s+)?.+\s+and\s+.+\s+(related|correlated)',
            r'\b.+\s+and\s+.+\s+(correlation|relationship)',

            # Comprehensive queries
            r'\b(summary|analysis|report|overview|metrics)\s+(from\s+)?(last\s+)?\d+\s+(days?|weeks?|months?)',
            r'\b(health|metrics?)\s+(from\s+)?(yesterday|today|last\s+week|this\s+week)',
            r'\bcomprehensive\s+(health|analysis|report)'
        ]

        return any(re.search(pattern, message, re.I) for pattern in structured_patterns)

    def _handle_nlp_parsed_query(self, user_id: str, parsed_query: ParsedQuery) -> Dict:
        """Handle queries parsed by the enhanced NLP parser using your proven date parsing"""
        try:
            # Route based on query type
            if parsed_query.query_type == 'correlation':
                return self._handle_correlation_nlp(user_id, parsed_query)
            elif parsed_query.query_type == 'trend':
                return self._handle_trend_nlp(user_id, parsed_query)
            elif parsed_query.query_type == 'comparison':
                return self._handle_comparison_nlp(user_id, parsed_query)
            else:
                # Standard metric query - use LLM service with structured query
                return self._handle_metric_query_nlp(user_id, parsed_query)

        except Exception as e:
            logger.error(f"Error handling NLP parsed query: {str(e)}")
            base_message = f"I understand you're asking about {parsed_query.metric_type.replace('_', ' ')} over {parsed_query.time_period}, but encountered an issue processing that request. Try a simpler query like 'average heart rate last week'."
            enhanced_message = self._enhance_message_with_llm(base_message, user_id, "error", parsed_query)

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_error",
                        "message": enhanced_message
                    }]
                }
            }

    def _handle_metric_query_nlp(self, user_id: str, parsed_query: ParsedQuery) -> Dict:
        """Handle standard metric queries using NLP parsing with LLM service"""
        try:
            # QUICK_SMS_FIX_APPLIED - Always try local processing first for reliable responses
            logger.info(f"🎯 Attempting local processing first for: {parsed_query.metric_type} {parsed_query.aggregation}")

            # Try local processing first (more reliable than OpenAI on PythonAnywhere)
            local_result = self._handle_metric_query_local_nlp(user_id, parsed_query)

            if local_result and local_result.get('success'):
                insights = local_result.get('immediate_insights', {}).get('insights', [])
                if insights and 'no data' not in insights[0].get('message', '').lower():
                    logger.info(f"✅ Local processing succeeded for {parsed_query.metric_type}")
                    return local_result

            # Only try LLM if local processing failed
            from services.llm_service import SMSLLMService

            # Create a structured query string for the LLM service
            structured_query = f"{parsed_query.aggregation} {parsed_query.metric_type.replace('_', ' ')} last {parsed_query.time_period_days} days"

            llm_service = SMSLLMService()
            response = llm_service.handle_structured_health_query(structured_query, user_id)

            # Enhance the response with NLP context
            enhanced_message = response.content

            # Add context from NLP parsing
            if parsed_query.extracted_entities.get('context') == 'exercise':
                enhanced_message += " 💪 (Exercise context detected)"
            elif parsed_query.extracted_entities.get('context') == 'sleep':
                enhanced_message += " 😴 (Sleep context detected)"

            if parsed_query.extracted_entities.get('urgency') == 'high':
                enhanced_message = f"⚠️ {enhanced_message}"

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_structured_query",
                        "message": enhanced_message,
                        "provider": response.provider.value,
                        "tokens_used": response.tokens_used,
                        "confidence": parsed_query.confidence,
                        "nlp_parsing": {
                            "original_query": parsed_query.raw_query,
                            "parsed_metric": parsed_query.metric_type,
                            "parsed_aggregation": parsed_query.aggregation,
                            "parsed_timeframe": parsed_query.time_period,
                            "start_date": parsed_query.start_date.isoformat() if parsed_query.start_date else None,
                            "end_date": parsed_query.end_date.isoformat() if parsed_query.end_date else None
                        }
                    }]
                }
            }

        except Exception as e:
            logger.error(f"LLM service failed for NLP query: {str(e)}")
            # Fallback to local processing using your proven approach
            return self._handle_metric_query_local_nlp(user_id, parsed_query)

    def _handle_metric_query_local_nlp(self, user_id: str, parsed_query: ParsedQuery) -> Dict:
        """Local fallback processing for NLP parsed metric queries"""
        try:
            # Use the parsed dates directly from your proven date parsing logic
            start_date = parsed_query.start_date
            end_date = parsed_query.end_date

            # If we don't have parsed dates, calculate them
            if not start_date:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=parsed_query.time_period_days)
            elif not end_date:
                end_date = datetime.now()

            # Use existing aggregation method
            result = self.fetch_metrics_aggregate(
                user_id,
                parsed_query.metric_type,
                parsed_query.aggregation,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if result is not None:
                # Generate response based on aggregation type
                metric_display = parsed_query.metric_type.replace('_', ' ')
                time_display = parsed_query.time_period  # No more underscores to replace
                unit = self._get_metric_unit(parsed_query.metric_type)

                if parsed_query.aggregation == 'average':
                    base_message = f"Your average {metric_display} over the {time_display} is {result:.1f} {unit}. 📊"
                elif parsed_query.aggregation == 'max':
                    base_message = f"Your highest {metric_display} over the {time_display} was {result:.1f} {unit}. 🔥"
                elif parsed_query.aggregation == 'min':
                    base_message = f"Your lowest {metric_display} over the {time_display} was {result:.1f} {unit}. 😴"
                else:
                    base_message = f"Your {parsed_query.aggregation} {metric_display} over the {time_display} is {result:.1f} {unit}. 💡"

                # Try to enhance with LLM insights
                try:
                    from services.llm_service import SMSLLMService
                    llm_service = SMSLLMService()

                    # Create context for LLM
                    llm_context = f"Health metric results: {base_message} "
                    llm_context += f"The user asked about their {parsed_query.aggregation} {metric_display} over {parsed_query.time_period_days} days. "
                    llm_context += f"The value is {result:.1f} {unit}. "
                    llm_context += f"Provide personalized health insights about what this {parsed_query.aggregation} {metric_display} value means for their health and wellness. Include actionable advice if relevant."

                    # Get LLM enhanced message
                    llm_response = llm_service.generate_sms_response(llm_context, max_length=320)
                    if llm_response and hasattr(llm_response, 'content') and llm_response.content.strip():
                        message = f"{base_message}\n\n💡 {llm_response.content}"
                    else:
                        message = base_message

                except Exception as llm_error:
                    logger.warning(f"LLM insights failed for metric query: {str(llm_error)}")
                    message = base_message

                # Add encouraging context for heart rate (only if LLM insights failed)
                if parsed_query.metric_type == 'heart_rate' and message == base_message:
                    if parsed_query.aggregation == 'average' and 60 <= result <= 100:
                        message += " That's within a healthy range! 💓"
                    elif parsed_query.aggregation == 'min' and result < 60:
                        message += " Great resting heart rate! 🌟"

                return {
                    "success": True,
                    "events_processed": 0,
                    "immediate_insights": {
                        "insights": [{
                            "type": "nlp_local_processing",
                            "message": message,
                            "provider": "enhanced_nlp_local",
                            "confidence": parsed_query.confidence,
                            "value": result,
                            "unit": unit,
                            "parsed_dates": {
                                "start": start_date.isoformat(),
                                "end": end_date.isoformat()
                            }
                        }]
                    }
                }
            else:
                base_message = f"I don't have enough {parsed_query.metric_type.replace('_', ' ')} data for the {parsed_query.time_period} period. Try a different time frame or check your data sync. 📱"
                enhanced_message = self._enhance_message_with_llm(base_message, user_id, "no_data", parsed_query)

                return {
                    "success": True,
                    "events_processed": 0,
                    "immediate_insights": {
                        "insights": [{
                            "type": "nlp_no_data",
                            "message": enhanced_message
                        }]
                    }
                }

        except Exception as e:
            logger.error(f"Local NLP metric query processing failed: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to process {parsed_query.metric_type} query: {str(e)}"
            }

    def _handle_trend_nlp(self, user_id: str, parsed_query: ParsedQuery) -> Dict:
        """Handle trend queries with NLP parsing"""
        try:
            metric_name = parsed_query.metric_type.replace('_', ' ')
            time_period = parsed_query.time_period or "recent period"

            # Try to get some trend data (simplified for demo)
            try:
                recent_data = self.enhanced_aggregation_with_nlp(
                    user_id, parsed_query.metric_type, "average",
                    parsed_query.start_date, parsed_query.end_date
                )

                if recent_data:
                    base_message = f"Your {metric_name} trend over {time_period} shows patterns worth analyzing. "
                    base_message += f"Recent average is {recent_data:.1f}. Trends help identify health patterns over time."
                else:
                    base_message = f"Analyzing {metric_name} trends over {time_period}. "
                    base_message += "Trend analysis reveals important patterns in your health metrics over time."

            except Exception:
                base_message = f"Your {metric_name} trends over {time_period} provide valuable health insights. "
                base_message += "Tracking patterns over time helps optimize your health journey."

            enhanced_message = self._enhance_message_with_llm(base_message, user_id, "trend", parsed_query)

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_trend",
                        "message": enhanced_message
                    }]
                }
            }

        except Exception as e:
            logger.warning(f"Trend analysis failed: {str(e)}")
            base_message = f"Trend analysis for {parsed_query.metric_type.replace('_', ' ')} helps identify patterns and improvements over time."
            enhanced_message = self._enhance_message_with_llm(base_message, user_id, "trend", parsed_query)

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_trend",
                        "message": enhanced_message
                    }]
                }
            }

    def _handle_correlation_nlp(self, user_id: str, parsed_query: ParsedQuery) -> Dict:
        """Handle correlation queries with NLP parsing"""
        try:
            # Import with better error handling
            try:
                from analysis.correlation_analysis import CorrelationAnalyzer
            except ImportError as e:
                logger.error(f"Failed to import CorrelationAnalyzer: {str(e)}")
                return {
                    "success": True,
                    "events_processed": 0,
                    "immediate_insights": {
                        "insights": [{
                            "type": "nlp_correlation_error",
                            "message": f"Correlation analysis module not available. Please try a simpler query. 📊"
                        }]
                    }
                }

            # Check if we have a secondary metric
            if not parsed_query.secondary_metric:
                base_message = f"I need two metrics to analyze correlation. Try: 'correlation between heart rate and sleep score last week' 📊"
                enhanced_message = self._enhance_message_with_llm(base_message, user_id, "error", parsed_query)

                return {
                    "success": True,
                    "events_processed": 0,
                    "immediate_insights": {
                        "insights": [{
                            "type": "nlp_correlation_error",
                            "message": enhanced_message
                        }]
                    }
                }

            # Get date range
            if parsed_query.start_date and parsed_query.end_date:
                start_date = parsed_query.start_date
                end_date = parsed_query.end_date
            else:
                end_date = datetime.now()
                # Use a default period if no time period was specified
                time_period_days = parsed_query.time_period_days if parsed_query.time_period_days > 0 else 7
                start_date = end_date - timedelta(days=time_period_days)

            logger.info(f"🔗 Analyzing correlation between {parsed_query.metric_type} and {parsed_query.secondary_metric}")

            # Fetch data for both metrics
            data = {}
            for metric_type in [parsed_query.metric_type, parsed_query.secondary_metric]:
                # Use enhanced lookup for better metric fetching
                enhanced_result = self.enhanced_lookup.fetch_metrics_aggregate_enhanced(
                    user_id, metric_type, 'raw',
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d")
                )

                if enhanced_result and enhanced_result.get('success') and enhanced_result.get('data'):
                    raw_data = enhanced_result['data']
                    if raw_data:
                        # Convert to format expected by correlation analyzer
                        data[metric_type] = {
                            'values': [float(point['value']) for point in raw_data],
                            'timestamps': [datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')) for point in raw_data]
                        }

            if len(data) < 2:
                # Try direct database fetch as fallback
                for metric_type in [parsed_query.metric_type, parsed_query.secondary_metric]:
                    if metric_type not in data:
                        result = self._fetch_raw_metrics_data(user_id, metric_type, start_date, end_date)
                        if result:
                            data[metric_type] = result

            if len(data) < 2:
                return {
                    "success": True,
                    "events_processed": 0,
                    "immediate_insights": {
                        "insights": [{
                            "type": "nlp_correlation_no_data",
                            "message": f"I need data for both {parsed_query.metric_type.replace('_', ' ')} and {parsed_query.secondary_metric.replace('_', ' ')} to calculate correlation. Try a different time period or check if you have recent data for both metrics. 📊"
                        }]
                    }
                }

            # Try advanced correlation analysis first, fallback to simple
            try:
                analyzer = CorrelationAnalyzer()
                correlation_results = analyzer.analyze_correlations(
                    data,
                    methods=['pearson', 'spearman'],
                    include_lagged=False
                )

                if 'error' in correlation_results:
                    raise Exception(correlation_results['error'])

            except Exception as analysis_error:
                logger.warning(f"Advanced correlation analysis failed: {str(analysis_error)}, trying simple correlation")
                # Fallback to simple correlation
                correlation_results = self._simple_correlation_analysis(data, parsed_query.metric_type, parsed_query.secondary_metric)

            # Extract correlation results
            pair_key = f"{parsed_query.metric_type}_vs_{parsed_query.secondary_metric}"
            reverse_pair_key = f"{parsed_query.secondary_metric}_vs_{parsed_query.metric_type}"

            pair_results = correlation_results.get('pairwise_correlations', {}).get(pair_key)
            if not pair_results:
                pair_results = correlation_results.get('pairwise_correlations', {}).get(reverse_pair_key)

            if not pair_results or 'error' in pair_results:
                return {
                    "success": True,
                    "events_processed": 0,
                    "immediate_insights": {
                        "insights": [{
                            "type": "nlp_correlation_error",
                            "message": f"Couldn't calculate correlation between {parsed_query.metric_type.replace('_', ' ')} and {parsed_query.secondary_metric.replace('_', ' ')}. May need more data points. 📊"
                        }]
                    }
                }

            # Get main correlation result (Pearson by default)
            pearson_data = pair_results.get('pearson', {})
            correlation = pearson_data.get('correlation', 0)
            p_value = pearson_data.get('p_value', 1)
            significant = pearson_data.get('significant', False)
            sample_size = pair_results.get('sample_size', 0)

            # Format correlation strength
            abs_corr = abs(correlation)
            if abs_corr >= 0.7:
                strength = "strong"
                emoji = "💪"
            elif abs_corr >= 0.5:
                strength = "moderate"
                emoji = "📊"
            elif abs_corr >= 0.3:
                strength = "weak"
                emoji = "📈"
            else:
                strength = "very weak"
                emoji = "📉"

            # Determine direction
            if correlation > 0:
                direction = "positive"
                direction_desc = "increase together"
            else:
                direction = "negative"
                direction_desc = "move in opposite directions"

            # Create readable message
            metric1_display = parsed_query.metric_type.replace('_', ' ')
            metric2_display = parsed_query.secondary_metric.replace('_', ' ')
            time_display = parsed_query.time_period

            if significant:
                base_message = f"📊 Found a {strength} {direction} correlation (r={correlation:.2f}) between {metric1_display} and {metric2_display} over the {time_display}. "
                base_message += f"They tend to {direction_desc}. {emoji} "
                base_message += f"(Based on {sample_size} data points, p={p_value:.3f})"
            else:
                base_message = f"📊 No significant correlation found between {metric1_display} and {metric2_display} over the {time_display}. "
                base_message += f"Correlation coefficient: r={correlation:.2f} (not statistically significant, p={p_value:.3f}). "
                base_message += f"Based on {sample_size} data points."

            # Try to enhance with LLM insights
            try:
                from services.llm_service import SMSLLMService
                llm_service = SMSLLMService()

                # Create context for LLM
                llm_context = f"Correlation analysis results: {base_message}. "
                llm_context += f"The user asked about correlation between {metric1_display} and {metric2_display}. "
                llm_context += f"Sample size: {sample_size} data points over {parsed_query.time_period_days} days. "

                if significant:
                    llm_context += f"The correlation is statistically significant (p={p_value:.3f}). "
                    if abs_corr < 0.3:
                        llm_context += f"This very weak correlation suggests minimal practical relationship. "
                    llm_context += f"Explain what this {strength} {direction} correlation between {metric1_display} and {metric2_display} means for health optimization. "
                    llm_context += f"Give actionable insights about how these metrics might influence each other."
                else:
                    llm_context += f"The correlation is not statistically significant (p={p_value:.3f}). "
                    llm_context += f"Explain why {metric1_display} and {metric2_display} might not be strongly related, and provide independent health tips for both metrics."

                # Get LLM enhanced message with more space for detailed insights
                llm_response = llm_service.generate_sms_response(llm_context, max_length=400)

                if llm_response and hasattr(llm_response, 'content') and llm_response.content.strip():
                    message = f"{base_message}\n\n💡 {llm_response.content}"
                else:
                    message = base_message

            except Exception as llm_error:
                logger.warning(f"LLM insights failed for correlation: {str(llm_error)}")
                message = base_message

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_correlation_analysis",
                        "message": message,
                        "correlation_data": {
                            "primary_metric": parsed_query.metric_type,
                            "secondary_metric": parsed_query.secondary_metric,
                            "correlation_coefficient": correlation,
                            "p_value": p_value,
                            "significant": significant,
                            "strength": strength,
                            "direction": direction,
                            "sample_size": sample_size,
                            "time_period": parsed_query.time_period_days
                        }
                    }]
                }
            }

        except Exception as e:
            import traceback
            logger.error(f"Error handling correlation query: {str(e)}")
            logger.error(f"Correlation error traceback: {traceback.format_exc()}")

            # More specific error message based on the error
            if "secondary_metric" in str(e) or not parsed_query.secondary_metric:
                error_message = f"I need two metrics to analyze correlation. Try: 'correlation between heart rate and sleep score last week' 📊"
            elif "data" in str(e).lower():
                error_message = f"Couldn't find enough data for both metrics. Try a different time period or check if you have recent data. 📊"
            else:
                error_message = f"Encountered an issue analyzing correlation. Try: 'average heart rate last week' or 'sleep score past 7 days' instead. 📊"

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_correlation_error",
                        "message": error_message
                    }]
                }
            }

    def _fetch_raw_metrics_data(self, user_id: str, metric_type: str, start_date: datetime, end_date: datetime) -> Optional[Dict]:
        """Fetch raw metrics data for correlation analysis"""
        try:
            # Query database for raw metrics data
            query = db.session.query(Metric).filter(
                Metric.user_id == user_id,
                Metric.metric_type == metric_type,
                Metric.timestamp >= start_date,
                Metric.timestamp <= end_date,
                Metric.value.isnot(None)
            ).order_by(Metric.timestamp.asc())

            results = query.all()

            if not results:
                return None

            return {
                'values': [float(result.value) for result in results],
                'timestamps': [result.timestamp for result in results]
            }

        except Exception as e:
            logger.error(f"Error fetching raw metrics data for {metric_type}: {str(e)}")
            return None

    def _enhance_message_with_llm(self, base_message: str, user_id: str, context_type: str = "general",
                                  parsed_query: Optional[ParsedQuery] = None) -> str:
        """Helper method to enhance any message with LLM insights"""
        # EMERGENCY FIX: Disable LLM enhancement to prevent fabricated data
        # The LLM was creating fake water intake and other tracking data
        # Return only the base message based on actual database data
        logger.info(f"LLM enhancement disabled to prevent fake data generation")
        return base_message

    def _handle_general_health_question(self, user_id: str, text: str) -> Dict:
        """Handle general health questions that don't require data analysis"""
        try:
            from services.llm_service import SMSLLMService
            llm_service = SMSLLMService()

            # Create simple context for health advice - no complex prompting
            health_context = f"User asked: {text}. Provide helpful health advice and tips."

            # Get LLM health advice
            llm_response = llm_service.generate_sms_response(health_context, max_length=320)

            if llm_response and hasattr(llm_response, 'content') and llm_response.content.strip():
                # Clean the response and format properly
                clean_content = llm_response.content.strip()
                # Remove any prompt leakage
                if clean_content.startswith("You are a helpful health coach"):
                    clean_content = "Here are some helpful tips for your health question! 💡"
                message = clean_content
            else:
                # Fallback for common questions
                message = self._get_fallback_health_advice(text)

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "general_health_advice",
                        "message": message,
                        "provider": "health_advisor"
                    }]
                }
            }

        except Exception as e:
            logger.warning(f"General health question handling failed: {str(e)}")
            # Fallback to basic health advice
            fallback_message = self._get_fallback_health_advice(text)
            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "general_health_advice",
                        "message": fallback_message,
                        "provider": "fallback_advisor"
                    }]
                }
            }

    def _get_fallback_health_advice(self, text: str) -> str:
        """Provide basic health advice fallbacks for common questions"""
        text_lower = text.lower()

        if "lower" in text_lower and "heart rate" in text_lower:
            return "💡 To lower your heart rate naturally: 1) Regular cardio exercise builds heart efficiency 2) Practice deep breathing or meditation 3) Reduce caffeine and stress 4) Get adequate sleep 5) Stay hydrated. If your resting HR is consistently >100 bpm, consult a doctor."

        elif "improve" in text_lower and "sleep" in text_lower:
            return "💡 For better sleep: 1) Keep a consistent sleep schedule 2) Create a cool, dark bedroom 3) Avoid screens 1-2 hours before bed 4) Limit caffeine after 2pm 5) Try relaxation techniques. Track your sleep patterns to identify what works best for you."

        elif "increase" in text_lower and ("hrv" in text_lower or "variability" in text_lower):
            return "💡 To improve HRV: 1) Regular moderate exercise (not overtraining) 2) Stress management techniques 3) Consistent sleep schedule 4) Avoid alcohol 5) Practice mindfulness. HRV typically improves gradually over weeks with consistent healthy habits."

        elif "reduce" in text_lower and "stress" in text_lower:
            return "💡 Stress reduction strategies: 1) Deep breathing exercises (4-7-8 technique) 2) Regular physical activity 3) Meditation or mindfulness 4) Time management and boundaries 5) Connect with supportive people. Your wearable data can help track stress patterns."

        elif "exercise" in text_lower and "heart" in text_lower:
            return "💡 Heart-healthy exercise: 1) Aim for 150 min moderate activity weekly 2) Include both cardio and strength training 3) Start gradually and build up 4) Monitor your heart rate zones 5) Recovery is important. Your heart rate data can guide exercise intensity."

        elif "good" in text_lower and "heart rate" in text_lower:
            return "💡 Resting heart rate ranges: Adults 60-100 bpm (lower often better). Athletes: 40-60 bpm. Factors affecting: fitness level, age, medications, stress, caffeine. Track trends over time rather than focusing on single readings."

        else:
            return "💡 I can help with health and wellness questions! For specific medical concerns, please consult with healthcare professionals. I can also analyze your health data - try asking about correlations, trends, or specific metrics like 'average heart rate last week'."

    def _simple_correlation_analysis(self, data: Dict, metric1: str, metric2: str) -> Dict:
        """Simple correlation analysis fallback using scipy"""
        try:
            from scipy.stats import pearsonr
            import numpy as np

            if metric1 not in data or metric2 not in data:
                return {'error': 'Missing metrics data'}

            values1 = np.array(data[metric1]['values'])
            values2 = np.array(data[metric2]['values'])

            # Align data by taking minimum length
            min_len = min(len(values1), len(values2))
            values1 = values1[:min_len]
            values2 = values2[:min_len]

            # Remove NaN values
            valid_mask = ~(np.isnan(values1) | np.isnan(values2))
            clean_values1 = values1[valid_mask]
            clean_values2 = values2[valid_mask]

            if len(clean_values1) < 3:
                return {'error': 'Insufficient data points for correlation'}

            # Calculate Pearson correlation
            correlation, p_value = pearsonr(clean_values1, clean_values2)

            # Format results similar to CorrelationAnalyzer
            pair_key = f"{metric1}_vs_{metric2}"
            return {
                'pairwise_correlations': {
                    pair_key: {
                        'pearson': {
                            'correlation': float(correlation),
                            'p_value': float(p_value),
                            'significant': p_value < 0.05,
                            'sample_size': len(clean_values1)
                        },
                        'sample_size': len(clean_values1)
                    }
                }
            }

        except Exception as e:
            return {'error': f'Simple correlation failed: {str(e)}'}

    def _handle_comparison_nlp(self, user_id: str, parsed_query: ParsedQuery) -> Dict:
        """Handle comparison queries with NLP parsing"""
        try:
            # Extract comparison periods from the query
            metric_name = parsed_query.metric_type.replace('_', ' ')

            # Try to get comparison data (simplified for demo)
            try:
                # Attempt to get data for both periods
                current_data = self.enhanced_aggregation_with_nlp(
                    user_id, parsed_query.metric_type, parsed_query.aggregation_type,
                    parsed_query.start_date, parsed_query.end_date
                )

                if current_data:
                    base_message = f"Your {metric_name} comparison shows interesting patterns. "
                    base_message += f"Recent analysis indicates {parsed_query.aggregation_type} of {current_data:.1f}."
                else:
                    base_message = f"Working on {metric_name} comparison analysis. "
                    base_message += "Comparison insights help you track progress over time periods."

            except Exception:
                base_message = f"Analyzing {metric_name} comparison patterns. "
                base_message += "Time period comparisons reveal important health trends and improvements."

            enhanced_message = self._enhance_message_with_llm(base_message, user_id, "comparison", parsed_query)

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_comparison",
                        "message": enhanced_message
                    }]
                }
            }

        except Exception as e:
            logger.warning(f"Comparison analysis failed: {str(e)}")
            base_message = f"Comparison analysis helps track your {parsed_query.metric_type.replace('_', ' ')} progress over different time periods."
            enhanced_message = self._enhance_message_with_llm(base_message, user_id, "comparison", parsed_query)

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "nlp_comparison",
                        "message": enhanced_message
                    }]
                }
            }

    def _get_metric_unit(self, metric_key: str) -> str:
        """Get unit for metric"""
        units = {
            "heart_rate": "bpm",
            "hrv": "ms",
            "sleep_score": "score",
            "temperature": "°C",
            "recovery": "score",
            "stress": "points",
            "steps": "steps",
            "vo2_max": "ml/kg/min"
        }
        return units.get(metric_key, "units")

    def _handle_structured_query(self, user_id: str, query: str) -> Dict:
        """Handle structured queries using LLM function calling"""
        try:
            from services.llm_service import SMSLLMService

            llm_service = SMSLLMService()
            response = llm_service.handle_structured_health_query(query, user_id)

            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "structured_query",
                        "message": response.content,
                        "provider": response.provider.value,
                        "tokens_used": response.tokens_used,
                        "cost_estimate": response.cost_estimate
                    }]
                }
            }

        except Exception as e:
            logger.error(f"Structured query failed: {str(e)}")
            return {
                "success": True,
                "events_processed": 0,
                "immediate_insights": {
                    "insights": [{
                        "type": "general",
                        "message": f"I understand you're asking about specific metrics, but I encountered an issue processing your query. Please try rephrasing or check if you have recent data."
                    }]
                }
            }

    # -------- intent predicates (keep your originals for backward-compat) --------

    def _is_correlation_query(self, message: str) -> bool:
        correlation_keywords = [
            'correlation', 'correlate', 'relationship', 'related', 'connection',
            'between', 'and', 'temperature', 'heart rate', 'hrv', 'sleep',
            'recovery', 'stress', 'activity', 'steps', 'vo2'
        ]
        correlation_count = sum(1 for keyword in correlation_keywords if keyword in message)
        has_between = 'between' in message and 'and' in message
        has_metrics = any(metric in message for metric in ['temperature', 'heart', 'hrv', 'sleep', 'recovery'])
        return correlation_count >= 2 or (has_between and has_metrics)

    def _is_general_health_question(self, text: str) -> bool:
        """Detect general health questions that need advice rather than data analysis"""
        text_lower = text.lower()

        # Must have both a health advice pattern AND a health topic
        has_advice_pattern = bool(INTENT_PATTERNS["health_advice"].search(text_lower))
        has_health_topic = bool(INTENT_PATTERNS["general_health"].search(text_lower))

        # Additional specific health question patterns
        health_question_patterns = [
            r"\bhow.*lower.*heart rate\b",
            r"\bhow.*improve.*sleep\b",
            r"\bhow.*reduce.*stress\b",
            r"\bhow.*increase.*hrv\b",
            r"\bwhat.*good.*heart rate\b",
            r"\bhow.*lose.*weight\b",
            r"\bwhat.*eat\b",
            r"\bexercise.*heart\b",
            r"\bwhen.*sleep\b",
            r"\bhow.*breathe\b",
            r"\bmeditation.*help\b",
            r"\btips.*recovery\b",
            r"\bwhy.*heart rate.*high\b",
            r"\bwhy.*sleep.*bad\b"
        ]

        has_specific_pattern = any(re.search(pattern, text_lower) for pattern in health_question_patterns)

        return (has_advice_pattern and has_health_topic) or has_specific_pattern

    def _is_lifestyle_event(self, message: str) -> bool:
        # First check if this looks like a question/analysis request (not a logging event)
        question_patterns = r'\b(what|how|is there|show me|correlation|relationship|trend|pattern|anomal)\b'
        if re.search(question_patterns, message, re.I):
            return False

        # Now check for actual lifestyle event patterns (more specific)
        lifestyle_patterns = [
            r'\bmeal\s+\w+',          # "meal chicken", "meal pasta"
            r'\bsupplement\s+',       # "supplement magnesium 400mg at 10pm" - match any supplement
            r'\bworkout\s+\w+',       # "workout cardio", "workout 30min"
            r'\bexercise\s+',         # "exercise running 30min 6am" - match any exercise
            r'\bactivity\s+',         # "activity swimming 1hr" - match any activity
            r'\bdrink\s+',            # "drink coffee 16oz 9am" - match any drink
            r'\b(?:ran|run|running|walked|walking|jogged|jogging)\s+\d+', # "ran 45 minutes", "walked 30 minutes"
            r'\bsleep\s+\d+:\d+',     # "sleep 23:30", "sleep 11pm"
            r'\bsleep\s+\w+\s+to\s+', # "sleep 11pm to 7am"
            r'\balcohol\s+\w+',       # "alcohol wine", "alcohol beer"
            r'\bcaffeine\s+\w+',      # "caffeine coffee", "caffeine 2pm"
            r'\bmood\s+\w+',          # "mood anxious", "mood happy"
            r'\bstress\s+\w+'         # "stress high", "stress work"
        ]

        return any(re.search(pattern, message, re.I) for pattern in lifestyle_patterns)

    def _extract_time_period_days(self, message: str) -> int:
        """Extract time period in days from message text"""

        # Common time period patterns
        patterns = [
            # "last 21 days", "past 14 days", "previous 7 days"
            r'(?:last|past|previous)\s+(\d+)\s+days?',
            # "21 days", "14 days" (standalone numbers)
            r'\b(\d+)\s+days?\b',
            # "three weeks", "two weeks", "one week"
            r'(?:last|past|previous)?\s*(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+weeks?',
            # Handle written numbers for weeks
            r'(?:last|past|previous)?\s*(one|two|three|four|five|six|seven|eight|nine|ten)\s+weeks?',
        ]

        # Word to number mapping
        word_to_num = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }

        for pattern in patterns:
            match = re.search(pattern, message, re.I)
            if match:
                period_str = match.group(1).lower()

                # Convert word to number if needed
                if period_str in word_to_num:
                    days = word_to_num[period_str] * 7  # weeks to days
                elif period_str.isdigit():
                    period_num = int(period_str)
                    # If pattern contains "week", multiply by 7
                    if 'week' in pattern:
                        days = period_num * 7
                    else:
                        days = period_num
                else:
                    continue

                # Reasonable bounds (1 day to 365 days)
                return max(1, min(365, days))

        # Default fallback: 7 days
        return 7

    # -------------------- Handlers: call analyzers + LLM --------------------

    def _handle_correlation(self, user_id: str, msg_lc: str) -> Dict:
        metrics = _extract_two_metrics_freeform(msg_lc)
        if len(metrics) < 2:
            return {"success": False, "error": "Please specify two metrics to compare (e.g., 'temperature and heart rate')"}

        m1, m2 = metrics[0], metrics[1]

        # Extract time period from message (e.g., "last 21 days", "last 14 days")
        days_back = self._extract_time_period_days(msg_lc)

        from services.statistical_analyzer import StatisticalAnalyzer
        analyzer = StatisticalAnalyzer()
        corr = analyzer.analyze_correlation(user_id, m1, m2, days_back=days_back)

        if not corr.get("success"):
            return {"success": False, "error": corr.get("error", "Failed to analyze correlation")}

        # Ensure structured payload has r/p/n/significance
        payload = {
            "success": True,
            "events_processed": 0,
            "correlation_analysis": {
                "metric1": m1,
                "metric2": m2,
                "correlation_coefficient": corr.get("correlation_coefficient"),
                "p_value": corr.get("p_value"),
                "sample_size": corr.get("sample_size"),
                "significance": corr.get("significance"),
            }
        }

        # LLM polish
        try:
            from services.minimal_llm_service import MinimalLLMService
            llm = MinimalLLMService()
            msg = llm.generate_health_insight(
                corr.get("correlation_coefficient", 0.0),
                corr.get("p_value", 1.0),
                corr.get("sample_size", 0),
                m1, m2
            )
            # Add time period context to the insight
            if days_back != 7:  # Only mention if not default
                msg += f" Based on {days_back} days of analysis."
        except Exception as e:
            logger.warning(f"LLM insight (correlation) failed: {e}")
            r = corr.get("correlation_coefficient", 0.0)
            p = corr.get("p_value", 1.0)
            n = corr.get("sample_size", 0)
            dirn = "positive" if r > 0 else "negative"
            strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.4 else "weak"
            sig = "significant" if p < 0.05 else "not significant"
            msg = f"📈 {strength} {dirn} correlation between {m1.replace('_',' ')} & {m2.replace('_',' ')} (r={r:.3f}, p={p:.3f}, n={n}; {sig})."

        payload["immediate_insights"] = {"insights": [{"type": "correlation", "message": msg, "data": payload["correlation_analysis"]}]}
        return payload

    def _handle_trend(self, user_id: str, msg_lc: str) -> Dict:
        # Try service analyzer; fallback to analysis module
        trend_res = None
        try:
            from services.statistical_analyzer import TrendAnalyzer  # if you have one
            trend = TrendAnalyzer()
            trend_res = trend.compute(user_id=user_id, query_text=msg_lc)
        except Exception:
            try:
                from analysis.trend_analysis import TrendAnalyzer as TA2
                trend = TA2()
                trend_res = trend.compute(user_id=user_id, query_text=msg_lc)
            except Exception as e2:
                logger.warning(f"Trend analyzer unavailable: {e2}")
                trend_res = {"success": False, "error": "Trend analysis unavailable"}

        if not trend_res or not trend_res.get("success"):
            # graceful fallback insight
            fallback = {
                "success": True,
                "events_processed": 0,
                "trend": {},
                "immediate_insights": {"insights": [{
                    "type": "trend",
                    "message": "No clear trend detected (insufficient data or high variance). Try a 7–14 day window and consistent logging."
                }]}
            }
            return fallback

        # Expected fields: metric, direction, strength (0-1), window_days, r2
        t = trend_res
        payload = {
            "success": True,
            "events_processed": 0,
            "trend": {
                "metric": t.get("metric"),
                "direction": t.get("direction"),      # improving / worsening / stable
                "strength": t.get("strength"),        # 0..1
                "r2": t.get("r2"),
                "window_days": t.get("window_days"),
            }
        }

        # LLM polish
        try:
            from services.minimal_llm_service import MinimalLLMService
            llm = MinimalLLMService()
            msg = llm.generate_trend_insight(
                metric=payload["trend"]["metric"],
                direction=payload["trend"]["direction"],
                strength=payload["trend"]["strength"],
                r2=payload["trend"]["r2"],
                window_days=payload["trend"]["window_days"]
            )
        except Exception:
            dir_emoji = "📈" if payload["trend"]["direction"] == "improving" else "📉" if payload["trend"]["direction"] == "worsening" else "➖"
            msg = f"{dir_emoji} {payload['trend']['metric']} trend: {payload['trend']['direction']} (strength {payload['trend']['strength']:.2f}, R²={payload['trend']['r2']:.2f}) over {payload['trend']['window_days']} days."

        payload["immediate_insights"] = {"insights": [{"type": "trend", "message": msg, "data": payload["trend"]}]}
        return payload

    def _handle_pattern(self, user_id: str, msg_lc: str) -> Dict:
        # Patterns: time-of-day/week associations, meal→overnight HR, etc.
        try:
            from services.pattern_recognition import PatternRecognizer
            pr = PatternRecognizer()
            patt = pr.find_patterns(user_id=user_id, query_text=msg_lc)
        except Exception as e:
            logger.warning(f"Pattern recognition unavailable: {e}")
            patt = {"success": False, "error": "Pattern analysis unavailable"}

        if not patt or not patt.get("success"):
            return {
                "success": True,
                "events_processed": 0,
                "patterns": {},
                "immediate_insights": {"insights": [{
                    "type": "pattern",
                    "message": "No clear recurring patterns detected. Try logging a few more days or narrowing to a weekday/time-of-day window."
                }]}
            }

        # Expected fields: top_patterns (list of dict summaries)
        payload = {
            "success": True,
            "events_processed": 0,
            "patterns": patt.get("top_patterns") or []
        }

        try:
            from services.minimal_llm_service import MinimalLLMService
            llm = MinimalLLMService()
            msg = llm.generate_pattern_insight(payload["patterns"])
        except Exception:
            # Compact human message
            if payload["patterns"]:
                p = payload["patterns"][0]
                msg = f"🧭 Pattern: {p.get('description','recurring effect')} (effect ~{p.get('effect_size','N/A')})."
            else:
                msg = "🧭 No strong recurring patterns detected."

        payload["immediate_insights"] = {"insights": [{"type": "pattern", "message": msg, "data": payload["patterns"]}]}
        return payload

    def _handle_anomaly(self, user_id: str, msg_lc: str) -> Dict:
        try:
            from services.statistical_analyzer import AnomalyDetector  # if exists
            ad = AnomalyDetector()
            res = ad.scan(user_id=user_id, query_text=msg_lc)
        except Exception:
            try:
                from analysis.anomaly_detection import AnomalyDetector as AD2
                ad = AD2()
                res = ad.scan(user_id=user_id, query_text=msg_lc)
            except Exception as e2:
                logger.warning(f"Anomaly detector unavailable: {e2}")
                res = {"success": False, "error": "Anomaly analysis unavailable"}

        if not res or not res.get("success"):
            return {
                "success": True,
                "events_processed": 0,
                "anomalies": [],
                "immediate_insights": {"insights": [{
                    "type": "anomaly",
                    "message": "No significant anomalies vs baseline. If you suspect a spike, specify the metric and date range."
                }]}
            }

        anomalies = res.get("anomalies") or []
        payload = {"success": True, "events_processed": 0, "anomalies": anomalies}

        try:
            from services.minimal_llm_service import MinimalLLMService
            llm = MinimalLLMService()
            msg = llm.generate_anomaly_insight(anomalies)
        except Exception:
            if anomalies:
                a = anomalies[0]
                msg = f"⚠️ {a.get('metric','metric').replace('_',' ').title()} anomaly: z={a.get('z_score','N/A')}, value={a.get('value','N/A')} @ {a.get('timestamp','')}"
            else:
                msg = "⚠️ No significant anomalies found."

        payload["immediate_insights"] = {"insights": [{"type": "anomaly", "message": msg, "data": anomalies}]}
        return payload

    def _handle_intervention(self, user_id: str, msg_lc: str) -> Dict:
        # Intervention effectiveness (pre/post deltas, simple AB-ish)
        try:
            from services.intervention_tracker import InterventionTracker
            it = InterventionTracker()
            res = it.evaluate(user_id=user_id, query_text=msg_lc)
        except Exception as e:
            logger.warning(f"Intervention tracker unavailable: {e}")
            res = {"success": False, "error": "Intervention analysis unavailable"}

        if not res or not res.get("success"):
            return {
                "success": True,
                "events_processed": 0,
                "intervention_effect": {},
                "immediate_insights": {"insights": [{
                    "type": "intervention",
                    "message": "Not enough data to attribute an effect. Keep the habit for 7–14 days and re-check."
                }]}
            }

        effect = {
            "intervention": res.get("intervention"),
            "primary_metric": res.get("primary_metric"),
            "improvement_pct": res.get("improvement_pct"),
            "confidence": res.get("confidence"),
            "n_before": res.get("n_before"),
            "n_after": res.get("n_after"),
            "window_days": res.get("window_days"),
        }
        payload = {"success": True, "events_processed": 0, "intervention_effect": effect}

        try:
            from services.minimal_llm_service import MinimalLLMService
            llm = MinimalLLMService()
            msg = llm.generate_intervention_insight(
                intervention=effect["intervention"],
                primary_metric=effect["primary_metric"],
                improvement_pct=effect["improvement_pct"],
                confidence=effect["confidence"],
                n_before=effect["n_before"],
                n_after=effect["n_after"]
            )
        except Exception:
            msg = (
                f"🎯 {effect.get('intervention','Intervention')} → "
                f"{effect.get('primary_metric','metric')} improved {effect.get('improvement_pct','N/A')}% "
                f"({effect.get('confidence','N/A')}% confidence)."
            )

        payload["immediate_insights"] = {"insights": [{"type": "intervention", "message": msg, "data": effect}]}
        return payload

    # ----------------- Legacy lifestyle acknowledgement path -----------------

    def _process_lifestyle_event(self, user_id: str, message: str) -> Dict:
        # Keep your original “ack” path for now; can be extended to parse and call log_lifestyle_event
        try:
            return {
                "success": True,
                "events_processed": 1,
                "immediate_insights": {"insights": [{"type": "lifestyle", "message": "✅ Event logged successfully!"}]}
            }
        except Exception as e:
            logger.error(f"Error processing lifestyle event: {str(e)}")
            return {"success": False, "error": str(e)}

    # --------------------- (legacy) metric extraction ---------------------

    def _extract_metrics_from_message(self, message: str) -> List[str]:
        # Retained for compatibility; new extractor _extract_two_metrics_freeform is preferred
        metric_mappings = {
            'temperature': 'temperature', 'temp': 'temperature', 'body temp': 'temperature',
            'heart rate': 'heart_rate', 'heart': 'heart_rate', 'hr': 'heart_rate',
            'hrv': 'hrv', 'heart rate variability': 'hrv',
            'sleep': 'sleep_score', 'sleep score': 'sleep_score',
            'recovery': 'recovery', 'recovery score': 'recovery',
            'stress': 'stress', 'activity': 'active_minutes', 'steps': 'steps',
            'vo2': 'vo2_max', 'vo2 max': 'vo2_max'
        }
        found_metrics = []
        for keyword, metric in metric_mappings.items():
            if keyword in message:
                found_metrics.append(metric)
        unique_metrics = []
        for metric in found_metrics:
            if metric not in unique_metrics:
                unique_metrics.append(metric)
        return unique_metrics[:2]

    # ==================== NEW: Aggregated Metric Queries ====================

    def fetch_metrics_aggregate(self, user_id: str, metric_key: str, aggregation: str,
                               start_date: str, end_date: str) -> Optional[float]:
        """Enhanced fetch aggregated metric values using comprehensive mapping"""
        try:
            # Use the enhanced lookup system with comprehensive metric mapping
            result = self.enhanced_lookup.fetch_metrics_aggregate_enhanced(
                user_id, metric_key, aggregation, start_date, end_date
            )

            if result is not None:
                logger.info(f"✅ Enhanced lookup found {metric_key} {aggregation}: {result}")
                return result
            else:
                logger.warning(f"❌ Enhanced lookup found no data for {metric_key} {aggregation}")

            # Fallback to original method for backwards compatibility
            return self._fetch_metrics_aggregate_fallback(user_id, metric_key, aggregation, start_date, end_date)

        except Exception as e:
            logger.error(f"Enhanced aggregated query failed for {metric_key}: {str(e)}")
            # Fallback to original method
            return self._fetch_metrics_aggregate_fallback(user_id, metric_key, aggregation, start_date, end_date)

    def _fetch_metrics_aggregate_fallback(self, user_id: str, metric_key: str, aggregation: str,
                                         start_date: str, end_date: str) -> Optional[float]:
        """Original aggregation method as fallback"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func

            # Parse dates
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            if start_dt >= end_dt:
                end_dt = start_dt + timedelta(days=1)  # Default to next day if same date

            # Simple metric mapping for fallback
            metric_mapping = {
                "hrv": ["hrv"],
                "heart_rate": ["heart_rate"],
                "sleep_score": ["sleep_score"],
                "temperature": ["temperature"],
                "recovery": ["recovery"],
                "steps": ["steps"],
                "active_minutes": ["active_minutes"],
                "vo2_max": ["vo2_max"],
                "movement_index": ["movement_index"]
            }

            metric_types = metric_mapping.get(metric_key, [metric_key])

            # Build query based on aggregation type
            query = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type.in_(metric_types),
                Metric.timestamp >= start_dt,
                Metric.timestamp < end_dt,
                Metric.value.isnot(None)
            )

            if aggregation == "average":
                result = query.with_entities(func.avg(Metric.value)).scalar()
            elif aggregation == "min":
                result = query.with_entities(func.min(Metric.value)).scalar()
            elif aggregation == "max":
                result = query.with_entities(func.max(Metric.value)).scalar()
            elif aggregation == "sum":
                result = query.with_entities(func.sum(Metric.value)).scalar()
            elif aggregation == "latest":
                latest_metric = query.order_by(Metric.timestamp.desc()).first()
                result = latest_metric.value if latest_metric else None
            else:
                logger.warning(f"Unknown aggregation type: {aggregation}")
                return None

            if result is not None:
                logger.info(f"✅ Fallback found {metric_key} {aggregation}: {result}")
                return float(result)
            return None

        except Exception as e:
            logger.error(f"Fallback aggregated query failed for {metric_key}: {str(e)}")
            return None

    def fetch_sleep_stage_info(self, user_id: str, stage_type: str, query_type: str,
                              start_date: str, end_date: str) -> Optional[Dict]:
        """Fetch sleep stage timing and duration information"""
        try:
            from datetime import datetime, timedelta

            # Parse dates
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            if start_dt >= end_dt:
                end_dt = start_dt + timedelta(days=1)

            # Map stage types to metric types
            stage_mapping = {
                "deep": ["deep_sleep_percentage", "deep_sleep_minutes"],
                "rem": ["rem_sleep_percentage", "rem_sleep_minutes"],
                "light": ["sleep_efficiency"],  # Proxy for light sleep
                "awake": ["sleep_score"]  # Proxy for wake periods
            }

            metric_types = stage_mapping.get(stage_type, [])
            if not metric_types:
                return {"error": f"Unknown sleep stage: {stage_type}"}

            # Query sleep metrics
            metrics = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type.in_(metric_types),
                Metric.timestamp >= start_dt,
                Metric.timestamp < end_dt,
                Metric.value.isnot(None)
            ).order_by(Metric.timestamp).all()

            if not metrics:
                return {"error": f"No {stage_type} sleep data found in date range"}

            if query_type == "average_timing":
                # Calculate average time of day for sleep events
                times = []
                for m in metrics:
                    hour = m.timestamp.hour
                    minute = m.timestamp.minute
                    time_decimal = hour + minute / 60.0
                    times.append(time_decimal)

                if times:
                    avg_time = sum(times) / len(times)
                    avg_hour = int(avg_time)
                    avg_minute = int((avg_time - avg_hour) * 60)
                    return {
                        "stage_type": stage_type,
                        "average_time": f"{avg_hour:02d}:{avg_minute:02d}",
                        "sample_size": len(times),
                        "date_range": f"{start_date} to {end_date}"
                    }

            elif query_type == "duration":
                # Calculate average duration (for percentage-based metrics, convert to estimated minutes)
                values = [m.value for m in metrics]
                avg_value = sum(values) / len(values)

                if "percentage" in metric_types[0]:
                    # Assume 8-hour sleep cycle for conversion
                    estimated_minutes = (avg_value / 100.0) * 480  # 8 hours = 480 minutes
                    return {
                        "stage_type": stage_type,
                        "average_percentage": round(avg_value, 1),
                        "estimated_minutes": round(estimated_minutes, 1),
                        "sample_size": len(values),
                        "date_range": f"{start_date} to {end_date}"
                    }
                else:
                    return {
                        "stage_type": stage_type,
                        "average_value": round(avg_value, 1),
                        "sample_size": len(values),
                        "date_range": f"{start_date} to {end_date}"
                    }

            elif query_type == "first_occurrence":
                # Return first occurrence in date range
                first_metric = metrics[0]
                return {
                    "stage_type": stage_type,
                    "first_occurrence": first_metric.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "value": first_metric.value,
                    "total_occurrences": len(metrics),
                    "date_range": f"{start_date} to {end_date}"
                }

            return {"error": f"Unknown query type: {query_type}"}

        except Exception as e:
            logger.error(f"Sleep stage query failed: {str(e)}")
            return {"error": f"Sleep stage analysis failed: {str(e)}"}

    def get_metric_summary(self, user_id: str, days: int = 7) -> Dict:
        """Get a comprehensive summary of user metrics for the LLM context"""
        try:
            from datetime import datetime, timedelta

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Get latest values for key metrics
            key_metrics = ["hrv", "heart_rate", "sleep_score", "temperature", "recovery", "steps"]
            summary = {}

            for metric in key_metrics:
                latest = Metric.query.filter(
                    Metric.user_id == user_id,
                    Metric.metric_type == metric,
                    Metric.timestamp >= start_date
                ).order_by(Metric.timestamp.desc()).first()

                if latest:
                    summary[metric] = {
                        "latest_value": latest.value,
                        "timestamp": latest.timestamp.isoformat(),
                        "unit": latest.unit
                    }

            return {
                "user_id": user_id,
                "summary_period_days": days,
                "metrics": summary,
                "generated_at": end_date.isoformat()
            }

        except Exception as e:
            logger.error(f"Metric summary failed: {str(e)}")
            return {"error": str(e)}

    def _process_sleep_stages_detailed(self, user_id: str, data_point: Dict, timestamp: datetime, metrics: List[Dict]):
        """Process detailed sleep stage data for enhanced analysis"""
        try:
            # Look for sleep stage data in various formats
            sleep_stages = data_point.get('sleep_stages', [])

            # Process individual sleep stages with timing
            for stage in sleep_stages:
                if not isinstance(stage, dict):
                    continue

                stage_type = stage.get('type', '').lower()
                duration = self._to_float(stage.get('duration_seconds'))
                start_time = stage.get('start_time')

                if stage_type and duration:
                    # Store stage duration
                    metrics.append({
                        'user_id': user_id,
                        'metric_type': f'{stage_type}_sleep_duration',
                        'value': duration / 60.0,  # Convert to minutes
                        'unit': 'minutes',
                        'timestamp': timestamp,
                        'source': 'ultrahuman',
                        'meta_data': {
                            'raw_data': stage,
                            'stage_type': stage_type,
                            'start_time': start_time
                        }
                    })

                # Store stage start time if available
                if start_time:
                    try:
                        stage_start = self._parse_timestamp(start_time)
                        time_of_day = stage_start.hour + stage_start.minute/60.0

                        metrics.append({
                            'user_id': user_id,
                            'metric_type': f'{stage_type}_sleep_start_time',
                            'value': time_of_day,
                            'unit': 'hour_of_day',
                            'timestamp': timestamp,
                            'source': 'ultrahuman',
                            'meta_data': {
                                'raw_data': stage,
                                'stage_type': stage_type,
                                'full_timestamp': stage_start.isoformat()
                            }
                        })
                    except Exception:
                        pass  # Skip if timestamp parsing fails

            # Process sleep efficiency breakdown if available
            sleep_breakdown = data_point.get('sleep_breakdown', {})
            for breakdown_type, value in sleep_breakdown.items():
                if breakdown_type.lower() in ['light', 'deep', 'rem', 'awake'] and value:
                    duration_minutes = self._to_float(value)
                    if duration_minutes:
                        metrics.append({
                            'user_id': user_id,
                            'metric_type': f'{breakdown_type.lower()}_sleep_minutes',
                            'value': duration_minutes,
                            'unit': 'minutes',
                            'timestamp': timestamp,
                            'source': 'ultrahuman',
                            'meta_data': {'raw_data': data_point, 'breakdown_type': breakdown_type}
                        })

        except Exception as e:
            logger.warning(f"Detailed sleep stage processing failed: {str(e)}")

    def get_sleep_pattern_analysis(self, user_id: str, days: int = 14) -> Dict:
        """Analyze sleep patterns for detailed insights"""
        try:
            from datetime import datetime, timedelta

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Query sleep timing metrics
            bedtime_metrics = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == 'bedtime',
                Metric.timestamp >= start_date
            ).order_by(Metric.timestamp).all()

            wake_time_metrics = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type == 'wake_time',
                Metric.timestamp >= start_date
            ).order_by(Metric.timestamp).all()

            # Query sleep stage metrics
            stage_metrics = Metric.query.filter(
                Metric.user_id == user_id,
                Metric.metric_type.like('%_sleep_%'),
                Metric.timestamp >= start_date
            ).all()

            analysis = {
                'user_id': user_id,
                'analysis_period_days': days,
                'sleep_schedule': {},
                'sleep_stages': {},
                'sleep_quality_trends': {}
            }

            # Analyze bedtime patterns
            if bedtime_metrics:
                bedtimes = [m.value for m in bedtime_metrics]
                analysis['sleep_schedule']['average_bedtime'] = f"{int(sum(bedtimes)/len(bedtimes)):02d}:{int(((sum(bedtimes)/len(bedtimes)) % 1) * 60):02d}"
                analysis['sleep_schedule']['bedtime_consistency'] = max(bedtimes) - min(bedtimes)
                analysis['sleep_schedule']['sample_size'] = len(bedtimes)

            # Analyze wake time patterns
            if wake_time_metrics:
                wake_times = [m.value for m in wake_time_metrics]
                analysis['sleep_schedule']['average_wake_time'] = f"{int(sum(wake_times)/len(wake_times)):02d}:{int(((sum(wake_times)/len(wake_times)) % 1) * 60):02d}"
                analysis['sleep_schedule']['wake_time_consistency'] = max(wake_times) - min(wake_times)

            # Analyze sleep stages
            stage_data = {}
            for metric in stage_metrics:
                stage_type = metric.metric_type
                if stage_type not in stage_data:
                    stage_data[stage_type] = []
                stage_data[stage_type].append(metric.value)

            for stage_type, values in stage_data.items():
                if values:
                    analysis['sleep_stages'][stage_type] = {
                        'average': sum(values) / len(values),
                        'range': {'min': min(values), 'max': max(values)},
                        'sample_size': len(values)
                    }

            return analysis

        except Exception as e:
            logger.error(f"Sleep pattern analysis failed: {str(e)}")
            return {"error": str(e)}

    # ==================== DATABASE QUERY OPTIMIZATION ====================

    def fetch_metrics_aggregate_optimized(self, user_id: str, metric_key: str, aggregation: str,
                                         start_date: str, end_date: str) -> Optional[float]:
        """Optimized aggregation using raw SQL for better performance"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import text

            # Parse dates
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            if start_dt >= end_dt:
                end_dt = start_dt + timedelta(days=1)

            # Map metric keys to database metric_type names
            metric_mapping = {
                "hrv": ["hrv", "hrv_sleep"],
                "heart_rate": ["heart_rate"],
                "sleep_score": ["sleep_score"],
                "temperature": ["temperature"],
                "recovery": ["recovery"],
                "stress": ["stress"],
                "steps": ["steps"],
                "calories_burned": ["calories_burned"],
                "active_minutes": ["active_minutes"],
                "glucose": ["glucose", "average_glucose"],
                "hba1c": ["hba1c"],
                "vo2_max": ["vo2_max"]
            }

            metric_types = metric_mapping.get(metric_key, [metric_key])

            # Build optimized SQL query
            if aggregation == "average":
                agg_func = "AVG"
            elif aggregation == "min":
                agg_func = "MIN"
            elif aggregation == "max":
                agg_func = "MAX"
            elif aggregation == "sum":
                agg_func = "SUM"
            elif aggregation == "latest":
                # Special case for latest - needs different query structure
                sql_query = text("""
                    SELECT value
                    FROM metric
                    WHERE user_id = :user_id
                        AND metric_type IN :metric_types
                        AND timestamp >= :start_dt
                        AND timestamp < :end_dt
                        AND value IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)

                result = db.session.execute(sql_query, {
                    'user_id': user_id,
                    'metric_types': tuple(metric_types),
                    'start_dt': start_dt,
                    'end_dt': end_dt
                }).scalar()

                return float(result) if result is not None else None
            else:
                logger.warning(f"Unknown aggregation type: {aggregation}")
                return None

            # Standard aggregation query
            sql_query = text(f"""
                SELECT {agg_func}(value) as result
                FROM metric
                WHERE user_id = :user_id
                    AND metric_type IN :metric_types
                    AND timestamp >= :start_dt
                    AND timestamp < :end_dt
                    AND value IS NOT NULL
            """)

            result = db.session.execute(sql_query, {
                'user_id': user_id,
                'metric_types': tuple(metric_types),
                'start_dt': start_dt,
                'end_dt': end_dt
            }).scalar()

            return float(result) if result is not None else None

        except Exception as e:
            logger.error(f"Optimized aggregated query failed for {metric_key}: {str(e)}")
            # Fallback to ORM method
            return self.fetch_metrics_aggregate(user_id, metric_key, aggregation, start_date, end_date)

    def get_metrics_batch_optimized(self, user_id: str, metric_types: List[str],
                                   days_back: int = 7) -> Dict:
        """Optimized batch retrieval of multiple metrics"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import text

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            # Single query to get all metrics at once
            sql_query = text("""
                SELECT
                    metric_type,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    COUNT(*) as count,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest
                FROM metric
                WHERE user_id = :user_id
                    AND metric_type IN :metric_types
                    AND timestamp >= :start_date
                    AND value IS NOT NULL
                GROUP BY metric_type
            """)

            results = db.session.execute(sql_query, {
                'user_id': user_id,
                'metric_types': tuple(metric_types),
                'start_date': start_date
            }).fetchall()

            metrics_summary = {}
            for row in results:
                metrics_summary[row.metric_type] = {
                    'average': float(row.avg_value),
                    'min': float(row.min_value),
                    'max': float(row.max_value),
                    'count': row.count,
                    'earliest': row.earliest.isoformat() if row.earliest else None,
                    'latest': row.latest.isoformat() if row.latest else None,
                    'days_covered': (row.latest - row.earliest).days if row.earliest and row.latest else 0
                }

            return {
                'user_id': user_id,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days_back
                },
                'metrics_summary': metrics_summary,
                'query_performance': 'optimized_batch'
            }

        except Exception as e:
            logger.error(f"Optimized batch query failed: {str(e)}")
            # Fallback to individual queries
            return {
                'error': str(e),
                'fallback_available': True,
                'user_id': user_id
            }

    def get_correlation_data_optimized(self, user_id: str, metric1: str, metric2: str,
                                     days_back: int = 30) -> Optional[Dict]:
        """Optimized correlation data retrieval with single query"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import text

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)

            # Single query to get paired data for correlation
            sql_query = text("""
                WITH metric1_data AS (
                    SELECT DATE(timestamp) as date, AVG(value) as value1
                    FROM metric
                    WHERE user_id = :user_id
                        AND metric_type = :metric1
                        AND timestamp >= :start_date
                        AND value IS NOT NULL
                    GROUP BY DATE(timestamp)
                ),
                metric2_data AS (
                    SELECT DATE(timestamp) as date, AVG(value) as value2
                    FROM metric
                    WHERE user_id = :user_id
                        AND metric_type = :metric2
                        AND timestamp >= :start_date
                        AND value IS NOT NULL
                    GROUP BY DATE(timestamp)
                )
                SELECT
                    m1.date,
                    m1.value1,
                    m2.value2
                FROM metric1_data m1
                INNER JOIN metric2_data m2 ON m1.date = m2.date
                ORDER BY m1.date
            """)

            results = db.session.execute(sql_query, {
                'user_id': user_id,
                'metric1': metric1,
                'metric2': metric2,
                'start_date': start_date
            }).fetchall()

            if len(results) < 3:  # Need at least 3 points for correlation
                return None

            dates = [row.date.isoformat() for row in results]
            values1 = [float(row.value1) for row in results]
            values2 = [float(row.value2) for row in results]

            return {
                'user_id': user_id,
                'metric1': metric1,
                'metric2': metric2,
                'dates': dates,
                'values1': values1,
                'values2': values2,
                'sample_size': len(results),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days_back
                }
            }

        except Exception as e:
            logger.error(f"Optimized correlation query failed: {str(e)}")
            return None

    def get_time_series_optimized(self, user_id: str, metric_type: str,
                                 hours_back: int = 24, sample_interval: int = 60) -> Dict:
        """Optimized time series data with sampling for large datasets"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import text

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=hours_back)

            # Use time-based sampling to reduce data points for large ranges
            if hours_back > 168:  # More than a week, sample every 4 hours
                sample_interval = 240
            elif hours_back > 48:  # More than 2 days, sample every 2 hours
                sample_interval = 120

            sql_query = text("""
                SELECT
                    timestamp,
                    value,
                    z_score,
                    anomaly_score
                FROM metric
                WHERE user_id = :user_id
                    AND metric_type = :metric_type
                    AND timestamp >= :start_date
                    AND value IS NOT NULL
                    AND EXTRACT(EPOCH FROM timestamp) % :sample_interval = 0
                ORDER BY timestamp
                LIMIT 1000
            """)

            results = db.session.execute(sql_query, {
                'user_id': user_id,
                'metric_type': metric_type,
                'start_date': start_date,
                'sample_interval': sample_interval
            }).fetchall()

            data_points = []
            for row in results:
                data_points.append({
                    'timestamp': row.timestamp.isoformat(),
                    'value': float(row.value),
                    'z_score': float(row.z_score) if row.z_score else None,
                    'anomaly_score': float(row.anomaly_score) if row.anomaly_score else None
                })

            return {
                'user_id': user_id,
                'metric_type': metric_type,
                'data_points': data_points,
                'sample_interval_minutes': sample_interval,
                'total_points': len(data_points),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'hours': hours_back
                }
            }

        except Exception as e:
            logger.error(f"Optimized time series query failed: {str(e)}")
            return {'error': str(e), 'user_id': user_id, 'metric_type': metric_type}

    def _parse_lifestyle_sms(self, text: str, current_time: datetime = None) -> tuple[str, dict, datetime]:
        """Parse SMS text into structured lifestyle event data with improved regex patterns"""
        import re
        from datetime import datetime, time

        text_lower = text.lower().strip()
        if current_time is None:
            current_time = datetime.utcnow()

        # Parse meal events - improved pattern
        meal_patterns = [
            r'meal\s+(\w+)(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)|breakfast|lunch|dinner))?',
            r'ate\s+(\w+)(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',
            r'had\s+(\w+)(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?'
        ]

        for pattern in meal_patterns:
            meal_match = re.search(pattern, text_lower)
            if meal_match:
                food = meal_match.group(1)
                time_str = meal_match.group(2)

                event_timestamp = self._parse_time_string(time_str, current_time) if time_str else current_time

                details = {
                    'food': food,
                    'parsed_from_sms': True,
                    'original_text': text
                }
                return 'meal', details, event_timestamp

        # Parse supplement events - IMPROVED with multiple flexible patterns
        supplement_patterns = [
            # Pattern 1: "supplement magnesium400mg 10pm" (no spaces)
            r'supplement\s+(\w+)(\d+(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',

            # Pattern 2: "supplement magnesium 400mg 10pm" (with spaces)
            r'supplement\s+(\w+)\s+(\d+(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',

            # Pattern 3: More flexible with optional "at"
            r'supplement\s+(\w+)\s*(\d+\s*(?:mg|g|iu|mcg|pills?|capsules?|tablets?))\s*(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm))?',

            # Pattern 4: Just supplement name and time (no dosage)
            r'supplement\s+(\w+)\s*(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm))',

            # Pattern 5: Just supplement name (no dosage or time)
            r'supplement\s+(\w+)$'
        ]

        for i, pattern in enumerate(supplement_patterns):
            supplement_match = re.search(pattern, text_lower)
            if supplement_match:
                groups = supplement_match.groups()

                if i < 3:  # Patterns with dosage
                    name = groups[0]
                    dosage = groups[1] if len(groups) > 1 and groups[1] else "unknown"
                    time_str = groups[2] if len(groups) > 2 and groups[2] else None
                elif i == 3:  # Pattern with name and time, no dosage
                    name = groups[0]
                    dosage = "unknown"
                    time_str = groups[1] if len(groups) > 1 and groups[1] else None
                else:  # Pattern with just name
                    name = groups[0]
                    dosage = "unknown"
                    time_str = None

                event_timestamp = self._parse_time_string(time_str, current_time) if time_str else current_time

                details = {
                    'name': name,
                    'dosage': dosage,
                    'parsed_from_sms': True,
                    'original_text': text,
                    'pattern_used': i + 1  # For debugging
                }
                return 'supplement', details, event_timestamp

        # Parse exercise/workout events - improved pattern
        exercise_patterns = [
            # Direct activity patterns: "ran 45 minutes at 6am"
            r'(ran|run|running|walked|walking|jogged|jogging|swam|swimming|cycled|cycling)\s+(\d+)\s+(minutes?|mins?|hours?|hrs?)\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',
            # Exercise/workout patterns: "exercise running 30min"
            r'(?:exercise|workout|activity)\s+(\w+)(?:\s+(\d+)(?:min|minutes?)?)?(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',
            # "did workout" patterns: "did cardio workout"
            r'(?:did|had)\s+(\w+)\s+(?:workout|exercise)(?:\s+(\d+)(?:min|minutes?)?)?(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?'
        ]

        for i, pattern in enumerate(exercise_patterns):
            exercise_match = re.search(pattern, text_lower)
            if exercise_match:
                groups = exercise_match.groups()

                if i == 0:  # Direct activity pattern: "ran 45 minutes at 6am"
                    exercise_type = groups[0]  # "ran"
                    duration = groups[1]       # "45"
                    unit = groups[2]           # "minutes"
                    time_str = groups[3] if len(groups) > 3 else None  # "6am"

                    # Convert duration based on unit
                    if 'hour' in unit:
                        duration_minutes = int(duration) * 60
                    else:
                        duration_minutes = int(duration)

                else:  # Other patterns: "exercise running", "did cardio workout"
                    exercise_type = groups[0]
                    duration = groups[1] if len(groups) > 1 else None
                    time_str = groups[2] if len(groups) > 2 else None
                    duration_minutes = int(duration) if duration else None

                event_timestamp = self._parse_time_string(time_str, current_time) if time_str else current_time

                details = {
                    'type': exercise_type,
                    'parsed_from_sms': True,
                    'original_text': text
                }

                if duration_minutes:
                    details['duration_minutes'] = duration_minutes
                    details['intensity'] = 'moderate'  # Default intensity

                return 'activity', details, event_timestamp

        # Parse sleep events - improved pattern
        sleep_patterns = [
            r'sleep(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)|bedtime))?',
            r'went\s+to\s+bed(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?',
            r'bedtime(?:\s+(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?'
        ]

        for pattern in sleep_patterns:
            sleep_match = re.search(pattern, text_lower)
            if sleep_match:
                time_str = sleep_match.group(1)

                # Default to current time if no time specified
                if time_str and time_str == 'bedtime':
                    # Assume bedtime is 11 PM
                    event_timestamp = current_time.replace(hour=23, minute=0, second=0, microsecond=0)
                elif time_str:
                    event_timestamp = self._parse_time_string(time_str, current_time)
                else:
                    event_timestamp = current_time

                details = {
                    'parsed_from_sms': True,
                    'original_text': text
                }
                return 'sleep_quality', details, event_timestamp

        # Parse drink events - improved pattern to capture multi-word drinks
        drink_patterns = [
            r'(?:drink|drank|had)\s+([\w\s]+?)(?:\s+(\d+(?:oz|ml|cups?)?))?\s*(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm))',
            r'(?:drink|drank|had)\s+([\w\s]+?)$',  # Just "drink green tea" without time
            r'(\w+)\s+(?:drink|beverage)(?:\s+(\d+(?:oz|ml|cups?)?))?\s*(?:(?:at\s+)?(\d+(?::\d+)?(?:am|pm)?|\d+(?:am|pm)))?'
        ]

        for pattern in drink_patterns:
            drink_match = re.search(pattern, text_lower)
            if drink_match:
                drink_type = drink_match.group(1)
                amount = drink_match.group(2)
                time_str = drink_match.group(3)

                event_timestamp = self._parse_time_string(time_str, current_time) if time_str else current_time

                details = {
                    'drink_type': drink_type,
                    'parsed_from_sms': True,
                    'original_text': text
                }

                if amount:
                    details['amount'] = amount

                return 'drink', details, event_timestamp

        # Default fallback - treat as generic lifestyle event
        return 'meal', {'food': 'unknown', 'parsed_from_sms': True, 'original_text': text}, current_time

    def _parse_time_string(self, time_str: str, reference_time: datetime) -> datetime:
        """Parse time string into datetime with improved handling"""
        import re
        from datetime import datetime, time as dt_time

        if not time_str:
            return reference_time

        time_str = time_str.lower().strip()

        # Handle "bedtime"
        if time_str == 'bedtime':
            return reference_time.replace(hour=23, minute=0, second=0, microsecond=0)

        # Parse formats like "7pm", "19:30", "7:30pm", "10pm"
        time_patterns = [
            r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)',  # "7:30pm", "10pm"
            r'(\d{1,2}):(\d{2})',                  # "19:30", "22:15"
            r'(\d{1,2})\s*(am|pm)',                # "7pm", "10am"
            r'(\d{1,2})$'                          # Just "7", "22"
        ]

        for pattern in time_patterns:
            time_match = re.search(pattern, time_str)
            if time_match:
                groups = time_match.groups()
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) > 1 and groups[1] and groups[1].isdigit() else 0
                ampm = groups[2] if len(groups) > 2 and groups[2] else groups[1] if len(groups) > 1 and groups[1] in ['am', 'pm'] else None

                # Convert to 24-hour format
                if ampm == 'pm' and hour != 12:
                    hour += 12
                elif ampm == 'am' and hour == 12:
                    hour = 0
                elif not ampm and hour <= 12:
                    # Smart defaults based on hour
                    if hour >= 6 and hour <= 11:
                        # Morning hours - assume AM
                        pass
                    elif hour >= 1 and hour <= 5:
                        # Could be early morning or late night - assume PM if after noon
                        if reference_time.hour >= 12:
                            hour += 12
                    # For 12-24 hour format, leave as is

                try:
                    return reference_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except ValueError:
                    # Invalid hour/minute, return reference time
                    return reference_time

        return reference_time

    def _parse_all_lifestyle_events(self, text: str, current_time: datetime = None) -> List[Dict]:
        """Parse all lifestyle events from a potentially multi-line SMS message"""
        import re

        if current_time is None:
            current_time = datetime.utcnow()

        events = []

        # Split message into lines and process each
        lines = text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line contains a lifestyle event
            if self._is_lifestyle_event(line.lower()):
                try:
                    event_type, details, timestamp = self._parse_lifestyle_sms(line, current_time)
                    events.append({
                        'event_type': event_type,
                        'details': details,
                        'timestamp': timestamp,
                        'original_line': line
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse line '{line}': {str(e)}")
                    # Continue to next line instead of failing completely
                    continue

        return events

    def _process_multiple_lifestyle_events(self, user_id: str, events: List[Dict]) -> Dict:
        """Process multiple lifestyle events and return consolidated response"""
        successful_events = []
        failed_events = []
        total_metrics_created = 0

        for event in events:
            try:
                result = self.log_lifestyle_event(
                    user_id,
                    event['event_type'],
                    event['details'],
                    event['timestamp']
                )

                if result.get("success"):
                    successful_events.append(event)
                    total_metrics_created += result.get("metrics_created", 1)
                else:
                    failed_events.append(event)

            except Exception as e:
                logger.error(f"Failed to log event {event['event_type']}: {str(e)}")
                failed_events.append(event)

        # Build response message
        if successful_events:
            if len(successful_events) == 1:
                # Single event - detailed response
                event = successful_events[0]
                response_message = f"✅ {event['event_type'].replace('_', ' ').title()} logged successfully!"

                # Add details
                details = event['details']
                if event['event_type'] == "meal" and "food" in details:
                    response_message += f" Food: {details['food']}"
                elif event['event_type'] == "supplement" and "name" in details:
                    response_message += f" Supplement: {details['name']}"
                    if "dosage" in details:
                        response_message += f" ({details['dosage']})"
                elif event['event_type'] == "activity" and "type" in details:
                    response_message += f" Activity: {details['type']}"
                    if "duration_minutes" in details:
                        response_message += f" ({details['duration_minutes']} min)"

                # Add timestamp
                if event['timestamp']:
                    time_str = event['timestamp'].strftime("%I:%M %p").lstrip('0')
                    response_message += f" at {time_str}"
            else:
                # Multiple events - summary response
                event_types = [event['event_type'].replace('_', ' ').title() for event in successful_events]
                response_message = f"✅ Logged {len(successful_events)} events: {', '.join(event_types)}"

                if failed_events:
                    response_message += f" ({len(failed_events)} failed)"

            return {
                "success": True,
                "events_processed": len(successful_events),
                "metrics_created": total_metrics_created,
                "failed_events": len(failed_events),
                "immediate_insights": {
                    "insights": [{
                        "type": "lifestyle_stored",
                        "message": response_message
                    }]
                }
            }
        else:
            # All events failed
            return {
                "success": False,
                "error": "Failed to store any lifestyle events",
                "events_processed": 0,
                "failed_events": len(failed_events),
                "immediate_insights": {
                    "insights": [{
                        "type": "lifestyle_error",
                        "message": "❌ Failed to log events. Please try again with format: 'meal chicken 7pm' or 'supplement magnesium 400mg 10pm'"
                    }]
                }
            }

    def _is_conversational_message(self, text: str) -> tuple[bool, str]:
        """Detect conversational messages and return appropriate response"""
        text_lower = text.lower().strip()

        # Greeting patterns
        greeting_patterns = [
            r'^(hi|hello|hey|good morning|good afternoon|good evening)!?$',
            r'^(hi|hello|hey) there!?$',
            r'^how are you\??$'
        ]

        for pattern in greeting_patterns:
            if re.match(pattern, text_lower):
                return True, self._get_greeting_response()

        # Thank you patterns
        thanks_patterns = [
            r'^(thank you|thanks|thx)!?$',
            r'^(thank you|thanks) so much!?$',
            r'^(appreciate it|thanks a lot)!?$',
            r'^ok thank you$',
            r'^got it,? thanks?$'
        ]

        for pattern in thanks_patterns:
            if re.match(pattern, text_lower):
                return True, self._get_thanks_response()

        # Goodbye patterns
        goodbye_patterns = [
            r'^(bye|goodbye|see you|talk later)!?$',
            r'^have a good (day|night|evening)!?$'
        ]

        for pattern in goodbye_patterns:
            if re.match(pattern, text_lower):
                return True, self._get_goodbye_response()

        return False, ""

    def _get_greeting_response(self) -> str:
        """Generate appropriate greeting response"""
        responses = [
            "Hello! I'm Ava, your health coach. How can I help you today?",
            "Hi there! Ready to explore your health data? Ask me anything!",
            "Hello! I can help you track metrics, find correlations, or answer health questions. What would you like to know?"
        ]
        import random
        return random.choice(responses)

    def _get_thanks_response(self) -> str:
        """Generate appropriate thank you response"""
        responses = [
            "You're welcome! Happy to help anytime. 😊",
            "My pleasure! Feel free to ask if you need anything else.",
            "Glad I could help! I'm here whenever you need health insights.",
            "You're very welcome! Keep up the great work with your health tracking! 💪"
        ]
        import random
        return random.choice(responses)

    def _get_goodbye_response(self) -> str:
        """Generate appropriate goodbye response"""
        responses = [
            "Goodbye! Take care and keep tracking your health! 🌟",
            "See you later! Remember to stay hydrated and get good sleep!",
            "Have a great day! I'll be here when you need me. 👋"
        ]
        import random
        return random.choice(responses)

    def _extract_numeric_dosage(self, dosage_str: str) -> float:
        """Extract numeric dosage value from string like '400mg', '1000IU', '2 capsules'"""
        import re

        if not dosage_str:
            return 1.0

        # Look for numbers in the dosage string
        numbers = re.findall(r'[\d.]+', str(dosage_str))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                pass

        return 1.0  # Default to 1 if no number found

    def _extract_dosage_unit(self, dosage_str: str) -> str:
        """Extract unit from dosage string like '400mg' -> 'mg', '1000IU' -> 'IU'"""
        import re

        if not dosage_str:
            return "dose"

        dosage_str = str(dosage_str).lower()

        # Common supplement units
        unit_patterns = [
            (r'\d+\.?\d*\s*mg', 'mg'),
            (r'\d+\.?\d*\s*g\b', 'g'),
            (r'\d+\.?\d*\s*mcg', 'mcg'),
            (r'\d+\.?\d*\s*iu', 'IU'),
            (r'\d+\.?\d*\s*pills?', 'pills'),
            (r'\d+\.?\d*\s*capsules?', 'capsules'),
            (r'\d+\.?\d*\s*tablets?', 'tablets'),
            (r'\d+\.?\d*\s*drops?', 'drops'),
            (r'\d+\.?\d*\s*ml', 'ml'),
            (r'\d+\.?\d*\s*oz', 'oz')
        ]

        for pattern, unit in unit_patterns:
            if re.search(pattern, dosage_str):
                return unit

        return "dose"  # Default unit

    def _extract_volume_unit(self, volume_str: str) -> str:
        """Extract volume unit from string like '16oz' -> 'oz', '250ml' -> 'ml'"""
        import re

        if not volume_str:
            return "servings"

        volume_str = str(volume_str).lower()

        # Common volume units
        volume_patterns = [
            (r'\d+\.?\d*\s*oz', 'oz'),
            (r'\d+\.?\d*\s*ml', 'ml'),
            (r'\d+\.?\d*\s*cups?', 'cups'),
            (r'\d+\.?\d*\s*liters?', 'liters'),
            (r'\d+\.?\d*\s*pints?', 'pints'),
            (r'\d+\.?\d*\s*glasses?', 'glasses')
        ]

        for pattern, unit in volume_patterns:
            if re.search(pattern, volume_str):
                return unit

        return "servings"  # Default unit

    def _estimate_caffeine_content(self, drink_type: str, amount: float = 1.0) -> float:
        """Estimate caffeine content based on drink type and amount"""

        # Caffeine content per standard serving (mg)
        caffeine_per_serving = {
            'coffee': 95,    # 8oz cup
            'espresso': 64,  # 1oz shot
            'tea': 26,       # 8oz cup
            'green_tea': 28, # 8oz cup
            'black_tea': 47, # 8oz cup
            'matcha': 70,    # 8oz cup
            'energy_drink': 80  # 8oz can
        }

        base_caffeine = caffeine_per_serving.get(drink_type, 50)  # Default 50mg
        return base_caffeine * amount
