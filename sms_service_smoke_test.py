# sms_service_smoke_test.py
"""
Self-contained smoke tests for sms_service.py
- No pytest needed
- Mocks Twilio client (no real SMS)
- Bypasses Redis rate limits
- Uses in-memory SQLite and real app context
Run:
    cd /home/bphlite/ultrahuman_agent
    source venv/bin/activate
    python sms_service_smoke_test.py
"""

import os
import sys
from types import SimpleNamespace

# --- Environment setup ---
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC_TEST")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "tok_TEST")
os.environ.setdefault("TWILIO_PHONE_NUMBER", "+15005550006")  # Twilio test shape
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.pop("REDIS_URL", None)  # force cache fallback; avoids external Redis

# --- Import app & modules with flexible paths ---
APP_IMPORTED = False
errors = []

# Try modern package layout first
try:
    from ultrahuman_agent import create_app
    from ultrahuman_agent.utils.database import db
    from ultrahuman_agent.models import User, SystemLog
    import ultrahuman_agent.services.sms_service as sms_mod
    APP_IMPORTED = True
except Exception as e:
    errors.append(("ultrahuman_agent.*", e))

if not APP_IMPORTED:
    # Add parent to sys.path and try again
    here = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(here)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    try:
        from ultrahuman_agent import create_app
        from ultrahuman_agent.utils.database import db
        from ultrahuman_agent.models import User, SystemLog
        import ultrahuman_agent.services.sms_service as sms_mod
        APP_IMPORTED = True
    except Exception as e:
        errors.append(("sys.path+ultrahuman_agent.*", e))

if not APP_IMPORTED:
    # Legacy layout fallback
    try:
        from app import create_app  # type: ignore
        from utils.database import db  # type: ignore
        from app.models import User, SystemLog  # type: ignore
        import services.sms_service as sms_mod  # type: ignore
        APP_IMPORTED = True
    except Exception as e:
        errors.append(("legacy app/utils/services", e))
        print("❌ Import failed; errors:", errors)
        sys.exit(1)

# --- Fake Twilio client (no real sends) ---
class _FakeTwilioMessage:
    def __init__(self, sid="SM_FAKE_SID", status="sent"):
        self.sid = sid
        self.status = status
        self.error_code = None
        self.error_message = None
        self.date_sent = None
        self.date_updated = None
        self.price = None
        self.price_unit = None

class _FakeMessagesAPI:
    def create(self, body, from_, to):
        return _FakeTwilioMessage()

    # support .messages(message_id).fetch()
    def __call__(self, message_id):
        class _Fetcher:
            def fetch(self_inner):
                return _FakeTwilioMessage(sid=message_id, status="delivered")
        return _Fetcher()

class _FakeAccountsAPI:
    def __init__(self, sid): self.sid = sid
    def fetch(self):
        return SimpleNamespace(status="active", friendly_name="Test Account")

class _FakeAPI:
    def accounts(self, sid): return _FakeAccountsAPI(sid)

class _FakeTwilioClient:
    def __init__(self, sid, token):
        self.messages = _FakeMessagesAPI()
        self.api = _FakeAPI()

# Monkeypatch symbols where sms_service imports them
sms_mod.Client = _FakeTwilioClient

# Bypass Redis-based rate limiter
class _FakeRateLimiter:
    @staticmethod
    def is_allowed(key, limit, window): return True
    @staticmethod
    def get_remaining(key, limit): return max(0, limit - 1)

sms_mod.RateLimiter = _FakeRateLimiter

# --- Build app + DB ---
app = create_app("testing")
app.app_context().push()
db.create_all()

# Seed a sample user
if not User.query.get("u1"):
    u = User(id="u1", ultrahuman_user_id="uh_u1",
             phone_number="+15875452951", timezone="UTC",
             preferences={"test_user": True})
    db.session.add(u); db.session.commit()

# Instance
SMSService = sms_mod.SMSService
svc = SMSService()

def ok(label):
    print(f"✅ {label}")

def bad(label, err):
    print(f"❌ {label}: {err}")

# --- Tests ---

# 1) send_sms success
try:
    res = svc.send_sms("u1", "+1 (587) 545-2951", "Hello from smoke test!")
    assert res["success"] is True and res["message_id"]
    ok("send_sms success")
except Exception as e:
    bad("send_sms success", e)

# 2) invalid phone
try:
    res = svc.send_sms("u1", "123", "Invalid phone")
    assert res["success"] is False and "Invalid phone number" in res["error"]
    ok("invalid phone handled")
except Exception as e:
    bad("invalid phone handled", e)

# 3) urgent alert bypass
try:
    out = svc.send_alert("u1", "+15875452951", "HRV dropped vs 7-day avg.", severity="high")
    assert out["success"] is True
    ok("urgent alert bypass")
except Exception as e:
    bad("urgent alert bypass", e)

# 4) bulk send
try:
    res = svc.bulk_send_daily_reports([
        {"user_id": "u1", "phone_number": "+15875452951", "message": "Report A"},
        {"user_id": "u1", "phone_number": "+15875452951", "message": "Report B"},
    ])
    assert res["total_users"] == 2 and res["successful_sends"] == 2
    ok("bulk send")
except Exception as e:
    bad("bulk send", e)

# 5) delivery status
try:
    status = svc.get_delivery_status("SM_FAKE_123")
    assert status and status["message_id"] == "SM_FAKE_123" and status["status"] in {"delivered", "sent", "queued"}
    ok("get_delivery_status")
except Exception as e:
    bad("get_delivery_status", e)

# 6) connectivity + health
try:
    conn = svc.test_connectivity()
    assert conn.get("success") is True
    health = svc.get_service_health()
    assert health["service_name"] == "SMS Service"
    ok("connectivity + health")
except Exception as e:
    bad("connectivity + health", e)

# 7) SystemLog entries exist
try:
    logs = SystemLog.query.filter(SystemLog.user_id == "u1").all()
    assert len(logs) >= 1
    ok("SystemLog entries created")
except Exception as e:
    bad("SystemLog entries created", e)

print("\nDone.")
