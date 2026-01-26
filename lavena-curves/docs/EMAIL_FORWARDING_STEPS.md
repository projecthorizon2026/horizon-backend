# Lumière Curves - Email Forwarding Setup
## Forward ashjad@lumierecurves.shop → ashjadmm@gmail.com

---

## STEP 1: Create Business Email in Hostinger

1. Log into [Hostinger](https://www.hostinger.com)
   - Email: `lumierecurves@proton.me`
   - Password: `curves$2026`

2. Go to **Emails** → **Email Accounts**

3. Click **Create Email Account**
   - Email: `ashjad@lumierecurves.shop`
   - Password: Create a strong password (save it!)

4. Click **Create**

---

## STEP 2: Set Up Forwarding in Hostinger

1. In Hostinger Email section, find `ashjad@lumierecurves.shop`

2. Click **Manage** → **Forwarding** (or **Email Forwarding**)

3. Add forwarding rule:
   - Forward to: `ashjadmm@gmail.com`
   - Keep copy: Yes (recommended)

4. Save settings

---

## STEP 3: Test Forwarding

1. Send a test email TO: `ashjad@lumierecurves.shop`
2. Check if it arrives at `ashjadmm@gmail.com`
3. ✅ If received, forwarding works!

---

## STEP 4: Gmail "Send As" Setup

This lets you SEND emails FROM `ashjad@lumierecurves.shop` using Gmail.

### Get SMTP Settings from Hostinger:

| Setting | Value |
|---------|-------|
| SMTP Server | `smtp.hostinger.com` |
| Port | 465 (SSL) or 587 (TLS) |
| Username | `ashjad@lumierecurves.shop` |
| Password | [Your email password] |

### Add to Gmail:

1. Open Gmail → ⚙️ Settings → **See all settings**

2. Go to **Accounts and Import** tab

3. Find **"Send mail as:"** → Click **"Add another email address"**

4. Enter:
   ```
   Name: Ashjad - Lumière Curves
   Email: ashjad@lumierecurves.shop
   ☑️ Treat as an alias
   ```
   Click **Next**

5. Enter SMTP settings:
   ```
   SMTP Server: smtp.hostinger.com
   Port: 587
   Username: ashjad@lumierecurves.shop
   Password: [Your Hostinger email password]
   ☑️ Secured connection using TLS
   ```
   Click **Add Account**

6. Gmail sends confirmation to `ashjad@lumierecurves.shop`
   - This forwards to your Gmail!
   - Click the confirmation link or enter code

7. Done! ✅

---

## STEP 5: Set as Default (Optional)

1. Gmail → Settings → Accounts and Import
2. Under "Send mail as:" → Click **"make default"** next to business email
3. Now all emails send from `ashjad@lumierecurves.shop`

---

## CREDENTIALS TO SAVE

```
BUSINESS EMAIL
Email: ashjad@lumierecurves.shop
Password: ____________________
SMTP: smtp.hostinger.com:587
IMAP: imap.hostinger.com:993
```

---

## QUICK TEST CHECKLIST

- [ ] Created ashjad@lumierecurves.shop in Hostinger
- [ ] Forwarding to ashjadmm@gmail.com works
- [ ] Gmail "Send As" configured
- [ ] Can send AND receive from Gmail

---

*Questions? Reply to this email!*
