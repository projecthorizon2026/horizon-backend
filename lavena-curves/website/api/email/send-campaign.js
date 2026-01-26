// Email Campaign API - Supports Resend and Brevo
// Resend Docs: https://resend.com/docs/api-reference/emails/send-email

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Check for Resend first (preferred), then Brevo
    const resendKey = process.env.RESEND_API_KEY;
    const brevoKey = process.env.BREVO_API_KEY;

    if (!resendKey && !brevoKey) {
      return res.status(500).json({
        error: 'Email service not configured. Add RESEND_API_KEY or BREVO_API_KEY to environment variables.'
      });
    }

    const {
      to,
      subject,
      htmlContent,
      textContent,
      from,
      replyTo
    } = req.body;

    if (!to || !subject) {
      return res.status(400).json({ error: 'Missing required fields: to, subject' });
    }

    // Format recipients
    const recipients = Array.isArray(to)
      ? to.map(r => typeof r === 'string' ? r : r.email)
      : [typeof to === 'string' ? to : to.email];

    // Use Resend if available
    if (resendKey) {
      // Use verified custom domain for sending
      const senderEmail = from || 'Lumière Curves <hello@lumierecurves.shop>';

      const response = await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${resendKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          from: senderEmail,
          to: recipients,
          subject,
          html: htmlContent,
          text: textContent,
          reply_to: replyTo || 'lumierecurves@proton.me'
        })
      });

      const data = await response.json();

      if (!response.ok) {
        console.error('Resend API error:', data);
        return res.status(response.status).json({
          error: data.message || 'Failed to send email',
          details: data
        });
      }

      return res.status(200).json({
        success: true,
        messageId: data.id,
        provider: 'resend',
        message: `Email sent to ${recipients.length} recipient(s)`
      });
    }

    // Fall back to Brevo
    if (brevoKey) {
      const emailPayload = {
        sender: { name: 'Lumière Curves', email: 'hello@lumierecurves.shop' },
        to: recipients.map(email => ({ email })),
        subject,
        htmlContent,
        textContent
      };

      const response = await fetch('https://api.brevo.com/v3/smtp/email', {
        method: 'POST',
        headers: {
          'accept': 'application/json',
          'api-key': brevoKey,
          'content-type': 'application/json'
        },
        body: JSON.stringify(emailPayload)
      });

      const data = await response.json();

      if (!response.ok) {
        console.error('Brevo API error:', data);
        return res.status(response.status).json({
          error: data.message || 'Failed to send email',
          code: data.code
        });
      }

      return res.status(200).json({
        success: true,
        messageId: data.messageId,
        provider: 'brevo',
        message: `Email sent to ${recipients.length} recipient(s)`
      });
    }

  } catch (error) {
    console.error('Error sending email:', error);
    res.status(500).json({ error: error.message || 'Failed to send email' });
  }
}
