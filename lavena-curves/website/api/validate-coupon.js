// Validate Coupon Code API
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY
)

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
    const { code, subtotal, customerEmail } = req.body

    if (!code) {
      return res.status(400).json({ valid: false, error: 'Coupon code is required' })
    }

    // Look up the coupon code (case-insensitive)
    const { data: coupon, error } = await supabase
      .from('discount_codes')
      .select('*')
      .ilike('code', code.trim())
      .single()

    if (error || !coupon) {
      return res.status(200).json({ valid: false, error: 'Invalid coupon code' })
    }

    // Check if coupon is active
    if (!coupon.is_active) {
      return res.status(200).json({ valid: false, error: 'This coupon is no longer active' })
    }

    // Check validity dates
    const now = new Date()
    const validFrom = new Date(coupon.valid_from)
    const validUntil = coupon.valid_until ? new Date(coupon.valid_until) : null

    if (now < validFrom) {
      return res.status(200).json({ valid: false, error: 'This coupon is not yet valid' })
    }

    if (validUntil && now > validUntil) {
      return res.status(200).json({ valid: false, error: 'This coupon has expired' })
    }

    // Check minimum order value
    if (coupon.min_order_value && subtotal < coupon.min_order_value) {
      return res.status(200).json({
        valid: false,
        error: `Minimum order of ₹${coupon.min_order_value} required for this coupon`
      })
    }

    // Check max uses
    if (coupon.max_uses && (coupon.used_count || 0) >= coupon.max_uses) {
      return res.status(200).json({ valid: false, error: 'This coupon has reached its usage limit' })
    }

    // Calculate discount
    let discountAmount = 0
    if (coupon.type === 'percentage') {
      discountAmount = Math.round((subtotal * coupon.value) / 100)
      // Apply max discount cap if set
      if (coupon.max_discount_amount && discountAmount > coupon.max_discount_amount) {
        discountAmount = coupon.max_discount_amount
      }
    } else {
      // Fixed amount
      discountAmount = coupon.value
    }

    // Don't allow discount greater than subtotal
    if (discountAmount > subtotal) {
      discountAmount = subtotal
    }

    return res.status(200).json({
      valid: true,
      coupon: {
        code: coupon.code,
        type: coupon.type,
        value: coupon.value,
        description: coupon.description,
        min_order_value: coupon.min_order_value,
        max_discount_amount: coupon.max_discount_amount
      },
      discountAmount,
      message: coupon.type === 'percentage'
        ? `${coupon.value}% discount applied!`
        : `₹${coupon.value} discount applied!`
    })

  } catch (error) {
    console.error('Coupon validation error:', error)
    return res.status(500).json({ valid: false, error: 'Failed to validate coupon' })
  }
}
