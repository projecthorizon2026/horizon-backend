// Email Templates for Lumière Curves

const brandStyles = `
  font-family: 'Helvetica Neue', Arial, sans-serif;
  background-color: #f8f8f8;
`

const headerHtml = `
<div style="text-align: center; margin-bottom: 30px;">
  <h1 style="color: #e11d48; font-size: 32px; margin: 0; font-weight: 300;">
    <span style="font-weight: 600;">Lumière</span> Curves
  </h1>
  <p style="color: #6b7280; margin-top: 8px; font-size: 14px;">Premium Plus-Size Lingerie</p>
</div>
`

const footerHtml = `
<div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
  <p style="color: #9ca3af; font-size: 14px; margin-bottom: 10px;">
    With love,<br>
    <strong style="color: #6b7280;">The Lumière Curves Team</strong>
  </p>
  <p style="color: #d1d5db; font-size: 12px;">
    <a href="https://instagram.com/lumierecurves" style="color: #ec4899; text-decoration: none;">@lumierecurves</a> |
    <a href="https://lumierecurves.shop" style="color: #ec4899; text-decoration: none;">lumierecurves.shop</a>
  </p>
  <p style="color: #d1d5db; font-size: 11px; margin-top: 15px;">
    Questions? Reply to this email or WhatsApp us at +91 98765 43210
  </p>
</div>
`

// Order Confirmation Email
export const orderConfirmation = (order) => ({
  subject: `Order Confirmed! #${order.order_number} 🎉`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="width: 60px; height: 60px; background: #dcfce7; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
          <span style="font-size: 30px;">✓</span>
        </div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Order Confirmed!</h2>
        <p style="color: #6b7280; margin-top: 8px;">Thank you for shopping with us, ${order.customer_name || 'Beautiful'}!</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Number</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">#${order.order_number}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Date</td>
            <td style="color: #111827; text-align: right;">${new Date(order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Payment Method</td>
            <td style="color: #111827; text-align: right;">${order.payment_method || 'Online'}</td>
          </tr>
        </table>
      </div>

      <h3 style="color: #374151; font-size: 16px; margin: 0 0 16px; border-bottom: 1px solid #e5e7eb; padding-bottom: 10px;">Order Items</h3>

      ${(order.items || []).map(item => `
        <div style="display: flex; gap: 15px; padding: 15px 0; border-bottom: 1px solid #f3f4f6;">
          <div style="width: 70px; height: 70px; background: #f3f4f6; border-radius: 8px; overflow: hidden;">
            ${item.image ? `<img src="${item.image}" style="width: 100%; height: 100%; object-fit: cover;">` : ''}
          </div>
          <div style="flex: 1;">
            <p style="margin: 0; font-weight: 600; color: #111827;">${item.name}</p>
            <p style="margin: 4px 0; color: #6b7280; font-size: 13px;">Size: ${item.size || 'N/A'} | Qty: ${item.quantity}</p>
            <p style="margin: 0; color: #e11d48; font-weight: 600;">₹${item.price?.toLocaleString('en-IN')}</p>
          </div>
        </div>
      `).join('')}

      <div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #e5e7eb;">
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 6px 0;">Subtotal</td>
            <td style="text-align: right;">₹${(order.subtotal || order.total)?.toLocaleString('en-IN')}</td>
          </tr>
          ${order.discount ? `<tr>
            <td style="color: #10b981; padding: 6px 0;">Discount</td>
            <td style="color: #10b981; text-align: right;">-₹${order.discount?.toLocaleString('en-IN')}</td>
          </tr>` : ''}
          <tr>
            <td style="color: #6b7280; padding: 6px 0;">Shipping</td>
            <td style="text-align: right;">${order.shipping_cost ? `₹${order.shipping_cost}` : 'FREE'}</td>
          </tr>
          <tr>
            <td style="color: #111827; font-weight: 700; padding: 12px 0; font-size: 16px;">Total</td>
            <td style="color: #e11d48; font-weight: 700; text-align: right; font-size: 18px;">₹${order.total?.toLocaleString('en-IN')}</td>
          </tr>
        </table>
      </div>

      <div style="background: #fdf2f8; border-radius: 12px; padding: 20px; margin-top: 24px;">
        <h4 style="color: #374151; margin: 0 0 10px; font-size: 14px;">📦 Shipping Address</h4>
        <p style="color: #6b7280; margin: 0; font-size: 14px; line-height: 1.6;">
          ${order.shipping_address?.name || order.customer_name}<br>
          ${order.shipping_address?.address || ''}<br>
          ${order.shipping_address?.city || ''}, ${order.shipping_address?.state || ''} ${order.shipping_address?.pincode || ''}<br>
          Phone: ${order.shipping_address?.phone || order.customer_phone || ''}
        </p>
      </div>

      <div style="text-align: center; margin-top: 30px;">
        <a href="https://lumierecurves.shop/track/${order.order_number}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Track Your Order
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Shipping Notification Email
export const shippingNotification = (order) => ({
  subject: `Your order is on its way! 🚚 #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 50px; margin-bottom: 15px;">🚚</div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Your Order Has Shipped!</h2>
        <p style="color: #6b7280; margin-top: 8px;">Great news! Your beautiful pieces are on their way.</p>
      </div>

      <div style="background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%); border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
        <p style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 8px;">Tracking Number</p>
        <p style="color: #e11d48; font-size: 20px; font-weight: 700; margin: 0; letter-spacing: 2px;">${order.tracking_number || 'Will be updated soon'}</p>
        <p style="color: #9ca3af; font-size: 12px; margin: 8px 0 0;">Carrier: ${order.carrier || 'Delhivery'}</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <h4 style="color: #374151; margin: 0 0 15px; font-size: 14px;">📍 Delivery Details</h4>
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 6px 0;">Order Number</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">#${order.order_number}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 6px 0;">Estimated Delivery</td>
            <td style="color: #10b981; font-weight: 600; text-align: right;">${order.estimated_delivery || '3-5 business days'}</td>
          </tr>
        </table>
      </div>

      <div style="background: #fdf2f8; border-radius: 12px; padding: 20px;">
        <h4 style="color: #374151; margin: 0 0 10px; font-size: 14px;">📦 Shipping To</h4>
        <p style="color: #6b7280; margin: 0; font-size: 14px; line-height: 1.6;">
          ${order.shipping_address?.name || order.customer_name}<br>
          ${order.shipping_address?.address || ''}<br>
          ${order.shipping_address?.city || ''}, ${order.shipping_address?.state || ''} ${order.shipping_address?.pincode || ''}
        </p>
      </div>

      <div style="text-align: center; margin-top: 30px;">
        <a href="${order.tracking_url || `https://lumierecurves.shop/track/${order.order_number}`}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Track Your Package
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Order Delivered Email
export const orderDelivered = (order) => ({
  subject: `Your order has been delivered! 📦💕 #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 50px; margin-bottom: 15px;">🎉</div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Your Order Has Arrived!</h2>
        <p style="color: #6b7280; margin-top: 8px;">We hope you love your new pieces as much as we loved making them for you!</p>
      </div>

      <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
        <p style="color: #166534; font-weight: 600; margin: 0;">✓ Order #${order.order_number} Delivered Successfully</p>
      </div>

      <div style="text-align: center; margin: 30px 0;">
        <h3 style="color: #374151; font-size: 18px; margin: 0 0 10px;">How was your experience?</h3>
        <p style="color: #6b7280; font-size: 14px; margin-bottom: 20px;">Your feedback helps us serve you better</p>
        <a href="https://lumierecurves.shop/review/${order.order_number}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Leave a Review ⭐
        </a>
      </div>

      <div style="border-top: 1px solid #e5e7eb; padding-top: 24px; margin-top: 24px;">
        <h4 style="color: #374151; font-size: 14px; margin: 0 0 15px;">Need Help?</h4>
        <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0;">
          If something isn't quite right, don't worry! We offer hassle-free exchanges within 30 days.
          Just reply to this email or WhatsApp us.
        </p>
      </div>

      <div style="background: #fdf2f8; border-radius: 12px; padding: 20px; margin-top: 24px; text-align: center;">
        <p style="color: #374151; font-weight: 600; margin: 0 0 8px;">Share Your Lumière Look!</p>
        <p style="color: #6b7280; font-size: 13px; margin: 0;">
          Tag us <a href="https://instagram.com/lumierecurves" style="color: #ec4899;">@lumierecurves</a> for a chance to be featured 📸
        </p>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Abandoned Cart Email
export const abandonedCart = (cart) => ({
  subject: `You left something beautiful behind... 👀`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Still Thinking It Over? 💭</h2>
        <p style="color: #6b7280; margin-top: 8px;">We saved your picks! They're waiting for you.</p>
      </div>

      <div style="margin-bottom: 24px;">
        ${(cart.items || []).map(item => `
          <div style="display: flex; gap: 15px; padding: 15px; background: #f9fafb; border-radius: 12px; margin-bottom: 10px;">
            <div style="width: 80px; height: 80px; background: #e5e7eb; border-radius: 8px; overflow: hidden;">
              ${item.image ? `<img src="${item.image}" style="width: 100%; height: 100%; object-fit: cover;">` : ''}
            </div>
            <div style="flex: 1;">
              <p style="margin: 0; font-weight: 600; color: #111827;">${item.name}</p>
              <p style="margin: 4px 0; color: #6b7280; font-size: 13px;">Size: ${item.size || 'N/A'}</p>
              <p style="margin: 0; color: #e11d48; font-weight: 600;">₹${item.price?.toLocaleString('en-IN')}</p>
            </div>
          </div>
        `).join('')}
      </div>

      <div style="background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%); border: 2px dashed #ec4899; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
        <p style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 8px;">Complete Your Order & Get</p>
        <p style="color: #e11d48; font-size: 28px; font-weight: 700; margin: 0;">10% OFF</p>
        <p style="color: #374151; font-size: 14px; margin: 8px 0 0;">Use code: <strong>COMEBACK10</strong></p>
        <p style="color: #9ca3af; font-size: 12px; margin: 8px 0 0;">Valid for 24 hours only!</p>
      </div>

      <div style="text-align: center;">
        <a href="https://lumierecurves.shop/cart" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px;">
          Complete My Order →
        </a>
      </div>

      <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 20px;">
        Free shipping on orders above ₹2,999 | 30-day easy returns
      </p>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Password Reset Email
export const passwordReset = (data) => ({
  subject: `Reset Your Password - Lumière Curves`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 50px; margin-bottom: 15px;">🔐</div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Reset Your Password</h2>
        <p style="color: #6b7280; margin-top: 8px;">We received a request to reset your password.</p>
      </div>

      <div style="text-align: center; margin: 30px 0;">
        <a href="${data.reset_url}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Reset Password
        </a>
      </div>

      <p style="color: #6b7280; font-size: 14px; text-align: center; line-height: 1.6;">
        This link will expire in 1 hour.<br>
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Payment Confirmation Email
export const paymentConfirmation = (order) => ({
  subject: `Payment Received! ₹${order.total?.toLocaleString('en-IN')} 💳 #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="width: 60px; height: 60px; background: #dcfce7; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
          <span style="font-size: 30px;">💳</span>
        </div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Payment Successful!</h2>
        <p style="color: #6b7280; margin-top: 8px;">Your payment has been securely processed.</p>
      </div>

      <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
        <p style="color: #166534; font-size: 14px; margin: 0 0 8px;">Amount Paid</p>
        <p style="color: #166534; font-size: 32px; font-weight: 700; margin: 0;">₹${order.total?.toLocaleString('en-IN')}</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Number</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">#${order.order_number}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Transaction ID</td>
            <td style="color: #111827; text-align: right; font-family: monospace;">${order.transaction_id || order.razorpay_payment_id || 'N/A'}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Payment Date</td>
            <td style="color: #111827; text-align: right;">${new Date(order.payment_date || order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Payment Method</td>
            <td style="color: #111827; text-align: right;">${order.payment_method || 'Online (Razorpay)'}</td>
          </tr>
        </table>
      </div>

      <div style="border-top: 1px solid #e5e7eb; padding-top: 20px;">
        <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0;">
          <strong style="color: #374151;">What's Next?</strong><br>
          We're preparing your order for shipment. You'll receive a shipping confirmation email with tracking details once your order is dispatched.
        </p>
      </div>

      <div style="text-align: center; margin-top: 30px;">
        <a href="https://lumierecurves.shop/orders/${order.order_number}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          View Order Details
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Refund Initiated Email
export const refundInitiated = (order) => ({
  subject: `Refund Initiated - #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 50px; margin-bottom: 15px;">🔄</div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Refund Initiated</h2>
        <p style="color: #6b7280; margin-top: 8px;">We've started processing your refund.</p>
      </div>

      <div style="background: #fef3c7; border: 1px solid #fcd34d; border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
        <p style="color: #92400e; font-size: 14px; margin: 0 0 8px;">Refund Amount</p>
        <p style="color: #92400e; font-size: 28px; font-weight: 700; margin: 0;">₹${order.refund_amount?.toLocaleString('en-IN')}</p>
        <p style="color: #b45309; font-size: 12px; margin: 8px 0 0;">Processing Time: 5-7 business days</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Number</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">#${order.order_number}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Refund Reason</td>
            <td style="color: #111827; text-align: right;">${order.refund_reason || 'Customer Request'}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Refund Method</td>
            <td style="color: #111827; text-align: right;">${order.refund_method || 'Original Payment Method'}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Request Date</td>
            <td style="color: #111827; text-align: right;">${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</td>
          </tr>
        </table>
      </div>

      ${order.refund_items ? `
      <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; margin-bottom: 20px;">
        <h4 style="color: #374151; font-size: 14px; margin: 0 0 15px;">Items Being Refunded</h4>
        ${order.refund_items.map(item => `
          <div style="display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid #f3f4f6;">
            <div style="flex: 1;">
              <p style="margin: 0; font-weight: 500; color: #111827; font-size: 14px;">${item.name}</p>
              <p style="margin: 4px 0 0; color: #6b7280; font-size: 13px;">Size: ${item.size || 'N/A'} | Qty: ${item.quantity}</p>
            </div>
            <p style="margin: 0; color: #e11d48; font-weight: 600;">₹${item.price?.toLocaleString('en-IN')}</p>
          </div>
        `).join('')}
      </div>
      ` : ''}

      <div style="background: #f0f9ff; border-radius: 12px; padding: 20px;">
        <p style="color: #0369a1; font-size: 14px; line-height: 1.6; margin: 0;">
          <strong>📌 Note:</strong> The refund will be credited to your original payment method. Bank processing times may vary.
        </p>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Refund Processed/Completed Email
export const refundProcessed = (order) => ({
  subject: `Refund Completed! ₹${order.refund_amount?.toLocaleString('en-IN')} 💚 #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="width: 60px; height: 60px; background: #dcfce7; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
          <span style="font-size: 30px;">✓</span>
        </div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Refund Completed!</h2>
        <p style="color: #6b7280; margin-top: 8px;">Your refund has been successfully processed.</p>
      </div>

      <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
        <p style="color: #166534; font-size: 14px; margin: 0 0 8px;">Amount Refunded</p>
        <p style="color: #166534; font-size: 32px; font-weight: 700; margin: 0;">₹${order.refund_amount?.toLocaleString('en-IN')}</p>
        <p style="color: #15803d; font-size: 12px; margin: 8px 0 0;">Credited to ${order.refund_method || 'Original Payment Method'}</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Number</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">#${order.order_number}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Refund ID</td>
            <td style="color: #111827; text-align: right; font-family: monospace;">${order.refund_id || 'N/A'}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Processed On</td>
            <td style="color: #111827; text-align: right;">${new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</td>
          </tr>
        </table>
      </div>

      <div style="border-top: 1px solid #e5e7eb; padding-top: 20px;">
        <p style="color: #6b7280; font-size: 14px; line-height: 1.6; margin: 0;">
          The refund should reflect in your account within 2-3 business days depending on your bank. If you don't see it after 5 business days, please contact your bank.
        </p>
      </div>

      <div style="background: #fdf2f8; border-radius: 12px; padding: 20px; margin-top: 24px; text-align: center;">
        <p style="color: #374151; font-weight: 600; margin: 0 0 8px;">We'd Love to Have You Back! 💕</p>
        <p style="color: #6b7280; font-size: 13px; margin: 0 0 15px;">
          Use code <strong style="color: #e11d48;">COMEBACK15</strong> for 15% off your next order
        </p>
        <a href="https://lumierecurves.shop" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 12px 28px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 14px;">
          Shop Now →
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Order Cancelled Email
export const orderCancelled = (order) => ({
  subject: `Order Cancelled - #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 50px; margin-bottom: 15px;">😔</div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Order Cancelled</h2>
        <p style="color: #6b7280; margin-top: 8px;">Your order has been cancelled as requested.</p>
      </div>

      <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; padding: 20px; margin-bottom: 24px; text-align: center;">
        <p style="color: #991b1b; font-weight: 600; margin: 0;">Order #${order.order_number} has been cancelled</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Date</td>
            <td style="color: #111827; text-align: right;">${new Date(order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Cancellation Reason</td>
            <td style="color: #111827; text-align: right;">${order.cancellation_reason || 'Customer Request'}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Total</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">₹${order.total?.toLocaleString('en-IN')}</td>
          </tr>
        </table>
      </div>

      ${order.payment_status === 'paid' ? `
      <div style="background: #f0fdf4; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <p style="color: #166534; font-size: 14px; line-height: 1.6; margin: 0;">
          <strong>💚 Refund Status:</strong> Your refund of ₹${order.total?.toLocaleString('en-IN')} has been initiated and will be credited to your original payment method within 5-7 business days.
        </p>
      </div>
      ` : ''}

      <div style="border-top: 1px solid #e5e7eb; padding-top: 20px;">
        <h4 style="color: #374151; font-size: 14px; margin: 0 0 15px;">Cancelled Items</h4>
        ${(order.items || []).map(item => `
          <div style="display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid #f3f4f6;">
            <div style="flex: 1;">
              <p style="margin: 0; font-weight: 500; color: #6b7280; font-size: 14px; text-decoration: line-through;">${item.name}</p>
              <p style="margin: 4px 0 0; color: #9ca3af; font-size: 13px;">Size: ${item.size || 'N/A'} | Qty: ${item.quantity}</p>
            </div>
          </div>
        `).join('')}
      </div>

      <div style="background: #fdf2f8; border-radius: 12px; padding: 20px; margin-top: 24px; text-align: center;">
        <p style="color: #374151; font-weight: 600; margin: 0 0 8px;">Changed Your Mind? 💕</p>
        <p style="color: #6b7280; font-size: 13px; margin: 0 0 15px;">
          We'd love to help you find the perfect pieces!
        </p>
        <a href="https://lumierecurves.shop" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 12px 28px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 14px;">
          Continue Shopping →
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Out for Delivery Email
export const outForDelivery = (order) => ({
  subject: `Out for Delivery Today! 🚚💨 #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 50px; margin-bottom: 15px;">🚚💨</div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Your Order is Out for Delivery!</h2>
        <p style="color: #6b7280; margin-top: 8px;">Get excited - your beautiful pieces arrive today!</p>
      </div>

      <div style="background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%); border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
        <p style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 8px;">Estimated Arrival</p>
        <p style="color: #e11d48; font-size: 24px; font-weight: 700; margin: 0;">Today by ${order.delivery_time || '8 PM'}</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Order Number</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">#${order.order_number}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Carrier</td>
            <td style="color: #111827; text-align: right;">${order.carrier || 'Delhivery'}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 8px 0;">Tracking Number</td>
            <td style="color: #111827; text-align: right; font-family: monospace;">${order.tracking_number || 'N/A'}</td>
          </tr>
        </table>
      </div>

      <div style="background: #fdf2f8; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <h4 style="color: #374151; margin: 0 0 10px; font-size: 14px;">📍 Delivering To</h4>
        <p style="color: #6b7280; margin: 0; font-size: 14px; line-height: 1.6;">
          ${order.shipping_address?.name || order.customer_name}<br>
          ${order.shipping_address?.address || ''}<br>
          ${order.shipping_address?.city || ''}, ${order.shipping_address?.state || ''} ${order.shipping_address?.pincode || ''}<br>
          Phone: ${order.shipping_address?.phone || order.customer_phone || ''}
        </p>
      </div>

      <div style="background: #fef3c7; border-radius: 12px; padding: 16px; margin-bottom: 24px;">
        <p style="color: #92400e; font-size: 14px; margin: 0; line-height: 1.5;">
          <strong>📞 Tip:</strong> Keep your phone handy! The delivery partner may call you when they arrive.
        </p>
      </div>

      <div style="text-align: center;">
        <a href="${order.tracking_url || `https://lumierecurves.shop/track/${order.order_number}`}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Track Live Location 📍
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Exchange Request Confirmation Email
export const exchangeConfirmation = (order) => ({
  subject: `Exchange Request Received ✓ #${order.order_number}`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="width: 60px; height: 60px; background: #dbeafe; border-radius: 50%; margin: 0 auto 15px; display: flex; align-items: center; justify-content: center;">
          <span style="font-size: 30px;">🔄</span>
        </div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Exchange Request Received!</h2>
        <p style="color: #6b7280; margin-top: 8px;">We've got your request and will process it soon.</p>
      </div>

      <div style="background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <p style="color: #0369a1; font-weight: 600; margin: 0 0 10px;">Exchange Details</p>
        <table style="width: 100%; font-size: 14px;">
          <tr>
            <td style="color: #6b7280; padding: 6px 0;">Exchange ID</td>
            <td style="color: #111827; font-weight: 600; text-align: right;">#EX${order.exchange_id || order.order_number}</td>
          </tr>
          <tr>
            <td style="color: #6b7280; padding: 6px 0;">Original Order</td>
            <td style="color: #111827; text-align: right;">#${order.order_number}</td>
          </tr>
        </table>
      </div>

      <div style="margin-bottom: 24px;">
        <h4 style="color: #374151; font-size: 14px; margin: 0 0 15px; padding-bottom: 10px; border-bottom: 1px solid #e5e7eb;">Items to Exchange</h4>
        ${(order.exchange_items || order.items || []).map(item => `
          <div style="display: flex; gap: 12px; padding: 12px 0; border-bottom: 1px solid #f3f4f6;">
            <div style="flex: 1;">
              <p style="margin: 0; font-weight: 500; color: #111827; font-size: 14px;">${item.name}</p>
              <p style="margin: 4px 0; color: #dc2626; font-size: 13px;">Current: Size ${item.current_size || item.size}</p>
              <p style="margin: 0; color: #16a34a; font-size: 13px;">Exchange for: Size ${item.new_size || 'TBD'}</p>
            </div>
          </div>
        `).join('')}
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <h4 style="color: #374151; font-size: 14px; margin: 0 0 15px;">📦 Next Steps</h4>
        <ol style="color: #6b7280; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
          <li>Pack your items securely in original packaging</li>
          <li>Our courier will pick up within 2-3 business days</li>
          <li>Once received, we'll ship your new size</li>
          <li>Track everything from your account</li>
        </ol>
      </div>

      <div style="background: #fef3c7; border-radius: 12px; padding: 16px; margin-bottom: 24px;">
        <p style="color: #92400e; font-size: 14px; margin: 0;">
          <strong>📍 Pickup Address:</strong> We'll collect from the same address as your original delivery. Need to change it? Reply to this email.
        </p>
      </div>

      <div style="text-align: center;">
        <a href="https://lumierecurves.shop/orders/${order.order_number}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 14px 32px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Track Exchange Status
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Back in Stock Email
export const backInStock = (data) => ({
  subject: `It's Back! ${data.product_name} is in stock 🎉`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <div style="font-size: 50px; margin-bottom: 15px;">🎉</div>
        <h2 style="color: #111827; font-size: 24px; margin: 0;">Great News - It's Back!</h2>
        <p style="color: #6b7280; margin-top: 8px;">The item you've been waiting for is back in stock!</p>
      </div>

      <div style="background: #f9fafb; border-radius: 16px; padding: 24px; margin-bottom: 24px; text-align: center;">
        ${data.product_image ? `
        <div style="margin-bottom: 16px;">
          <img src="${data.product_image}" alt="${data.product_name}" style="max-width: 200px; border-radius: 12px;">
        </div>
        ` : ''}
        <h3 style="color: #111827; font-size: 20px; margin: 0 0 8px;">${data.product_name}</h3>
        <p style="color: #6b7280; font-size: 14px; margin: 0 0 12px;">Size: ${data.size || 'Multiple sizes available'}</p>
        <p style="color: #e11d48; font-size: 24px; font-weight: 700; margin: 0;">₹${data.price?.toLocaleString('en-IN')}</p>
      </div>

      <div style="background: #fef3c7; border-radius: 12px; padding: 16px; margin-bottom: 24px; text-align: center;">
        <p style="color: #92400e; font-size: 14px; margin: 0;">
          ⚡ <strong>Selling fast!</strong> This item was previously sold out - grab it before it's gone again!
        </p>
      </div>

      <div style="text-align: center;">
        <a href="${data.product_url || 'https://lumierecurves.shop'}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 50px; font-weight: 600; font-size: 16px;">
          Shop Now Before It's Gone →
        </a>
      </div>

      <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 20px;">
        Free shipping on orders above ₹2,999 | 30-day easy returns
      </p>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Welcome Email (Account Creation)
export const welcomeAccount = (user) => ({
  subject: `Welcome to Lumière Curves, ${user.name || 'Beautiful'}! 💕`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: #111827; font-size: 28px; margin: 0;">Welcome to the Family! 💕</h2>
        <p style="color: #6b7280; margin-top: 8px;">Your account has been created successfully.</p>
      </div>

      <p style="color: #4b5563; font-size: 16px; line-height: 1.7; margin-bottom: 24px;">
        Hi ${user.name || 'Beautiful'},<br><br>
        Thank you for joining Lumière Curves! We're India's premier plus-size lingerie brand, dedicated to helping every woman feel confident and beautiful.
      </p>

      <div style="background: linear-gradient(135deg, #fdf2f8 0%, #fce7f3 100%); border: 2px dashed #ec4899; border-radius: 12px; padding: 24px; text-align: center; margin-bottom: 24px;">
        <p style="color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: 2px; margin: 0 0 8px;">Welcome Gift</p>
        <p style="color: #e11d48; font-size: 32px; font-weight: 700; margin: 0;">15% OFF</p>
        <p style="color: #374151; font-size: 14px; margin: 8px 0 0;">Use code: <strong>WELCOME15</strong></p>
        <p style="color: #9ca3af; font-size: 12px; margin: 8px 0 0;">Valid for 30 days on your first order</p>
      </div>

      <div style="background: #f9fafb; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
        <h4 style="color: #374151; font-size: 14px; margin: 0 0 15px;">Your Account Benefits:</h4>
        <ul style="color: #6b7280; font-size: 14px; line-height: 1.8; margin: 0; padding-left: 20px;">
          <li>Track orders & manage returns easily</li>
          <li>Save your measurements for perfect fits</li>
          <li>Faster checkout with saved addresses</li>
          <li>Early access to sales & new arrivals</li>
          <li>Earn points on every purchase</li>
        </ul>
      </div>

      <div style="text-align: center; margin-top: 30px;">
        <a href="https://lumierecurves.shop" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Start Shopping →
        </a>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

// Review Request Email (sent 7 days after delivery)
export const reviewRequest = (order) => ({
  subject: `How are you loving your new pieces? ⭐`,
  html: `
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 0; ${brandStyles}">
  <div style="max-width: 600px; margin: 0 auto; padding: 40px 20px;">
    ${headerHtml}

    <div style="background: white; border-radius: 16px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
      <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="color: #111827; font-size: 24px; margin: 0;">How's Your New Lingerie? 💕</h2>
        <p style="color: #6b7280; margin-top: 8px;">We'd love to hear about your experience!</p>
      </div>

      <p style="color: #4b5563; font-size: 16px; line-height: 1.7; text-align: center; margin-bottom: 24px;">
        Your review helps other women find their perfect fit. Share your thoughts and get <strong style="color: #e11d48;">₹200 off</strong> your next order!
      </p>

      <div style="text-align: center; margin: 30px 0;">
        <a href="https://lumierecurves.shop/review/${order.order_number}" style="display: inline-block; background: linear-gradient(135deg, #ec4899 0%, #e11d48 100%); color: white; padding: 16px 40px; text-decoration: none; border-radius: 50px; font-weight: 600;">
          Write a Review ⭐
        </a>
      </div>

      <div style="background: #fdf2f8; border-radius: 12px; padding: 20px; text-align: center;">
        <p style="color: #374151; font-weight: 600; margin: 0 0 8px;">Share Your Lumière Look!</p>
        <p style="color: #6b7280; font-size: 13px; margin: 0;">
          Post a photo and tag <a href="https://instagram.com/lumierecurves" style="color: #ec4899;">@lumierecurves</a> for a chance to win a ₹2,000 gift card! 📸
        </p>
      </div>
    </div>

    ${footerHtml}
  </div>
</body>
</html>
`
})

export default {
  orderConfirmation,
  shippingNotification,
  orderDelivered,
  abandonedCart,
  passwordReset,
  reviewRequest,
  paymentConfirmation,
  refundInitiated,
  refundProcessed,
  orderCancelled,
  outForDelivery,
  exchangeConfirmation,
  backInStock,
  welcomeAccount
}
