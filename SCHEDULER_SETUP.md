# 🚀 Smart Alarm - Complete Setup Guide

## Why Scheduler Doesn't Auto-Start

Django discourages database access during app initialization. Since the scheduler needs to load routines from the database, we **don't start it automatically** when Django starts.

Instead, you choose one of two methods:

---

## 📋 Setup Method Comparison

| Feature | Middleware | Separate Process |
|---------|-----------|-----------------|
| **Ease of Setup** | ⭐⭐⭐ Easy | ⭐⭐ Medium |
| **Production Ready** | ⭐⭐ | ⭐⭐⭐ |
| **Restart Handling** | Restarts with Django | Independent |
| **Debugging** | Logs in Django console | Own console output |
| **Best For** | Development | Production |

---

## Method 1: Middleware (Quick Start) 🏃

### When to Use
- ✅ Local development
- ✅ Quick testing
- ✅ Single-user setups
- ❌ Production (Method 2 is better)

### Setup Steps

**Step 1: Add Middleware**

Edit `config/settings.py` and add the middleware:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Add this line at the end:
    'alarm_app.middleware.SchedulerMiddleware',
]
```

**Step 2: Start Django**

```bash
python manage.py runserver
```

**Step 3: Trigger Scheduler**

Visit any page in your browser:
```
http://localhost:8000/
```

The scheduler starts automatically on the first request.

**Step 4: Verify**

```bash
python manage.py check_scheduler
```

Should show:
```
✓ Scheduler is RUNNING
✓ Scheduled Jobs: X
```

### Advantages
- ✅ Easy setup (just one line in settings)
- ✅ Starts automatically
- ✅ No extra terminal needed

### Disadvantages
- ⚠️ Stops when Django stops
- ⚠️ Restarts when Django reloads (in DEBUG mode)
- ⚠️ Not ideal for production

---

## Method 2: Separate Process (Recommended) ⭐

### When to Use
- ✅ Production deployments
- ✅ Better control and monitoring
- ✅ Independent scheduler management
- ✅ When you want scheduler to stay running even if Django restarts

### Setup Steps

**Step 1: Start Django (Terminal 1)**

```bash
# Terminal 1 - Django Web Server
python manage.py runserver
```

Leave this running.

**Step 2: Start Scheduler (Terminal 2)**

```bash
# Terminal 2 - Scheduler Process
python manage.py run_scheduler
```

You should see:
```
Starting scheduler...
✓ Scheduler started successfully
✓ Loaded 3 scheduled job(s)

Scheduled jobs:
  - routine_1: Next run at 2024-11-02 07:00:00
  - routine_2: Next run at 2024-11-02 18:00:00
  - routine_3: Next run at 2024-11-02 20:00:00

Scheduler is running. Press Ctrl+C to stop.
```

**Step 3: Verify (Terminal 3)**

```bash
# Terminal 3 - Verification
python manage.py check_scheduler
```

Should show:
```
✓ Scheduler is RUNNING
✓ Scheduled Jobs: 3
```

### Advantages
- ✅ **Production-ready**
- ✅ Independent of Django web server
- ✅ Can restart Django without affecting scheduler
- ✅ Clear scheduler output in its own terminal
- ✅ Better monitoring and logging

### Disadvantages
- ⚠️ Requires two terminals (or process manager in production)
- ⚠️ Slightly more complex setup

---

## Production Deployment

### Using systemd (Linux)

Create two service files:

**1. Django Web Service: `/etc/systemd/system/smart-alarm-web.service`**

```ini
[Unit]
Description=Smart Alarm Django Web Server
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Scheduler Service: `/etc/systemd/system/smart-alarm-scheduler.service`**

```ini
[Unit]
Description=Smart Alarm Scheduler
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python manage.py run_scheduler
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable and start both:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable smart-alarm-web
sudo systemctl enable smart-alarm-scheduler
sudo systemctl start smart-alarm-web
sudo systemctl start smart-alarm-scheduler
sudo systemctl status smart-alarm-web
sudo systemctl status smart-alarm-scheduler
```

### Using Supervisor

**Configuration: `/etc/supervisor/conf.d/smart-alarm.conf`**

```ini
[program:smart-alarm-web]
command=/path/to/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000
directory=/path/to/project
user=youruser
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/smart-alarm-web.log

[program:smart-alarm-scheduler]
command=/path/to/venv/bin/python manage.py run_scheduler
directory=/path/to/project
user=youruser
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/smart-alarm-scheduler.log
```

**Start:**

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start smart-alarm-web
sudo supervisorctl start smart-alarm-scheduler
sudo supervisorctl status
```

---

## Verifying Everything Works

### 1. Check Scheduler Status

```bash
python manage.py check_scheduler
```

**Good output:**
```
=== Scheduler Status ===
✓ Scheduler is RUNNING
✓ Scheduled Jobs: 3

Job Details:
  - routine_1
    Next Run: 2024-11-02 07:00:00
    Trigger: cron[day_of_week='mon,tue,wed,thu,fri', hour='7', minute='0']
```

**Bad output:**
```
✗ Scheduler is STOPPED
```
→ Go back and start the scheduler using Method 1 or 2

### 2. Create a Test Routine

1. Go to http://localhost:8000/routines/create/
2. Create a simple routine:
   - Name: "Test"
   - Schedule: Recurring, 2 minutes from now, Today only
   - Steps: Add one "Quote" step
3. Save and enable

### 3. Reload Schedules

```bash
python manage.py check_scheduler --reload
```

### 4. Wait and Watch

Check the scheduler terminal (if using Method 2) or Django console (if using Method 1).

After 2 minutes, you should see execution logs.

### 5. Verify in Web UI

Go to http://localhost:8000/ and check "Recent Activity" section.

---

## Common Issues & Quick Fixes

### Issue: "Scheduler is STOPPED"

**Fix:**
- Method 1: Add middleware to settings.py, restart Django, visit any page
- Method 2: Run `python manage.py run_scheduler` in separate terminal

### Issue: "No jobs scheduled"

**Fix:**
```bash
python manage.py check_scheduler --reload
```

### Issue: Database warnings

**Fix:** You're using the old apps.py. Make sure you've updated to the new version that doesn't start the scheduler in apps.py.

### Issue: Routines not executing

**Checklist:**
- [ ] Scheduler is running (check_scheduler shows RUNNING)
- [ ] Routine is enabled
- [ ] Schedule is valid (time + days for recurring, or future datetime for one-time)
- [ ] Routine has at least one step
- [ ] Schedules are loaded (run `check_scheduler --reload`)

---

## Monitoring and Logs

### View Scheduler Output (Method 2)

The scheduler terminal shows:
- Job executions
- Errors
- Schedule updates

### View Django Logs

```bash
# Terminal running Django server
# Shows web requests and middleware messages
```

### View Database Logs

```bash
python manage.py check_scheduler
# Shows recent execution history
```

### Enable Debug Logging

Add to `config/settings.py`:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'alarm_app': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'apscheduler': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

---

## Recommendations

### For Development
✅ **Use Method 1 (Middleware)**
- Quick and easy
- Restarts automatically
- Good enough for testing

### For Production
✅ **Use Method 2 (Separate Process)**
- Professional setup
- Better reliability
- Easier monitoring
- Industry standard

---

## Need Help?

1. Run: `python manage.py check_scheduler`
2. Read output for specific issues
3. Check `TROUBLESHOOTING.md` for detailed solutions
4. Use `QUICK_FIX.md` for common quick fixes

---

## Summary

```bash
# Development (Easy)
# 1. Add 'alarm_app.middleware.SchedulerMiddleware' to MIDDLEWARE in settings.py
# 2. python manage.py runserver
# 3. Visit http://localhost:8000/

# Production (Recommended)
# Terminal 1: python manage.py runserver
# Terminal 2: python manage.py run_scheduler
```

That's it! Your scheduler is now running properly. 🎉
