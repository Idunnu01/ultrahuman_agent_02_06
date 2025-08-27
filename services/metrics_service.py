"""
Metrics service for processing Ultrahuman Ring data and user lifestyle events
"""

import os
import json  # ADD THIS IMPORT
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import requests
import numpy as np
# pandas kept in case other parts import it elsewhere; safe to remove if unused
import pandas as pd  # noqa: F401

from app.models import User, Metric, SystemLog
from utils.database import db, bulk_insert_metrics
from utils.cache import MetricsCache, cache_user_data
from utils.stats_utils import StatisticalValidator, RobustStatistics

logger = logging.getLogger(__name__)


class MetricsService:
    """Core service for handling all health metrics and lifestyle data"""

    def __init__(self):
        self.ultrahuman_base_url = os.getenv("ULTRAHUMAN_API_BASE", "https://api.ultrahuman.com").rstrip("/")
        self.ultrahuman_api_key = os.getenv("ULTRAHUMAN_API_KEY")
        self.store_minute_series = os.getenv("ULTRAHUMAN_STORE_MINUTE_SERIES", "0") == "1"

        # Mappings kept for future use/extensions
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
        """
        Resolve Ultrahuman email with precedence:
          1) env UH_EMAIL
          2) user.preferences.ultrahuman_email
          3) user.preferences.email
          4) user.ultrahuman_user_id
        """
        uh_email = os.getenv("UH_EMAIL")
        if uh_email:
            return uh_email

        prefs = (getattr(user, "preferences", None) or {}) if user else {}
        if prefs.get("ultrahuman_email"):
            return prefs["ultrahuman_email"]
        if prefs.get("email"):
            return prefs["email"]

        return getattr(user, "ultrahuman_user_id", None)

    def _to_float(self, x):
        """Best-effort numeric conversion; returns None for null/blank/non-numeric."""
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
        """
        Fetch data for a user/date range.

        Partner API (preferred):
          GET /metrics?email=<email>&date=YYYY-MM-DD
          Header: Authorization: <RAW_TOKEN> (no "Bearer")
          One request per day in [start, end] inclusive.

        Legacy product endpoints (fallback):
          /users/{email}/hrv|sleep|activity|recovery?start_date=...&end_date=...
          Header: Authorization: Bearer <TOKEN>
        """
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

            # normalize dates
            start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
            end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
            if start_dt >= end_dt:
                return {"error": "Invalid date range: start_date must be before end_date", "user_id": user_id}

            s = start_dt.date()
            e = end_dt.date()

            # -------- Partner API mode (per-day) --------
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

            # -------- Legacy (range) --------
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
        """Make authenticated GET request to Ultrahuman API"""
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

    def _map_partner_to_internal(self, response: Dict) -> Dict[str, List[dict]]:
        """
        Map Partner day payload into buckets - FIXED VERSION
        """
        out = {"sleep": [], "activity": [], "hrv": [], "recovery": [], "series": []}
        if not isinstance(response, dict):
            return out

        payload = response.get("data") or response.get("metrics") or response
        metric_data = payload.get("metric_data") if isinstance(payload, dict) else None
        if not isinstance(metric_data, list):
            # Legacy/alternate shapes
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

        # Group recovery metrics by day to merge them
        recovery_by_day = {}

        for item in metric_data:
            if not isinstance(item, dict):
                continue

            typ_raw = item.get("type")
            typ = (typ_raw or "").lower().strip()
            # DEBUG: Log all metric types we're seeing
            if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                print(f"DEBUG: Processing metric type: '{typ}' from raw: '{typ_raw}'")
            obj = item.get("object") or {}
            day_start = obj.get("day_start_timestamp")
            day_key = day_iso(day_start) if day_start else None

            # ------------------ SLEEP (daily) ------------------
            if typ == "sleep" or typ == "sleep_score" or typ == "sleep_summary":
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Full sleep object: {obj}")
                    print(f"DEBUG: Sleep object keys: {list(obj.keys())}")

                s = {}
                details = obj.get("details") or {}
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Sleep details keys: {list(details.keys()) if details else 'No details'}")

                bt_start = details.get("bedtime_start")
                s["bedtime"] = ts_iso(bt_start or day_start)

                # sleep score may be under object.score or object.sleep_score.score
                sc = obj.get("score")
                if sc is None:
                    ss = obj.get("sleep_score")
                    if isinstance(ss, dict):
                        sc = ss.get("score")
                if sc is not None:
                    s["sleep_score"] = sc

                # total sleep (seconds) + efficiency from quick_metrics
                total_sleep_min = None
                qm = details.get("quick_metrics") or []
                for q in qm:
                    qtype = (q.get("type") or "").lower()
                    if qtype == "total_sleep" and "value" in q:
                        total_sleep_min = float(q["value"]) / 60.0
                        s["total_sleep_time"] = total_sleep_min
                    if qtype in ("sleep_efic", "sleep_efficiency") and "value" in q:
                        s["sleep_efficiency"] = q["value"]

                # fallback: sleep efficiency from summary list
                if "sleep_efficiency" not in s:
                    for summ in details.get("summary") or []:
                        title = (summ.get("title") or "").lower()
                        if title.startswith("sleep efficiency") and "score" in summ:
                            s["sleep_efficiency"] = summ["score"]
                            break

                # deep/REM minutes from stage percentages
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

                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Processed sleep data: {s}")

                if any(k in s for k in ("sleep_score", "sleep_efficiency", "total_sleep_time",
                                         "deep_sleep_minutes", "rem_sleep_minutes", "bedtime")):
                    out["sleep"].append(s)
                continue

            # ------------------ SKIN TEMPERATURE ------------------
            if typ == "temp":
                vals = obj.get("values") or []
                nums = [_num(v.get("value")) for v in vals if v and v.get("value") is not None]
                if nums and day_key:
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["skin_temperature"] = float(sum(nums) / len(nums))
                continue

            # ------------------ HRV (daily avg) ------------------
            if typ == "hrv":
                avg = _num(obj.get("avg"))
                ts = ts_iso(day_start)
                if avg is not None and ts:
                    out["hrv"].append({"timestamp": ts, "rmssd": avg})
                continue

            # ------------------ Average Sleep HRV (separate metric) ------------------
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

            # ------------------ NIGHT RESTING HR ------------------
            if typ in ("night_rhr", "sleep_rhr"):
                avg = _num(obj.get("avg"))
                if avg is not None and day_key:
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["resting_heart_rate"] = avg
                continue

            # ------------------ STEPS (daily sum from values) ------------------
            if typ == "steps":
                vals = obj.get("values") or []
                svals = [_num(v.get("value")) for v in vals if v and v.get("value") is not None]
                if svals and day_start:
                    out["activity"].append({
                        "date": day_iso(day_start),
                        "steps": float(sum(svals))
                    })
                continue

            # ------------------ ACTIVE MINUTES (own type) ------------------
            if typ == "active_minutes":
                val = _num(obj.get("value"))
                if val is None:
                    vals = obj.get("values") or []
                    arr = [_num(v.get("value")) for v in vals if v and v.get("value") is not None]
                    if arr:
                        val = float(sum(arr))
                if val is not None and day_start:
                    out["activity"].append({
                        "date": day_iso(day_start),
                        "active_minutes": val
                    })
                continue

            # ------------------ RECOVERY SCORE / INDEX ------------------
            if typ in ("recovery", "recovery_index"):
                val = _num(obj.get("score") or obj.get("value"))
                if val is not None and day_key:
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["recovery_score"] = val
                continue

            # ------------------ GLUCOSE METRICS (FIXED) ------------------
            if typ == "glucose":
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Processing glucose metric: {obj}")
                # Handle both individual values and time series
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                        print(f"DEBUG: Adding glucose to recovery_by_day[{day_key}]: {val}")
                    # This is a daily average
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["average_glucose"] = val

                # Handle minute-level series if enabled
                if self.store_minute_series:
                    vals = obj.get("values") or []
                    for v in vals:
                        if not v or v.get("value") is None or v.get("timestamp") is None:
                            continue
                        ts = ts_iso(v.get("timestamp"))
                        num = _num(v.get("value"))
                        if ts and num is not None:
                            out["series"].append({
                                "metric_type": "glucose_mgdl",
                                "timestamp": ts,
                                "value": num,
                                "unit": "mg/dL"
                            })
                continue

            # ------------------ INDIVIDUAL GLUCOSE METRICS ------------------
            if typ == "average_glucose":
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Processing average_glucose: {obj}")
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                        print(f"DEBUG: Adding average_glucose to recovery_by_day[{day_key}]: {val}")
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["average_glucose"] = val
                continue

            if typ == "glucose_variability":
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Processing glucose_variability: {obj}")
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                        print(f"DEBUG: Adding glucose_variability to recovery_by_day[{day_key}]: {val}")
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["glucose_variability"] = val
                continue

            if typ == "metabolic_score":
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Processing metabolic_score: {obj}")
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                        print(f"DEBUG: Adding metabolic_score to recovery_by_day[{day_key}]: {val}")
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["metabolic_score"] = val
                continue

            if typ == "hba1c":
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Processing hba1c: {obj}")
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                        print(f"DEBUG: Adding hba1c to recovery_by_day[{day_key}]: {val}")
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["hba1c"] = val
                continue

            if typ == "time_in_target":
                if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                    print(f"DEBUG: Processing time_in_target: {obj}")
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                        print(f"DEBUG: Adding time_in_target to recovery_by_day[{day_key}]: {val}")
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["time_in_target"] = val
                continue

            if typ == "movement_index":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["movement_index"] = val
                continue

            if typ == "vo2_max":
                val = _num(obj.get("value"))
                if val is not None and day_key:
                    if day_key not in recovery_by_day:
                        recovery_by_day[day_key] = {"date": day_key}
                    recovery_by_day[day_key]["vo2_max"] = val
                continue

            # ------------------ HEART RATE (FIXED) ------------------
            if typ == "hr":
                # Handle minute-level series if enabled
                if self.store_minute_series:
                    vals = obj.get("values") or []
                    for v in vals:
                        if not v or v.get("value") is None or v.get("timestamp") is None:
                            continue
                        ts = ts_iso(v.get("timestamp"))
                        num = _num(v.get("value"))
                        if ts and num is not None:
                            out["series"].append({
                                "metric_type": "heart_rate_minute",
                                "timestamp": ts,
                                "value": num,
                                "unit": "bpm"
                            })
                continue

        # Add all recovery metrics grouped by day
        if os.getenv("ULTRAHUMAN_DEBUG") == "1":
            print(f"DEBUG: recovery_by_day contains: {recovery_by_day}")
        for day_data in recovery_by_day.values():
            if len(day_data) > 1:  # More than just the date key
                out["recovery"].append(day_data)

        # Final debug output
        if os.getenv("ULTRAHUMAN_DEBUG") == "1":
            print(f"DEBUG: Final output summary:")
            for category, items in out.items():
                print(f"  {category}: {len(items)} items")
                if items:
                    print(f"    Sample: {items[0] if items else 'None'}")

        return out

    def _map_partner_legacy_like(self, payload: Dict) -> Dict[str, List[dict]]:
        """Best-effort mapping for older/alternate shapes."""
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

        return out

    # --------------------------- processing ---------------------------

    def process_ultrahuman_data(self, user_id: str, raw_data: Dict) -> Dict:
        """Process and normalize raw Ultrahuman data"""
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
        """Get list of available metrics for a user with data availability info"""
        try:
            from app.models import Metric
            from datetime import datetime, timedelta

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days_back)

            # Get available metrics with counts
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
        """Process HRV data point"""
        try:
            metrics: List[Dict] = []
            timestamp = self._parse_timestamp(data_point.get("timestamp"))

            # daily RMSSD
            if "rmssd" in data_point:
                val = self._to_float(data_point.get("rmssd"))
                if val is not None:
                    metrics.append({
                        "user_id": user_id, "metric_type": "hrv", "value": val,
                        "unit": "ms", "timestamp": timestamp, "source": "ultrahuman",
                        "meta_data": {"raw_data": data_point, "context": "daily"}
                    })

            # sleep average RMSSD (kept separate to avoid unique key clashes)
            if "sleep_rmssd" in data_point:
                val = self._to_float(data_point.get("sleep_rmssd"))
                if val is not None:
                    metrics.append({
                        "user_id": user_id, "metric_type": "hrv_sleep", "value": val,
                        "unit": "ms", "timestamp": timestamp, "source": "ultrahuman",
                        "meta_data": {"raw_data": data_point, "context": "sleep_avg"}
                    })

            # optional extras
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
        """Process sleep data point (daily summary)."""
        try:
            if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                print(f"DEBUG: Processing sleep data: {data_point}")

            metrics = []
            timestamp = self._parse_timestamp(data_point.get('bedtime'))

            # Sleep score
            v = self._to_float(data_point.get('sleep_score'))
            if v is not None:
                metrics.append({
                    'user_id': user_id,
                    'metric_type': 'sleep_score',
                    'value': v,
                    'unit': 'score',
                    'timestamp': timestamp,
                    'source': 'ultrahuman',
                    'meta_data': {
                        'raw_data': data_point,
                        'total_sleep_time': data_point.get('total_sleep_time'),
                        'sleep_efficiency': data_point.get('sleep_efficiency'),
                        'wake_after_sleep_onset': data_point.get('waso')
                    }
                })

            # Sleep efficiency
            v = self._to_float(data_point.get('sleep_efficiency'))
            if v is not None:
                metrics.append({
                    'user_id': user_id,
                    'metric_type': 'sleep_efficiency',
                    'value': v,
                    'unit': 'percent',
                    'timestamp': timestamp,
                    'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })

            # Deep sleep percentage
            total_sleep = self._to_float(data_point.get('total_sleep_time'))
            deep_minutes = self._to_float(data_point.get('deep_sleep_minutes'))
            if total_sleep and deep_minutes is not None and total_sleep > 0:
                deep_sleep_pct = (deep_minutes / total_sleep) * 100.0
                metrics.append({
                    'user_id': user_id,
                    'metric_type': 'deep_sleep_percentage',
                    'value': float(deep_sleep_pct),
                    'unit': 'percent',
                    'timestamp': timestamp,
                    'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })

            # REM sleep percentage
            rem_minutes = self._to_float(data_point.get('rem_sleep_minutes'))
            if total_sleep and rem_minutes is not None and total_sleep > 0:
                rem_sleep_pct = (rem_minutes / total_sleep) * 100.0
                metrics.append({
                    'user_id': user_id,
                    'metric_type': 'rem_sleep_percentage',
                    'value': float(rem_sleep_pct),
                    'unit': 'percent',
                    'timestamp': timestamp,
                    'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })

            if os.getenv("ULTRAHUMAN_DEBUG") == "1":
                print(f"DEBUG: Sleep processing created {len(metrics)} metrics")

            return metrics

        except Exception as e:
            logger.warning(f"Sleep data processing failed: {str(e)}")
            return []

    def _process_activity_data(self, user_id: str, data_point: Dict) -> List[Dict]:
        """Process activity data point."""
        try:
            metrics = []
            timestamp = self._parse_timestamp(data_point.get('date'))

            # Steps
            v = self._to_float(data_point.get('steps'))
            if v is not None:
                metrics.append({
                    'user_id': user_id,
                    'metric_type': 'steps',
                    'value': v,
                    'unit': 'count',
                    'timestamp': timestamp,
                    'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })

            # Calories burned
            v = self._to_float(data_point.get('calories_burned'))
            if v is not None:
                metrics.append({
                    'user_id': user_id,
                    'metric_type': 'calories_burned',
                    'value': v,
                    'unit': 'calories',
                    'timestamp': timestamp,
                    'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })

            # Active minutes
            v = self._to_float(data_point.get('active_minutes'))
            if v is not None:
                metrics.append({
                    'user_id': user_id,
                    'metric_type': 'active_minutes',
                    'value': v,
                    'unit': 'minutes',
                    'timestamp': timestamp,
                    'source': 'ultrahuman',
                    'meta_data': {'raw_data': data_point}
                })

            return metrics

        except Exception as e:
            logger.warning(f"Activity data processing failed: {str(e)}")
            return []

    def _process_recovery_data(self, user_id: str, data_point: Dict) -> List[Dict]:
        if os.getenv("ULTRAHUMAN_DEBUG") == "1":
            print(f"DEBUG: Processing recovery data: {data_point}")
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

            # Optional extras if present
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
        """Process per-minute series rows (hr, glucose)."""
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

            metrics = self._process_lifestyle_event(user_id, event_type, details, timestamp)
            if metrics:
                if bulk_insert_metrics(metrics):
                    self._update_metrics_cache(user_id, metrics)
                    return {"success": True, "event_type": event_type, "metrics_created": len(metrics), "timestamp": timestamp.isoformat()}
                return {"error": "Failed to store lifestyle event"}
            return {"error": "Failed to process lifestyle event"}
        except Exception as e:
            logger.error(f"Lifestyle event logging failed: {str(e)}")
            return {"error": str(e)}

    def _process_lifestyle_event(self, user_id: str, event_type: str, details: Dict, timestamp: datetime) -> List[Dict]:
        try:
            metrics: List[Dict] = []
            if event_type == "meal":
                metrics.append({
                    "user_id": user_id, "metric_type": "meal_timing",
                    "value": timestamp.hour + timestamp.minute/60.0, "unit": "hour_of_day",
                    "timestamp": timestamp, "source": "user_input",
                    "meta_data": {"event_type": "meal", "details": details, "parsed_from_sms": details.get("parsed_from_sms", False)}
                })
                if "estimated_calories" in details:
                    metrics.append({
                        "user_id": user_id, "metric_type": "calorie_intake", "value": float(details["estimated_calories"]),
                        "unit": "calories", "timestamp": timestamp, "source": "user_input",
                        "meta_data": {"event_type": "meal", "details": details}
                    })
            elif event_type == "supplement":
                metrics.append({
                    "user_id": user_id, "metric_type": "supplement_intake", "value": 1.0,
                    "unit": "boolean", "timestamp": timestamp, "source": "user_input",
                    "meta_data": {"event_type": "supplement", "details": details,
                                  "supplement_name": details.get("name", "unknown"),
                                  "dosage": details.get("dosage", "unknown")}
                })
            elif event_type == "activity":
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
        """Get recent metrics with enhanced error handling and suggestions"""
        try:
            # First check what data is actually available
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

            # If specific metrics requested, check if they exist
            if metric_types:
                missing_metrics = [mt for mt in metric_types if mt not in available_metric_types]
                if missing_metrics:
                    return {
                        'error': f'Requested metrics not available: {missing_metrics}',
                        'available_metrics': available_metric_types,
                        'suggestion': f'Try requesting analysis with available metrics: {available_metric_types}',
                        'user_id': user_id
                    }

            # Continue with the existing logic but use available metrics
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

            # Process the data as before
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

            # Add metadata about what was found vs requested
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
        """Validate metric data before processing"""
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