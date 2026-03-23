"""
notifications.py — all email sending logic lives here.

Every function:
1. Loads current SystemSettings
2. Checks if email is enabled + the relevant toggle
3. Builds the email using Django's EmailMessage
4. Sends via a dynamically-configured SMTP backend
5. Never raises — logs failures silently so a bad email config
   never breaks a payment transaction.
"""
import logging
from django.core.mail import EmailMessage
from django.core.mail.backends.smtp import EmailBackend

logger = logging.getLogger(__name__)


def _get_backend(s):
    """Build an SMTP backend from SystemSettings."""
    return EmailBackend(
        host=s.smtp_host,
        port=s.smtp_port,
        username=s.smtp_username,
        password=s.smtp_password,
        use_tls=s.smtp_use_tls,
        fail_silently=False,
    )


def _send(subject, body_html, recipient_list, s):
    """Core send helper. Returns True on success, False on failure."""
    if not s.email_enabled:
        logger.info('Email disabled — skipping: %s', subject)
        return False
    if not recipient_list:
        logger.warning('No recipients for: %s', subject)
        return False
    try:
        backend = _get_backend(s)
        msg = EmailMessage(
            subject=subject,
            body=body_html,
            from_email=s.email_from or s.smtp_username,
            to=recipient_list,
            connection=backend,
        )
        msg.content_subtype = 'html'
        msg.send()
        logger.info('Email sent: %s → %s', subject, recipient_list)
        return True
    except Exception as exc:
        logger.error('Email failed (%s): %s', subject, exc)
        return False


def _base_style():
    return """
    <style>
      body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 20px; }
      .wrap { max-width: 600px; margin: 0 auto; background: #fff;
              border-radius: 10px; overflow: hidden;
              border: 1px solid #e5e7eb; }
      .header { background: #0f1923; color: #fff; padding: 20px 28px; }
      .header h1 { margin: 0; font-size: 18px; }
      .header p  { margin: 4px 0 0; font-size: 12px; color: #9ca3af; }
      .body  { padding: 24px 28px; }
      .kpi-row { display: flex; gap: 12px; margin: 16px 0; }
      .kpi { flex: 1; background: #f9fafb; border: 1px solid #e5e7eb;
             border-radius: 8px; padding: 12px 16px; }
      .kpi .label { font-size: 11px; color: #6b7280; font-weight: bold;
                    text-transform: uppercase; }
      .kpi .value { font-size: 20px; font-weight: 700; color: #111827; margin-top: 4px; }
      .kpi.green .value { color: #16a34a; }
      .kpi.red   .value { color: #dc2626; }
      table { width: 100%; border-collapse: collapse; margin: 12px 0; }
      th { background: #0f1923; color: #fff; padding: 8px 12px;
           font-size: 11px; text-align: left; }
      td { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; font-size: 13px; }
      tr:last-child td { border-bottom: none; }
      .alert { padding: 14px 18px; border-radius: 8px; margin: 16px 0;
               font-size: 14px; font-weight: 500; }
      .alert-red    { background: #fee2e2; color: #991b1b; border-left: 4px solid #ef4444; }
      .alert-yellow { background: #fef3c7; color: #92400e; border-left: 4px solid #f59e0b; }
      .alert-green  { background: #d1fae5; color: #065f46; border-left: 4px solid #16a34a; }
      .footer { background: #f9fafb; padding: 14px 28px; font-size: 11px;
                color: #9ca3af; border-top: 1px solid #e5e7eb; }
      a { color: #0d6efd; }
    </style>"""


# ── 1. Void Request Notification ─────────────────────────────

def send_void_request(payment, requested_by):
    """Sent to admin/manager when a teller requests a void."""
    from settings_app.models import SystemSettings
    s = SystemSettings.get()
    if not s.notify_void_request:
        return False

    subject = f'[{s.business_name}] Void Request — {payment.txn_number}'
    body = f"""{_base_style()}
    <div class="wrap">
      <div class="header">
        <h1>⚡ {s.business_name}</h1>
        <p>Void Request Alert</p>
      </div>
      <div class="body">
        <div class="alert alert-yellow">
          ⚠ A teller has requested to void a transaction. Please review and approve or reject.
        </div>
        <table>
          <tr><th colspan="2">Transaction Details</th></tr>
          <tr><td><strong>Ref #</strong></td><td>{payment.txn_number}</td></tr>
          <tr><td><strong>Biller</strong></td><td>{payment.biller_name}</td></tr>
          <tr><td><strong>Account</strong></td><td>{payment.biller_account_number}</td></tr>
          <tr><td><strong>Amount</strong></td><td>₱{payment.total_due:,.2f}</td></tr>
          <tr><td><strong>Date</strong></td>
              <td>{payment.created_at.strftime('%B %d, %Y %I:%M %p')}</td></tr>
          <tr><td><strong>Requested by</strong></td>
              <td>{requested_by.get_full_name() or requested_by.username}</td></tr>
          <tr><td><strong>Reason</strong></td><td>{payment.void_reason or '—'}</td></tr>
        </table>
        <p style="font-size:13px;color:#6b7280;">
          Please log in to the system to approve or reject this void request.
        </p>
      </div>
      <div class="footer">{s.business_name} · Internal Monitoring System · Do not reply</div>
    </div>"""

    return _send(subject, body, s.get_admin_emails(), s)


# ── 2. EOD Shortage Alert ────────────────────────────────────

def send_eod_shortage(eod, closed_by):
    """Sent when EOD is closed with a shortage (negative discrepancy)."""
    from settings_app.models import SystemSettings
    s = SystemSettings.get()
    if not s.notify_eod_shortage:
        return False
    if eod.discrepancy >= 0:
        return False  # No shortage, no alert

    shortage = abs(eod.discrepancy)
    subject = f'[{s.business_name}] ⚠ Cash Shortage Detected — {eod.date}'
    body = f"""{_base_style()}
    <div class="wrap">
      <div class="header">
        <h1>⚡ {s.business_name}</h1>
        <p>EOD Shortage Alert — {eod.date.strftime('%B %d, %Y')}</p>
      </div>
      <div class="body">
        <div class="alert alert-red">
          ⚠ A cash shortage of <strong>₱{shortage:,.2f}</strong> was detected
          during end-of-day reconciliation.
        </div>
        <div class="kpi-row">
          <div class="kpi">
            <div class="label">Expected Cash</div>
            <div class="value">₱{eod.total_collected:,.2f}</div>
          </div>
          <div class="kpi">
            <div class="label">Declared Cash</div>
            <div class="value">₱{eod.declared_cash:,.2f}</div>
          </div>
          <div class="kpi red">
            <div class="label">Shortage</div>
            <div class="value">₱{shortage:,.2f}</div>
          </div>
        </div>
        <table>
          <tr><th colspan="2">EOD Summary — {eod.date}</th></tr>
          <tr><td>Transactions</td><td>{eod.total_transactions}</td></tr>
          <tr><td>Total Collected</td><td>₱{eod.total_collected:,.2f}</td></tr>
          <tr><td>Service Fees</td><td>₱{eod.total_service_fees:,.2f}</td></tr>
          <tr><td>LEYECO Remittance</td><td>₱{eod.total_bill_amount:,.2f}</td></tr>
          <tr><td>Closed By</td>
              <td>{closed_by.get_full_name() or closed_by.username}</td></tr>
          <tr><td>Notes</td><td>{eod.notes or '—'}</td></tr>
        </table>
        <p style="font-size:13px;color:#6b7280;">
          Please investigate immediately. Check the audit log for details.
        </p>
      </div>
      <div class="footer">{s.business_name} · Internal Monitoring System · Do not reply</div>
    </div>"""

    return _send(subject, body, s.get_admin_emails(), s)


# ── 3. Daily Summary Email ───────────────────────────────────

def send_daily_summary(eod, teller_rows, closed_by):
    """Full day summary sent when EOD is closed."""
    from settings_app.models import SystemSettings
    s = SystemSettings.get()
    if not s.notify_daily_summary:
        return False

    teller_html = ''
    for t in teller_rows:
        teller_html += f"""
        <tr>
          <td>{t['teller_name']}</td>
          <td style="text-align:right;">{t['count']}</td>
          <td style="text-align:right;">₱{t['total_collected']:,.2f}</td>
          <td style="text-align:right;color:#16a34a;">₱{t['total_fees']:,.2f}</td>
        </tr>"""

    disc_class = 'green' if eod.discrepancy >= 0 else 'red'
    disc_label = 'Overage' if eod.discrepancy > 0 else ('Balanced ✓' if eod.discrepancy == 0 else 'Shortage ⚠')
    disc_sign  = '+' if eod.discrepancy > 0 else ''

    subject = f'[{s.business_name}] Daily Summary — {eod.date}'
    body = f"""{_base_style()}
    <div class="wrap">
      <div class="header">
        <h1>⚡ {s.business_name}</h1>
        <p>Daily Summary — {eod.date.strftime('%B %d, %Y')}</p>
      </div>
      <div class="body">
        <div class="kpi-row">
          <div class="kpi">
            <div class="label">Transactions</div>
            <div class="value">{eod.total_transactions}</div>
          </div>
          <div class="kpi">
            <div class="label">Total Collected</div>
            <div class="value">₱{eod.total_collected:,.2f}</div>
          </div>
          <div class="kpi green">
            <div class="label">Service Fees</div>
            <div class="value">₱{eod.total_service_fees:,.2f}</div>
          </div>
          <div class="kpi {disc_class}">
            <div class="label">{disc_label}</div>
            <div class="value">{disc_sign}₱{abs(eod.discrepancy):,.2f}</div>
          </div>
        </div>

        <table>
          <tr>
            <th>Teller</th>
            <th style="text-align:right;">Transactions</th>
            <th style="text-align:right;">Collected</th>
            <th style="text-align:right;">Fees</th>
          </tr>
          {teller_html if teller_html else '<tr><td colspan="4" style="color:#9ca3af;">No teller data</td></tr>'}
        </table>

        <table>
          <tr><th colspan="2">Financial Summary</th></tr>
          <tr><td>Total Collected</td><td style="text-align:right;">₱{eod.total_collected:,.2f}</td></tr>
          <tr><td>LEYECO Remittance</td>
              <td style="text-align:right;">₱{eod.total_bill_amount:,.2f}</td></tr>
          <tr><td>Service Fee Income</td>
              <td style="text-align:right;color:#16a34a;">₱{eod.total_service_fees:,.2f}</td></tr>
          <tr><td>Declared Cash</td>
              <td style="text-align:right;">₱{eod.declared_cash:,.2f}</td></tr>
          <tr><td><strong>Discrepancy</strong></td>
              <td style="text-align:right;font-weight:700;
                color:{'#16a34a' if eod.discrepancy >= 0 else '#dc2626'};">
                {disc_sign}₱{abs(eod.discrepancy):,.2f}</td></tr>
        </table>
      </div>
      <div class="footer">
        Closed by {closed_by.get_full_name() or closed_by.username} ·
        {s.business_name} · Do not reply
      </div>
    </div>"""

    return _send(subject, body, s.get_admin_emails(), s)


# ── 4. Welcome Email for New Users ──────────────────────────

def send_welcome_email(new_user, plain_password):
    """Sent to new user when admin creates their account."""
    from settings_app.models import SystemSettings
    s = SystemSettings.get()
    if not s.notify_new_user:
        return False
    if not new_user.email:
        return False

    subject = f'Welcome to {s.business_name} — Your Account is Ready'
    body = f"""{_base_style()}
    <div class="wrap">
      <div class="header">
        <h1>⚡ {s.business_name}</h1>
        <p>Your account has been created</p>
      </div>
      <div class="body">
        <p style="font-size:15px;">
          Hi <strong>{new_user.get_full_name() or new_user.username}</strong>,
        </p>
        <p style="font-size:13px;color:#374151;">
          Your account for the {s.business_name} Payment Monitoring System
          has been created. Here are your login credentials:
        </p>
        <table>
          <tr><th colspan="2">Login Credentials</th></tr>
          <tr><td><strong>Username</strong></td><td>{new_user.username}</td></tr>
          <tr><td><strong>Password</strong></td><td>{plain_password}</td></tr>
          <tr><td><strong>Role</strong></td><td>{new_user.get_role_display()}</td></tr>
          <tr><td><strong>Branch</strong></td><td>{new_user.branch or '—'}</td></tr>
        </table>
        <div class="alert alert-yellow">
          Please change your password after your first login.
        </div>
      </div>
      <div class="footer">{s.business_name} · Internal Monitoring System · Do not reply</div>
    </div>"""

    return _send(subject, body, [new_user.email], s)


# ── 5. Test Email ────────────────────────────────────────────

def send_test_email(recipient_email, s):
    """Sends a test email to verify SMTP settings are working."""
    subject = f'[{s.business_name}] Test Email — SMTP Configuration OK'
    body = f"""{_base_style()}
    <div class="wrap">
      <div class="header">
        <h1>⚡ {s.business_name}</h1>
        <p>SMTP Test</p>
      </div>
      <div class="body">
        <div class="alert alert-green">
          ✓ Your email settings are working correctly!
        </div>
        <p style="font-size:13px;color:#374151;">
          This is a test email from the {s.business_name} Payment Monitoring System.
          If you received this, your SMTP configuration is correct and email
          notifications are ready to use.
        </p>
        <table>
          <tr><th colspan="2">Current SMTP Settings</th></tr>
          <tr><td>Host</td><td>{s.smtp_host}:{s.smtp_port}</td></tr>
          <tr><td>Username</td><td>{s.smtp_username}</td></tr>
          <tr><td>TLS</td><td>{'Enabled' if s.smtp_use_tls else 'Disabled'}</td></tr>
        </table>
      </div>
      <div class="footer">{s.business_name} · Internal Monitoring System · Do not reply</div>
    </div>"""
    return _send(subject, body, [recipient_email], s)
