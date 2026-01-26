# Lumière Curves - Domain & Email Setup Guide
## Complete Step-by-Step Instructions

---

## PART 1: DOMAIN NAME OPTIONS

### Recommended Domain Names (.shop TLD)

| Domain | Availability | Why |
|--------|--------------|-----|
| **lumierecurves.shop** | Check | Primary choice, matches brand |
| **lumiere-curves.shop** | Check | Hyphenated alternative |
| **lumiercurves.shop** | Check | Simpler spelling |
| **thelumierecurves.shop** | Check | With "the" prefix |
| **shoplumiere.shop** | Check | Shop-focused |

### Alternative TLDs

| Domain | Best For |
|--------|----------|
| lumierecurves.com | Global credibility (if available) |
| lumierecurves.in | India market focus |
| lumierecurves.store | E-commerce focus |
| lumierecurves.co | Modern, short |

---

## PART 2: BUY DOMAIN ON NAMECHEAP

### Step 1: Search for Domain
1. Go to [namecheap.com](https://www.namecheap.com)
2. In the search bar, type: `lumierecurves.shop`
3. Click "Search"
4. If available, click "Add to Cart"

### Step 2: Choose Plan
**Recommended: Domain + Hosting Bundle**

| Option | Price (Est.) | Includes |
|--------|--------------|----------|
| Stellar Hosting (1 year) | $28.88/year | FREE .shop domain, 20GB SSD, 3 websites |
| Stellar Plus (1 year) | $44.88/year | FREE .shop domain, Unlimited SSD, Auto backup |

**Or just domain:**
- .shop domain only: ~$2.98/year (first year), ~$32/year renewal

### Step 3: Create Account
1. Click "Checkout"
2. Create account with:
   - Email: ashjadmm@gmail.com (or your preferred email)
   - Password: [Create strong password]
3. Complete payment

### Step 4: Domain Settings (After Purchase)
1. Go to Dashboard → Domain List
2. Click on your domain
3. Go to "Advanced DNS"
4. Note down your nameservers (you'll need these)

---

## PART 3: SET UP PROFESSIONAL EMAIL

### Option A: Namecheap Private Email (Recommended - Easy)

**Price:** $0.91/month (Starter) or $2.49/month (Pro)

**Steps:**
1. In Namecheap Dashboard, go to "Apps" → "Private Email"
2. Select your domain: `lumierecurves.shop`
3. Choose plan (Starter is fine to start)
4. Create mailbox:
   - Email: `ashjad@lumierecurves.shop`
   - Password: [Create strong password - SAVE THIS]
5. Complete purchase

### Option B: Namecheap Email Forwarding (FREE but limited)

1. Go to Domain List → Your Domain → "Redirect Email"
2. Add forwarding rule:
   - **Alias:** ashjad
   - **Forward to:** ashjadmm@gmail.com
3. Save

**Limitation:** You can receive but not send from this address

### Option C: Zoho Mail (Free for 1 user)

1. Go to [zoho.com/mail](https://www.zoho.com/mail/)
2. Sign up for free plan
3. Add your domain
4. Create ashjad@lumierecurves.shop
5. Update DNS records in Namecheap

---

## PART 4: EMAIL FORWARDING TO GMAIL

### If Using Namecheap Private Email:

**Step 1: Set Up Forwarding in Namecheap**
1. Log into Private Email webmail: `privateemail.com`
2. Go to Settings → Mail → Forwarding
3. Add rule:
   - Forward to: `ashjadmm@gmail.com`
   - Keep copy in mailbox: Yes
4. Save

**Step 2: Verify It Works**
- Send test email to `ashjad@lumierecurves.shop`
- Check if it arrives at `ashjadmm@gmail.com`

---

## PART 5: GMAIL "SEND AS" SETUP

This allows you to SEND emails from `ashjad@lumierecurves.shop` using Gmail.

### Step 1: Get SMTP Details from Namecheap

**Namecheap Private Email SMTP Settings:**
| Setting | Value |
|---------|-------|
| SMTP Server | `mail.privateemail.com` |
| Port | 465 (SSL) or 587 (TLS) |
| Username | `ashjad@lumierecurves.shop` |
| Password | [Your email password] |

### Step 2: Add to Gmail

1. Open Gmail (ashjadmm@gmail.com)
2. Click ⚙️ Settings → "See all settings"
3. Go to "Accounts and Import" tab
4. Find "Send mail as:" section
5. Click "Add another email address"

### Step 3: Enter Your Business Email
```
Name: Ashjad - Lumière Curves
Email: ashjad@lumierecurves.shop
☑️ Treat as an alias
```
Click "Next Step"

### Step 4: Enter SMTP Settings
```
SMTP Server: mail.privateemail.com
Port: 587
Username: ashjad@lumierecurves.shop
Password: [Your Namecheap email password]
☑️ Secured connection using TLS
```
Click "Add Account"

### Step 5: Verify
1. Gmail will send a confirmation email to `ashjad@lumierecurves.shop`
2. This will forward to your Gmail (from Step 4)
3. Click the confirmation link OR enter the code
4. Done!

### Step 6: Set as Default (Optional)
1. Go back to Settings → Accounts and Import
2. Under "Send mail as:", click "make default" next to your business email

---

## PART 6: HOST YOUR WEBSITE

### Option A: Namecheap Hosting (If You Bought Bundle)

**For Static Site (Your React Website):**

1. Build your website:
```bash
cd /Users/ashnabaziz/Downloads/project-horizon-v15-2/lavena-curves/website
npm run build
```

2. This creates a `dist` folder

3. In Namecheap cPanel:
   - Go to File Manager
   - Navigate to `public_html`
   - Upload all files from `dist` folder

4. Your site will be live at `lumierecurves.shop`

### Option B: Vercel (FREE - Recommended for React)

1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Import your project
4. Deploy automatically

5. Connect custom domain:
   - In Vercel: Settings → Domains → Add `lumierecurves.shop`
   - In Namecheap: Add DNS records Vercel provides

### Option C: Netlify (FREE Alternative)

1. Go to [netlify.com](https://netlify.com)
2. Drag & drop your `dist` folder
3. Connect custom domain

---

## PART 7: DNS SETTINGS REFERENCE

### If Using Vercel Hosting:

Add these in Namecheap → Advanced DNS:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | @ | 76.76.21.21 | Automatic |
| CNAME | www | cname.vercel-dns.com | Automatic |

### If Using Namecheap Hosting:

Keep default nameservers - no changes needed.

### For Email (Namecheap Private Email):

These should be auto-configured, but verify:

| Type | Host | Value |
|------|------|-------|
| MX | @ | mx1.privateemail.com (Priority 10) |
| MX | @ | mx2.privateemail.com (Priority 20) |
| TXT | @ | v=spf1 include:spf.privateemail.com ~all |

---

## CREDENTIALS TO SAVE

**⚠️ SAVE THESE SECURELY:**

### Namecheap Account
```
Website: namecheap.com
Email: ashjadmm@gmail.com
Password: [YOUR PASSWORD]
```

### Business Email
```
Email: ashjad@lumierecurves.shop
Password: [YOUR PASSWORD]
Webmail: privateemail.com
SMTP: mail.privateemail.com:587
IMAP: mail.privateemail.com:993
```

### Domain Details
```
Domain: lumierecurves.shop
Registrar: Namecheap
Expiry: [DATE + 1 YEAR]
Auto-renew: [Enable this!]
```

---

## QUICK CHECKLIST

- [ ] Buy domain on Namecheap
- [ ] Purchase Private Email add-on
- [ ] Create ashjad@lumierecurves.shop
- [ ] Set up forwarding to ashjadmm@gmail.com
- [ ] Add "Send As" in Gmail
- [ ] Verify email works both ways
- [ ] Deploy website (Vercel recommended)
- [ ] Connect domain to website
- [ ] Test website loads on domain

---

## ESTIMATED COSTS (First Year)

| Item | Cost |
|------|------|
| .shop Domain | $2.98 (or FREE with hosting) |
| Stellar Hosting | $28.88/year |
| Private Email | $10.92/year ($0.91/mo) |
| **TOTAL** | **~$42/year** |

---

## NEED HELP?

- Namecheap Support: Live chat on their website
- Gmail Help: support.google.com/mail
- Vercel Docs: vercel.com/docs

---

*Created: January 2, 2026*
*For: Lumière Curves Setup*
