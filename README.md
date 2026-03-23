# LEYECO Payment Monitor — v5 (Complete)

Internal electric bill payment tracking system for teller accountability.

## Quick Setup

```
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_demo
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Demo Credentials

| Role    | Username | Password   |
|---------|----------|------------|
| Admin   | admin    | admin123   |
| Manager | manager  | manager123 |
| Teller  | teller1  | teller123  |
| Teller  | teller2  | teller123  |

## Full Feature List (v1 through v5)

### Core Payment System
- New payment form with live denomination calculator
- Auto-compute service fee (configurable), total due, change
- Denomination breakdown validated against cash received
- Auto-generated transaction numbers (LECO-YYYYMMDD-NNNNN)
- Duplicate payment detection (warns if same account paid today)
- Void request workflow — teller requests, manager/admin approves
- Printable receipts with denomination breakdown
- Receipt reprint from any transaction detail page

### Transactions
- Full list with search, date/status filter, pagination (50/page)
- Transaction detail with audit history
- Biller history lookup — full payment history by account number

### Dashboard
- Today's KPIs (collected, fees, remittance, count)
- 30-day collections trend chart
- Per-teller activity summary (admin/manager)
- Open shift status banner for tellers

### Reports (Manager/Admin)
- Daily report — any date, with teller breakdown
- Date range report — chart + teller comparison + voids
- Advanced reports — monthly trend, peak hours, teller comparison, top billers
- EOD Reconciliation — declare cash, detect shortages, lock the day
- Shortage history — list of all EOD shortages ever recorded
- Export to Excel (3-sheet) and PDF

### Audit Log (Manager/Admin)
- Every action logged with user, timestamp, IP
- Filter by user, action, date, keyword
- Today's count pills per action type
- Export audit log to Excel

### Shift Management
- Teller opens/closes shift with opening and closing cash
- Live discrepancy calculator at shift close
- Shift history for managers

### User Management (Manager/Admin)
- Add, edit, activate/deactivate users
- Reset passwords
- Force password change on next login
- Profile page with personal stats for all users
- Change own password

### Email Notifications (Admin)
- Void request alert to admin/manager
- EOD shortage alert
- Daily summary email at EOD close
- Welcome email with credentials to new users
- Test email button to verify SMTP

### Settings (Admin)
- Business name, address, receipt footer
- Service fee amount (live — changes on next transaction)
- Gmail SMTP configuration
- Per-notification toggles

### Security
- Login lockout after 5 failed attempts (django-axes)
- Password policy — min 8 chars, no common passwords
- Force password change flag per user
- Session expires after 8 hours
- All actions logged with IP address
- Immutable audit log

### Backup & Export (Admin)
- Full ZIP backup: transactions, users, EOD, shifts, audit log as Excel files
- CSV export for date range (for accounting software)
- `python manage.py backup_now` for scheduled/automated backups

## URL Map

| URL | Description |
|-----|-------------|
| / | Dashboard |
| /transactions/ | Transaction list |
| /transactions/new/ | New payment |
| /transactions/biller/ | Biller history lookup |
| /reports/ | Reports hub |
| /reports/daily/ | Daily report |
| /reports/range/ | Date range report |
| /reports/advanced/ | Advanced analytics |
| /reports/eod/ | EOD reconciliation |
| /audit/ | Audit log |
| /shifts/ | Shift management |
| /accounts/profile/ | My profile |
| /accounts/users/ | User management |
| /settings/ | System settings |
| /backup/ | Backup & export |
| /admin/ | Django admin |

## Scheduled Backup (Windows Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 11:00 PM
4. Action: Start a program
   - Program: python.exe (full path)
   - Arguments: manage.py backup_now
   - Start in: C:\path\to\leyeco_monitor
5. Backups saved to: leyeco_monitor/backups/
