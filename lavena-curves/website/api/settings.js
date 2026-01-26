// Get Store Settings API
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY
)

// Default settings
const DEFAULTS = {
  free_shipping_threshold: 2000,
  default_shipping_cost: 99,
  express_shipping_cost: 199,
  shipping_days_standard: '5-7',
  shipping_days_express: '2-3'
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  // Short cache to ensure fresh settings
  res.setHeader('Cache-Control', 's-maxage=10, stale-while-revalidate=30')

  if (req.method === 'OPTIONS') {
    return res.status(200).end()
  }

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' })
  }

  try {
    // Fetch all settings (stored as key-value pairs)
    const { data, error } = await supabase
      .from('store_settings')
      .select('key, value')

    if (error) {
      console.error('Settings fetch error:', error)
      return res.status(200).json(DEFAULTS)
    }

    // Parse key-value pairs into settings object
    const settings = { ...DEFAULTS }

    if (data && data.length > 0) {
      data.forEach(row => {
        try {
          const value = JSON.parse(row.value)
          settings[row.key] = value
        } catch {
          settings[row.key] = row.value
        }
      })
    }

    return res.status(200).json({
      free_shipping_threshold: settings.free_shipping_threshold ?? DEFAULTS.free_shipping_threshold,
      default_shipping_cost: settings.default_shipping_cost ?? DEFAULTS.default_shipping_cost,
      express_shipping_cost: settings.express_shipping_cost ?? DEFAULTS.express_shipping_cost,
      shipping_days_standard: settings.shipping_days_standard ?? DEFAULTS.shipping_days_standard,
      shipping_days_express: settings.shipping_days_express ?? DEFAULTS.shipping_days_express
    })

  } catch (error) {
    console.error('Settings API error:', error)
    return res.status(200).json(DEFAULTS)
  }
}
