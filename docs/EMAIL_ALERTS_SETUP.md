# Periodic Gmail/email alerts

The product includes a working subscription endpoint and protected scheduler endpoint. To actually deliver email, configure one sender account once on the server.

## Gmail sender setup

1. Enable 2-Step Verification on the sender Google account.
2. In Google Account → Security → App passwords, create an app password for Smart Wealth Advisor.
3. Add these server-only values to `.env.local`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=sender@gmail.com
SMTP_PASS=the_16_character_app_password
NOTIFICATION_FROM="Smart Wealth Advisor <sender@gmail.com>"
DATABASE_URL=postgresql://wealth_app:change_me_in_production@localhost:5432/smart_wealth
CRON_SECRET=a_long_random_secret
```

Never use the normal Gmail password and never prefix secrets with `NEXT_PUBLIC_`.

## Scheduler

Call this endpoint daily from Vercel Cron, GitHub Actions, AWS EventBridge, Azure Scheduler, or another trusted scheduler:

```http
GET /api/cron/notifications
Authorization: Bearer <CRON_SECRET>
```

The route selects due subscriptions, sends messages, and computes the next delivery date from each user's daily, weekly, or monthly preference.

## User experience

Users click the bell in the header, enter their Gmail/email address, choose frequency, and activate alerts. The UI explicitly reports whether the schedule was persisted and whether SMTP delivery is configured.
