import { useState, useEffect } from 'react'
import {
  Store,
  CreditCard,
  Truck,
  Mail,
  Bell,
  Shield,
  Globe,
  Palette,
  Save,
  RefreshCw,
  Check,
  AlertCircle,
  Key,
  ExternalLink
} from 'lucide-react'
import { supabase } from '../lib/supabase'

const settingsTabs = [
  { id: 'store', label: 'Store Info', icon: Store },
  { id: 'payment', label: 'Payments', icon: CreditCard },
  { id: 'shipping', label: 'Shipping', icon: Truck },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'integrations', label: 'Integrations', icon: Globe }
]

export default function Settings() {
  const [activeTab, setActiveTab] = useState('store')
  const [settings, setSettings] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    setLoading(true)
    try {
      const { data, error } = await supabase.from('store_settings').select('*')
      if (error) throw error

      const settingsMap = {}
      data?.forEach(s => {
        try {
          settingsMap[s.key] = JSON.parse(s.value)
        } catch {
          settingsMap[s.key] = s.value
        }
      })
      setSettings(settingsMap)
    } catch (err) {
      console.error('Error loading settings:', err)
    } finally {
      setLoading(false)
    }
  }

  const saveSetting = async (key, value) => {
    try {
      const { error } = await supabase
        .from('store_settings')
        .upsert({
          key,
          value: JSON.stringify(value),
          updated_at: new Date().toISOString()
        }, { onConflict: 'key' })

      if (error) throw error

      setSettings(prev => ({ ...prev, [key]: value }))
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      console.error('Error saving setting:', err)
      alert('Failed to save setting')
    }
  }

  const handleBulkSave = async (updates) => {
    setSaving(true)
    try {
      for (const [key, value] of Object.entries(updates)) {
        await saveSetting(key, value)
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 mt-1">Configure your store preferences</p>
        </div>
        {saved && (
          <div className="flex items-center gap-2 px-4 py-2 bg-green-100 text-green-700 rounded-lg">
            <Check className="w-4 h-4" />
            Saved!
          </div>
        )}
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar - Horizontal scrollable tabs on mobile, vertical sidebar on desktop */}
        <div className="lg:w-56 flex-shrink-0">
          <nav className="flex lg:flex-col gap-2 lg:gap-1 overflow-x-auto pb-2 lg:pb-0 -mx-4 px-4 lg:mx-0 lg:px-0">
            {settingsTabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 lg:gap-3 px-4 py-2 lg:py-3 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'bg-rose-50 text-rose-600'
                    : 'text-gray-600 hover:bg-gray-50 bg-gray-50 lg:bg-transparent'
                }`}
              >
                <tab.icon className="w-4 h-4 lg:w-5 lg:h-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {activeTab === 'store' && (
            <StoreSettings settings={settings} onSave={handleBulkSave} saving={saving} />
          )}
          {activeTab === 'payment' && (
            <PaymentSettings settings={settings} onSave={handleBulkSave} saving={saving} />
          )}
          {activeTab === 'shipping' && (
            <ShippingSettings settings={settings} onSave={handleBulkSave} saving={saving} />
          )}
          {activeTab === 'notifications' && (
            <NotificationSettings settings={settings} onSave={handleBulkSave} saving={saving} />
          )}
          {activeTab === 'integrations' && (
            <IntegrationSettings settings={settings} onSave={handleBulkSave} saving={saving} />
          )}
        </div>
      </div>
    </div>
  )
}

function StoreSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    store_name: settings.store_name || 'Lumière Curves',
    store_email: settings.store_email || 'hello@lumierecurves.shop',
    store_phone: settings.store_phone || '+971509751546',
    currency: settings.currency || 'INR',
    order_prefix: settings.order_prefix || 'LC',
    store_address: settings.store_address || '',
    gst_number: settings.gst_number || '',
    about_text: settings.about_text || ''
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(form)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">Store Information</h2>
        <p className="text-sm text-gray-500">Basic store details and branding</p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Store Name</label>
            <input
              type="text"
              value={form.store_name}
              onChange={(e) => setForm({ ...form, store_name: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Contact Email</label>
            <input
              type="email"
              value={form.store_email}
              onChange={(e) => setForm({ ...form, store_email: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number</label>
            <input
              type="tel"
              value={form.store_phone}
              onChange={(e) => setForm({ ...form, store_phone: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Currency</label>
            <select
              value={form.currency}
              onChange={(e) => setForm({ ...form, currency: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            >
              <option value="INR">INR (₹)</option>
              <option value="USD">USD ($)</option>
              <option value="AED">AED (د.إ)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Order Number Prefix</label>
            <input
              type="text"
              value={form.order_prefix}
              onChange={(e) => setForm({ ...form, order_prefix: e.target.value.toUpperCase() })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500 uppercase"
              maxLength={5}
            />
            <p className="text-xs text-gray-500 mt-1">Example: {form.order_prefix}-2024-00001</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">GST Number</label>
            <input
              type="text"
              value={form.gst_number}
              onChange={(e) => setForm({ ...form, gst_number: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="Optional"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Store Address</label>
          <textarea
            value={form.store_address}
            onChange={(e) => setForm({ ...form, store_address: e.target.value })}
            rows={3}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500 resize-none"
            placeholder="Full address for invoices..."
          />
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}

function PaymentSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    razorpay_key_id: settings.razorpay_key_id || '',
    razorpay_key_secret: settings.razorpay_key_secret || '',
    cod_enabled: settings.cod_enabled !== false,
    cod_min_order: settings.cod_min_order || 0,
    cod_max_order: settings.cod_max_order || 10000
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(form)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">Payment Settings</h2>
        <p className="text-sm text-gray-500">Configure payment gateways and methods</p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* Razorpay */}
        <div className="bg-blue-50 rounded-xl p-4">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Razorpay</h3>
              <p className="text-sm text-gray-500">Accept UPI, cards, netbanking & wallets</p>
            </div>
            <a
              href="https://dashboard.razorpay.com/app/keys"
              target="_blank"
              rel="noopener noreferrer"
              className="ml-auto flex items-center gap-1 text-sm text-blue-600 hover:underline"
            >
              Get API Keys <ExternalLink className="w-3 h-3" />
            </a>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Key ID</label>
              <input
                type="text"
                value={form.razorpay_key_id}
                onChange={(e) => setForm({ ...form, razorpay_key_id: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                placeholder="rzp_live_..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Key Secret</label>
              <input
                type="password"
                value={form.razorpay_key_secret}
                onChange={(e) => setForm({ ...form, razorpay_key_secret: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                placeholder="••••••••"
              />
            </div>
          </div>
        </div>

        {/* COD */}
        <div className="bg-gray-50 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gray-200 rounded-lg flex items-center justify-center">
                <Truck className="w-5 h-5 text-gray-600" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Cash on Delivery</h3>
                <p className="text-sm text-gray-500">Allow customers to pay on delivery</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={form.cod_enabled}
                onChange={(e) => setForm({ ...form, cod_enabled: e.target.checked })}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-rose-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-rose-600"></div>
            </label>
          </div>
          {form.cod_enabled && (
            <div className="grid grid-cols-2 gap-4 mt-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Min Order (₹)</label>
                <input
                  type="number"
                  value={form.cod_min_order}
                  onChange={(e) => setForm({ ...form, cod_min_order: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Order (₹)</label>
                <input
                  type="number"
                  value={form.cod_max_order}
                  onChange={(e) => setForm({ ...form, cod_max_order: parseInt(e.target.value) || 0 })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                />
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}

function ShippingSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    free_shipping_threshold: settings.free_shipping_threshold || 2999,
    default_shipping_cost: settings.default_shipping_cost || 99,
    express_shipping_cost: settings.express_shipping_cost || 199,
    shipping_days_standard: settings.shipping_days_standard || '5-7',
    shipping_days_express: settings.shipping_days_express || '2-3',
    ship_to_countries: settings.ship_to_countries || ['India']
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(form)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">Shipping Settings</h2>
        <p className="text-sm text-gray-500">Configure shipping rates and delivery times</p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Free Shipping Threshold (₹)</label>
            <input
              type="number"
              value={form.free_shipping_threshold}
              onChange={(e) => setForm({ ...form, free_shipping_threshold: parseInt(e.target.value) || 0 })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
            <p className="text-xs text-gray-500 mt-1">Orders above this get free shipping</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Standard Shipping (₹)</label>
            <input
              type="number"
              value={form.default_shipping_cost}
              onChange={(e) => setForm({ ...form, default_shipping_cost: parseInt(e.target.value) || 0 })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Express Shipping (₹)</label>
            <input
              type="number"
              value={form.express_shipping_cost}
              onChange={(e) => setForm({ ...form, express_shipping_cost: parseInt(e.target.value) || 0 })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Standard Delivery (days)</label>
            <input
              type="text"
              value={form.shipping_days_standard}
              onChange={(e) => setForm({ ...form, shipping_days_standard: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="e.g., 5-7"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}

function NotificationSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    email_order_confirmation: settings.email_order_confirmation !== false,
    email_shipping_update: settings.email_shipping_update !== false,
    email_delivery_confirmation: settings.email_delivery_confirmation !== false,
    admin_new_order_email: settings.admin_new_order_email || '',
    low_stock_alert_threshold: settings.low_stock_alert_threshold || 5
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(form)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">Notification Settings</h2>
        <p className="text-sm text-gray-500">Configure email and alert preferences</p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Customer Notifications</h3>
          {[
            { key: 'email_order_confirmation', label: 'Order Confirmation Email' },
            { key: 'email_shipping_update', label: 'Shipping Update Email' },
            { key: 'email_delivery_confirmation', label: 'Delivery Confirmation Email' }
          ].map(item => (
            <div key={item.key} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <span className="text-sm text-gray-700">{item.label}</span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={form[item.key]}
                  onChange={(e) => setForm({ ...form, [item.key]: e.target.checked })}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:ring-4 peer-focus:ring-rose-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-rose-600"></div>
              </label>
            </div>
          ))}
        </div>

        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Admin Notifications</h3>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">New Order Alert Email</label>
            <input
              type="email"
              value={form.admin_new_order_email}
              onChange={(e) => setForm({ ...form, admin_new_order_email: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="admin@example.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Low Stock Alert Threshold</label>
            <input
              type="number"
              value={form.low_stock_alert_threshold}
              onChange={(e) => setForm({ ...form, low_stock_alert_threshold: parseInt(e.target.value) || 5 })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}

function IntegrationSettings({ settings, onSave, saving }) {
  const [form, setForm] = useState({
    ga4_measurement_id: settings.ga4_measurement_id || '',
    clarity_project_id: settings.clarity_project_id || '',
    facebook_pixel_id: settings.facebook_pixel_id || '',
    whatsapp_number: settings.whatsapp_number || ''
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(form)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      <div className="px-6 py-4 border-b border-gray-100">
        <h2 className="text-lg font-semibold text-gray-900">Integrations</h2>
        <p className="text-sm text-gray-500">Connect third-party services</p>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* Analytics */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Analytics & Tracking</h3>

          <div className="bg-gray-50 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 font-bold text-xs">GA4</span>
              </div>
              <div>
                <p className="font-medium text-gray-900">Google Analytics 4</p>
                <a href="https://analytics.google.com" target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                  Get Measurement ID <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
            <input
              type="text"
              value={form.ga4_measurement_id}
              onChange={(e) => setForm({ ...form, ga4_measurement_id: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="G-XXXXXXXXXX"
            />
          </div>

          <div className="bg-gray-50 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 font-bold text-xs">MS</span>
              </div>
              <div>
                <p className="font-medium text-gray-900">Microsoft Clarity</p>
                <a href="https://clarity.microsoft.com" target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                  Get Project ID <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
            <input
              type="text"
              value={form.clarity_project_id}
              onChange={(e) => setForm({ ...form, clarity_project_id: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="Project ID"
            />
          </div>

          <div className="bg-gray-50 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xs">FB</span>
              </div>
              <div>
                <p className="font-medium text-gray-900">Facebook Pixel</p>
                <a href="https://business.facebook.com/events_manager" target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                  Get Pixel ID <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
            <input
              type="text"
              value={form.facebook_pixel_id}
              onChange={(e) => setForm({ ...form, facebook_pixel_id: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="Pixel ID"
            />
          </div>
        </div>

        {/* Messaging */}
        <div className="space-y-4">
          <h3 className="font-medium text-gray-900">Messaging</h3>

          <div className="bg-green-50 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xs">WA</span>
              </div>
              <div>
                <p className="font-medium text-gray-900">WhatsApp Business</p>
                <p className="text-xs text-gray-500">For customer support chat widget</p>
              </div>
            </div>
            <input
              type="tel"
              value={form.whatsapp_number}
              onChange={(e) => setForm({ ...form, whatsapp_number: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="+91XXXXXXXXXX"
            />
          </div>
        </div>

        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <p className="font-medium text-yellow-800">Important</p>
              <p className="text-sm text-yellow-700">
                After updating tracking IDs, you need to update the corresponding values in your index.html file for them to take effect.
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  )
}
