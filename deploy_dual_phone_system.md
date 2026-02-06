# Deploy Dual Phone System for Apostle Emmanuel

## **Summary: How It Works**

✅ **Notifications (daily reports, alerts) → PRIMARY phone only**
✅ **SMS responses → phone that sent the message**
✅ **Both phones can text and get responses**
✅ **All data attribution → same user (user_7000)**

---

## **Files to Upload to Production Server**

Upload these **5 files** to your PythonAnywhere server:

1. **app/__init__.py** (updated SMS webhook with dual phone authentication)
2. **services/sms_service.py** (notification routing to primary phone)
3. **add_emmanuel_phone.py** (add +15875452951)
4. **test_dual_phone_behavior.py** (comprehensive testing)
5. **test_sms_routing.py** (basic routing tests)

---

## **Deploy on Production Server**

### **1. Connect to PythonAnywhere**
```bash
# Via web console (recommended) or SSH
ssh bphlite@ssh.pythonanywhere.com
cd ultrahuman_agent
```

### **2. Backup Current Files**
```bash
# Backup in case we need to rollback
cp app/__init__.py app/__init__.py.backup
cp services/sms_service.py services/sms_service.py.backup
```

### **3. Upload Modified Files**
Upload the 5 files listed above to replace existing files.

### **4. Add +15875452951 to Apostle Emmanuel**
```bash
# Activate environment
source venv/bin/activate

# Add the new phone number
python add_emmanuel_phone.py
```

**Expected Output:**
```
============================================================
ADDING +15875452951 TO APOSTLE EMMANUEL
============================================================
Found user: user_7000 (Apostle Emmanuel)
Primary phone: [current_phone]

✅ Successfully added +15875452951 to user_7000 (Apostle Emmanuel)

📱 Apostle Emmanuel's authorized phone numbers:
   Primary: [current_phone]
   Additional 1: +15875452951

🎯 Total authorized phones: 2

✅ SMS Access for Apostle Emmanuel:
   Text from [current_phone] → access user_7000 data
   Text from +15875452951 → access user_7000 data
```

### **5. Test the System**
```bash
# Run comprehensive tests
python test_dual_phone_behavior.py
```

**Expected Output:**
```
DUAL PHONE BEHAVIOR TEST SUITE
Testing SMS routing for Apostle Emmanuel

✅ PASSED: Dual Phone Setup
✅ PASSED: SMS Routing Logic
✅ PASSED: Notification Routing
✅ PASSED: Real Scenarios

Results: 4/4 tests passed
🎉 All tests passed! Dual phone system is ready to deploy.
```

### **6. Restart Web App**
Go to your PythonAnywhere **Web** tab and click **"Reload"** to apply changes.

---

## **How The System Behaves**

### **📤 Outgoing Messages (System → User)**

| Message Type | Destination | Example |
|--------------|-------------|---------|
| Daily Reports (4 AM) | PRIMARY phone | "🏥 Your sleep score: 85/100..." |
| Health Alerts | PRIMARY phone | "⚠️ HRV anomaly detected..." |
| Critical Alerts | PRIMARY phone | "🆘 Critical pattern found..." |
| Intervention Updates | PRIMARY phone | "📈 Magnesium update: 15% improvement..." |

### **📱 Incoming Messages (User → System)**

| Sender Phone | Authentication | Response Destination | Data Attribution |
|--------------|----------------|---------------------|------------------|
| PRIMARY phone | ✅ Authenticated | PRIMARY phone | user_7000 |
| +15875452951 | ✅ Authenticated | +15875452951 | user_7000 |
| Unknown phone | ❌ Rejected | No response | N/A |

### **💬 Example SMS Flows**

**Scenario 1: Daily Report**
- **4:00 AM**: System generates daily report
- **Target**: PRIMARY phone only
- **Content**: "🏥 Sleep: 85/100, HRV trending up 12%..."

**Scenario 2: Text from PRIMARY phone**
- **User texts**: "meal chicken 7pm" from PRIMARY phone
- **System**: Logs meal for user_7000
- **Response to**: PRIMARY phone ("✅ Logged meal. Thanks!")

**Scenario 3: Text from +15875452951**
- **User texts**: "how am I doing?" from +15875452951
- **System**: Analyzes user_7000 data
- **Response to**: +15875452951 ("📊 HRV up 8%, sleep quality improving...")

**Scenario 4: Health Alert**
- **System**: Detects HRV anomaly in user_7000 data
- **Target**: PRIMARY phone only
- **Content**: "⚠️ HRV anomaly: 32ms (-2.1σ low). Monitor closely..."

---

## **Security & Data Access**

✅ **Phone Authentication**: Only registered phones can access data
✅ **Data Isolation**: All messages (both phones) access same user_7000 data
✅ **Notification Control**: Reports/alerts only go to primary phone
✅ **Response Routing**: SMS replies go back to sender
✅ **Rate Limiting**: 20 responses/hour, 25 total messages/day per user

---

## **Testing After Deployment**

### **Test 1: Phone Authentication**
```bash
python test_sms_routing.py
```

### **Test 2: Complete Behavior**
```bash
python test_dual_phone_behavior.py
```

### **Test 3: Live SMS Test**
1. **Text from PRIMARY**: "test message" → should get response to PRIMARY
2. **Text from +15875452951**: "test message" → should get response to +15875452951
3. **Wait for next daily report** → should go to PRIMARY only

---

## **Configuration Verification**

Check the user configuration:
```bash
python -c "
from app import create_app
from app.models import User
app = create_app()
with app.app_context():
    user = User.query.filter_by(id='user_7000').first()
    print('User:', user.id)
    print('Primary phone:', user.phone_number)
    additional = user.preferences.get('additional_phone_numbers', [])
    print('Additional phones:', additional)
    print('Total authorized phones:', 1 + len(additional))
"
```

**Expected Output:**
```
User: user_7000
Primary phone: [current_primary_phone]
Additional phones: ['+15875452951']
Total authorized phones: 2
```

---

## **Troubleshooting**

### **If SMS from +15875452951 is rejected:**
1. ✅ Verify phone was added: `python test_dual_phone_behavior.py`
2. ✅ Check web app was reloaded
3. ✅ Verify SMS webhook logs in PythonAnywhere error log

### **If responses go to wrong phone:**
1. ✅ Check SMS service logs for "Redirecting" messages
2. ✅ Verify `force_phone=True` for responses
3. ✅ Test with `test_dual_phone_behavior.py`

### **If daily reports go to additional phone:**
1. ❌ This is incorrect behavior
2. ✅ Check `get_primary_phone_for_user()` method
3. ✅ Verify `daily_reports` message type routing

### **To rollback if needed:**
```bash
# Restore backups
cp app/__init__.py.backup app/__init__.py
cp services/sms_service.py.backup services/sms_service.py

# Reload web app
```

---

## **Future Phone Management**

### **To add more phones:**
```bash
python add_phone_number.py
# Follow interactive prompts
```

### **To remove phones:**
Manually edit user preferences in database or create removal script.

### **To change primary phone:**
Update `user.phone_number` field (notifications will follow).

---

## **Final Checklist**

- [ ] Upload 5 files to production server
- [ ] Run `python add_emmanuel_phone.py`
- [ ] Run `python test_dual_phone_behavior.py` (4/4 tests pass)
- [ ] Reload PythonAnywhere web app
- [ ] Test with actual SMS from both phones
- [ ] Monitor next daily report (should go to primary only)

🎯 **Result**: Apostle Emmanuel can text from either phone and get responses, but all reports/alerts go to the primary phone only.