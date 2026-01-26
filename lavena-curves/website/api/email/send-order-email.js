// Send Order-related Emails API
import * as templates from './templates.js'

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

  const resendKey = process.env.RESEND_API_KEY
  if (!resendKey) {
    return res.status(500).json({ error: 'Email service not configured' })
  }

  try {
    const { type, data, to } = req.body

    if (!type || !data || !to) {
      return res.status(400).json({ error: 'Missing required fields: type, data, to' })
    }

    // Get the appropriate template
    let emailTemplate
    switch (type) {
      case 'order_confirmation':
        emailTemplate = templates.orderConfirmation(data)
        break
      case 'payment_confirmation':
        emailTemplate = templates.paymentConfirmation(data)
        break
      case 'shipping':
        emailTemplate = templates.shippingNotification(data)
        break
      case 'out_for_delivery':
        emailTemplate = templates.outForDelivery(data)
        break
      case 'delivered':
        emailTemplate = templates.orderDelivered(data)
        break
      case 'order_cancelled':
        emailTemplate = templates.orderCancelled(data)
        break
      case 'refund_initiated':
        emailTemplate = templates.refundInitiated(data)
        break
      case 'refund_processed':
        emailTemplate = templates.refundProcessed(data)
        break
      case 'exchange_confirmation':
        emailTemplate = templates.exchangeConfirmation(data)
        break
      case 'abandoned_cart':
        emailTemplate = templates.abandonedCart(data)
        break
      case 'back_in_stock':
        emailTemplate = templates.backInStock(data)
        break
      case 'password_reset':
        emailTemplate = templates.passwordReset(data)
        break
      case 'review_request':
        emailTemplate = templates.reviewRequest(data)
        break
      case 'welcome_account':
        emailTemplate = templates.welcomeAccount(data)
        break
      default:
        return res.status(400).json({ error: `Unknown email type: ${type}` })
    }

    // Send via Resend
    const response = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${resendKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        from: 'Lumière Curves <hello@lumierecurves.shop>',
        to: Array.isArray(to) ? to : [to],
        subject: emailTemplate.subject,
        html: emailTemplate.html,
        reply_to: 'lumierecurves@proton.me'
      })
    })

    const result = await response.json()

    if (!response.ok) {
      console.error('Resend error:', result)
      return res.status(response.status).json({ error: result.message || 'Failed to send email' })
    }

    return res.status(200).json({
      success: true,
      messageId: result.id,
      type,
      to
    })

  } catch (error) {
    console.error('Send order email error:', error)
    return res.status(500).json({ error: 'Failed to send email' })
  }
}
