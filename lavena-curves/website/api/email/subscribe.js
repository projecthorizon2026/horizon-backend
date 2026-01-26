// Newsletter Subscribe API - Saves subscriber and sends welcome email

import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY
)

const welcomeEmailHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #f8f8f8;">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    <!-- Header -->
    <div style="text-align: center; margin-bottom: 30px;">
      <h1 style="color: #e11d48; font-size: 32px; margin: 0; font-weight: 300;">
        <span style="font-weight: 600;">Lumière</span> Curves
      </h1>
      <p style="color: #6b7280; margin-top: 8px; font-size: 14px;">Premium Plus-Size Lingerie</p>
    </div>

    <!-- Main Content -->
    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <h2 style="color: #111827; font-size: 28px; margin: 0 0 20px; text-align: center;">
        Welcome to the Family! 💕
      </h2>

      <p style="color: #4b5563; font-size: 16px; line-height: 1.7; margin-bottom: 20px;">
        Thank you for joining Lumière Curves! We're thrilled to have you as part of our community of confident, beautiful women who celebrate their curves.
      </p>

      <p style="color: #4b5563; font-size: 16px; line-height: 1.7; margin-bottom: 24px;">
        As a welcome gift, here's <strong style="color: #e11d48;">15% OFF</strong> your first order:
      </p>

      <!-- Discount Code Box -->
      <div style="background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%); border: 2px dashed #ec4899; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 30px;">
        <p style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 8px;">Your Exclusive Code</p>
        <p style="color: #e11d48; font-size: 32px; font-weight: 700; margin: 0; letter-spacing: 4px;">WELCOME15</p>
        <p style="color: #9ca3af; font-size: 12px; margin: 8px 0 0;">Valid for 30 days • One-time use</p>
      </div>

      <!-- CTA Button -->
      <div style="text-align: center; margin-bottom: 30px;">
        <a href="https://lumierecurves.shop" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px; box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);">
          Start Shopping →
        </a>
      </div>

      <!-- What to Expect -->
      <div style="border-top: 1px solid #f3f4f6; padding-top: 24px;">
        <h3 style="color: #374151; font-size: 16px; margin: 0 0 16px;">What you can expect from us:</h3>
        <ul style="color: #6b7280; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
          <li>First access to new arrivals & collections</li>
          <li>Exclusive VIP-only discounts</li>
          <li>Styling tips for your body type</li>
          <li>Member-only flash sales</li>
        </ul>
      </div>
    </div>

    <!-- Footer -->
    <div style="text-align: center; margin-top: 30px;">
      <p style="color: #9ca3af; font-size: 14px; margin-bottom: 10px;">
        With love,<br>
        <strong style="color: #6b7280;">The Lumière Curves Team</strong>
      </p>
      <p style="color: #d1d5db; font-size: 12px;">
        Follow us:
        <a href="https://instagram.com/lumierecurves" style="color: #ec4899; text-decoration: none;">@lumierecurves</a>
      </p>
      <p style="color: #d1d5db; font-size: 11px; margin-top: 20px;">
        You received this email because you signed up at lumierecurves.shop<br>
        <a href="https://lumierecurves.shop/unsubscribe" style="color: #9ca3af;">Unsubscribe</a>
      </p>
    </div>
  </div>
</body>
</html>
`

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')

  if (req.method === 'OPTIONS') {
    return res.status(200).end()
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    const { email } = req.body

    if (!email) {
      return res.status(400).json({ error: 'Email is required' })
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      return res.status(400).json({ error: 'Invalid email format' })
    }

    // Check if already subscribed
    const { data: existing } = await supabase
      .from('subscribers')
      .select('id')
      .eq('email', email.toLowerCase())
      .single()

    if (existing) {
      return res.status(400).json({ error: 'Already subscribed! Check your inbox for your welcome discount.' })
    }

    // Save to subscribers table
    const { error: insertError } = await supabase
      .from('subscribers')
      .insert({
        email: email.toLowerCase(),
        source: 'website_footer',
        subscribed_at: new Date().toISOString()
      })

    if (insertError) {
      console.error('Supabase insert error:', insertError)
      // Continue even if insert fails - still send welcome email
    }

    // Send welcome email via Resend
    const resendKey = process.env.RESEND_API_KEY
    if (resendKey) {
      const emailResponse = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${resendKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          from: 'Lumière Curves <hello@lumierecurves.shop>',
          to: [email],
          subject: 'Welcome to Lumière Curves! Here\'s 15% Off 💕',
          html: welcomeEmailHtml,
          reply_to: 'lumierecurves@proton.me'
        })
      })

      const emailData = await emailResponse.json()

      if (!emailResponse.ok) {
        console.error('Resend error:', emailData)
      }
    }

    return res.status(200).json({
      success: true,
      message: 'Welcome! Check your inbox for your exclusive discount code.'
    })

  } catch (error) {
    console.error('Subscribe error:', error)
    return res.status(500).json({ error: 'Failed to subscribe. Please try again.' })
  }
}
