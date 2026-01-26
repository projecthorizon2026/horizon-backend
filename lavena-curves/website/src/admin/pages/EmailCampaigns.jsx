import { useState, useEffect } from 'react'
import {
  Mail,
  Plus,
  Send,
  Edit2,
  Trash2,
  X,
  RefreshCw,
  Users,
  Eye,
  Clock,
  CheckCircle,
  BarChart3,
  MousePointer,
  ShoppingBag,
  Copy,
  FileText,
  Zap,
  Calendar,
  Target,
  TrendingUp,
  AlertTriangle,
  Settings,
  TestTube,
  Link,
  Unlink
} from 'lucide-react'
import { supabase } from '../lib/supabase'

const campaignTypes = [
  { id: 'newsletter', label: 'Newsletter', icon: FileText, color: 'blue' },
  { id: 'promotional', label: 'Promotional', icon: Zap, color: 'orange' },
  { id: 'abandoned_cart', label: 'Abandoned Cart', icon: ShoppingBag, color: 'red' },
  { id: 'welcome', label: 'Welcome Series', icon: Users, color: 'green' },
  { id: 'order_update', label: 'Order Update', icon: Clock, color: 'purple' }
]

const emailTemplates = [
  {
    id: 'welcome',
    name: 'Welcome Email',
    subject: 'Welcome to Lumière Curves! 💕',
    preview: 'Thank you for joining our community...',
    type: 'welcome',
    html: `
      <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #e11d48; font-size: 28px; margin: 0;">Lumière Curves</h1>
          <p style="color: #6b7280; margin-top: 5px;">Premium Plus-Size Lingerie</p>
        </div>
        <h2 style="color: #111827; font-size: 24px;">Welcome to the Family! 💕</h2>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6;">
          Thank you for joining Lumière Curves! We're thrilled to have you as part of our community of confident, beautiful women.
        </p>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6;">
          As a welcome gift, enjoy <strong>15% off</strong> your first order with code: <strong style="color: #e11d48;">WELCOME15</strong>
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="https://lumierecurves.shop" style="display: inline-block; background: #e11d48; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600;">Shop Now</a>
        </div>
        <p style="color: #9ca3af; font-size: 14px; text-align: center;">
          With love,<br>The Lumière Curves Team
        </p>
      </div>
    `
  },
  {
    id: 'abandoned_cart',
    name: 'Abandoned Cart Reminder',
    subject: 'You left something beautiful behind... 👀',
    preview: 'Complete your purchase and enjoy...',
    type: 'abandoned_cart',
    html: `
      <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #e11d48; font-size: 28px; margin: 0;">Lumière Curves</h1>
        </div>
        <h2 style="color: #111827; font-size: 24px;">Still thinking it over? 💭</h2>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6;">
          We noticed you left some beautiful pieces in your cart. Don't worry, we've saved them for you!
        </p>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6;">
          Complete your purchase in the next 24 hours and get <strong>10% off</strong> with code: <strong style="color: #e11d48;">COMEBACK10</strong>
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="https://lumierecurves.shop/cart" style="display: inline-block; background: #e11d48; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600;">Complete My Order</a>
        </div>
      </div>
    `
  },
  {
    id: 'new_arrival',
    name: 'New Arrivals',
    subject: 'New styles just dropped! ✨',
    preview: 'Be the first to shop our latest...',
    type: 'promotional',
    html: `
      <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #e11d48; font-size: 28px; margin: 0;">Lumière Curves</h1>
        </div>
        <h2 style="color: #111827; font-size: 24px; text-align: center;">New Arrivals Are Here! ✨</h2>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6; text-align: center;">
          Be the first to discover our latest collection of premium plus-size lingerie. Designed for comfort, made for confidence.
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="https://lumierecurves.shop/new" style="display: inline-block; background: #e11d48; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600;">Shop New Arrivals</a>
        </div>
      </div>
    `
  },
  {
    id: 'sale',
    name: 'Sale Announcement',
    subject: 'SALE: Up to 50% off everything! 🎉',
    preview: "Don't miss our biggest sale...",
    type: 'promotional',
    html: `
      <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px; background: linear-gradient(135deg, #fdf2f8, #fff);">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #e11d48; font-size: 28px; margin: 0;">Lumière Curves</h1>
        </div>
        <div style="text-align: center; background: #e11d48; color: white; padding: 30px; border-radius: 12px;">
          <h2 style="font-size: 32px; margin: 0;">UP TO 50% OFF</h2>
          <p style="font-size: 18px; margin-top: 10px;">Our biggest sale of the season!</p>
        </div>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6; text-align: center; margin-top: 20px;">
          Shop our premium collection at incredible prices. Limited time only!
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="https://lumierecurves.shop/sale" style="display: inline-block; background: #111827; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600;">Shop the Sale</a>
        </div>
      </div>
    `
  },
  {
    id: 'order_confirmed',
    name: 'Order Confirmation',
    subject: 'Your order is confirmed! 🎉',
    preview: 'Thank you for your order...',
    type: 'order_update',
    html: `
      <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #e11d48; font-size: 28px; margin: 0;">Lumière Curves</h1>
        </div>
        <div style="text-align: center; margin-bottom: 20px;">
          <div style="width: 60px; height: 60px; background: #dcfce7; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;">
            <span style="font-size: 30px;">✓</span>
          </div>
        </div>
        <h2 style="color: #111827; font-size: 24px; text-align: center;">Order Confirmed!</h2>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6; text-align: center;">
          Thank you for your order! We're preparing your items with care.
        </p>
        <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
          <p style="margin: 0; color: #6b7280;">Order details will appear here</p>
        </div>
      </div>
    `
  },
  {
    id: 'shipping',
    name: 'Shipping Notification',
    subject: 'Your order is on its way! 📦',
    preview: 'Great news! Your order has shipped...',
    type: 'order_update',
    html: `
      <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 40px 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
          <h1 style="color: #e11d48; font-size: 28px; margin: 0;">Lumière Curves</h1>
        </div>
        <h2 style="color: #111827; font-size: 24px; text-align: center;">Your Order Has Shipped! 📦</h2>
        <p style="color: #4b5563; font-size: 16px; line-height: 1.6; text-align: center;">
          Great news! Your order is on its way to you.
        </p>
        <div style="text-align: center; margin: 30px 0;">
          <a href="#" style="display: inline-block; background: #e11d48; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600;">Track Your Order</a>
        </div>
      </div>
    `
  }
]

function CreateCampaignModal({ campaign, onClose, onSave, brevoConnected }) {
  const [formData, setFormData] = useState({
    name: campaign?.name || '',
    type: campaign?.type || 'newsletter',
    subject: campaign?.subject || '',
    content: campaign?.content || '',
    scheduled_at: campaign?.scheduled_at ? new Date(campaign.scheduled_at).toISOString().slice(0, 16) : '',
    segment: campaign?.segment?.type || 'all'
  })
  const [saving, setSaving] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [testEmail, setTestEmail] = useState('')
  const [sendingTest, setSendingTest] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)

    try {
      const payload = {
        ...formData,
        scheduled_at: formData.scheduled_at ? new Date(formData.scheduled_at).toISOString() : null,
        status: formData.scheduled_at ? 'scheduled' : 'draft',
        segment: { type: formData.segment }
      }

      if (campaign) {
        await supabase.from('email_campaigns').update(payload).eq('id', campaign.id)
      } else {
        await supabase.from('email_campaigns').insert(payload)
      }

      onSave()
      onClose()
    } catch (err) {
      console.error('Error saving campaign:', err)
    } finally {
      setSaving(false)
    }
  }

  const applyTemplate = (template) => {
    setFormData({
      ...formData,
      subject: template.subject,
      type: template.type,
      content: template.html
    })
    setSelectedTemplate(template.id)
  }

  const sendTestEmail = async () => {
    if (!testEmail || !formData.subject || !formData.content) {
      alert('Please fill in subject and content, and enter a test email')
      return
    }

    setSendingTest(true)
    try {
      const response = await fetch('/api/email/send-campaign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: testEmail,
          subject: `[TEST] ${formData.subject}`,
          htmlContent: formData.content,
          from: 'Lumière Curves <hello@lumierecurves.shop>'
        })
      })

      const data = await response.json()

      if (response.ok) {
        alert('Test email sent successfully!')
      } else {
        alert(`Failed to send: ${data.error}`)
      }
    } catch (err) {
      alert('Failed to send test email')
    } finally {
      setSendingTest(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">
            {campaign ? 'Edit Campaign' : 'Create Email Campaign'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[calc(90vh-140px)] space-y-6">
          {/* Templates */}
          {!campaign && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Start with a template</label>
              <div className="grid grid-cols-3 gap-2">
                {emailTemplates.slice(0, 6).map(template => (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => applyTemplate(template)}
                    className={`p-3 text-left border-2 rounded-lg transition-colors ${
                      selectedTemplate === template.id
                        ? 'border-rose-500 bg-rose-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <p className="font-medium text-gray-900 text-sm truncate">{template.name}</p>
                    <p className="text-xs text-gray-500 truncate">{template.preview}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                placeholder="e.g., January Newsletter"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Type</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              >
                {campaignTypes.map(type => (
                  <option key={type.id} value={type.id}>{type.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Audience Segment</label>
              <select
                value={formData.segment}
                onChange={(e) => setFormData({ ...formData, segment: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              >
                <option value="all">All Subscribers</option>
                <option value="new">New Customers (Last 30 days)</option>
                <option value="vip">VIP Customers (₹5000+ spent)</option>
                <option value="inactive">Inactive (No order in 60 days)</option>
                <option value="abandoned">Abandoned Cart Users</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email Subject *</label>
            <input
              type="text"
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="Enter email subject line"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email Content (HTML)</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              rows={8}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500 resize-none font-mono text-sm"
              placeholder="Write your email content here... (HTML supported)"
            />
          </div>

          {/* Test Email */}
          {brevoConnected && (
            <div className="bg-gray-50 rounded-lg p-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Send Test Email</label>
              <div className="flex gap-2">
                <input
                  type="email"
                  value={testEmail}
                  onChange={(e) => setTestEmail(e.target.value)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                  placeholder="your@email.com"
                />
                <button
                  type="button"
                  onClick={sendTestEmail}
                  disabled={sendingTest}
                  className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 flex items-center gap-2"
                >
                  {sendingTest ? (
                    <RefreshCw className="w-4 h-4 animate-spin" />
                  ) : (
                    <TestTube className="w-4 h-4" />
                  )}
                  Send Test
                </button>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Schedule (Optional)</label>
            <input
              type="datetime-local"
              value={formData.scheduled_at}
              onChange={(e) => setFormData({ ...formData, scheduled_at: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
            <p className="text-xs text-gray-500 mt-1">Leave empty to save as draft</p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : formData.scheduled_at ? 'Schedule Campaign' : 'Save Draft'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function EmailSetupModal({ onClose, onConnect }) {
  const [checking, setChecking] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('resend')

  const checkConnection = async () => {
    setChecking(true)
    try {
      const response = await fetch('/api/email/contacts?action=stats')
      const data = await response.json()

      if (response.ok && (data.email || data.connected)) {
        onConnect({
          provider: data.provider || 'resend',
          email: data.email,
          plan: data.plan?.[0]?.type || 'Free',
          credits: data.plan?.[0]?.credits || 100
        })
        onClose()
      } else {
        alert('Email service not configured. Add RESEND_API_KEY to Vercel environment variables.')
      }
    } catch (err) {
      alert('Failed to connect. Check your API key.')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Connect Email Service</h2>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto max-h-[60vh]">
          {/* Provider Selection */}
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setSelectedProvider('resend')}
              className={`p-4 border-2 rounded-xl text-left transition-colors ${
                selectedProvider === 'resend'
                  ? 'border-rose-500 bg-rose-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="font-semibold text-gray-900">Resend</div>
              <div className="text-xs text-gray-500 mt-1">Recommended - Easy setup</div>
              <div className="text-xs text-green-600 mt-1">100 emails/day free</div>
            </button>
            <button
              onClick={() => setSelectedProvider('brevo')}
              className={`p-4 border-2 rounded-xl text-left transition-colors ${
                selectedProvider === 'brevo'
                  ? 'border-rose-500 bg-rose-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="font-semibold text-gray-900">Brevo</div>
              <div className="text-xs text-gray-500 mt-1">More features</div>
              <div className="text-xs text-green-600 mt-1">300 emails/day free</div>
            </button>
          </div>

          {selectedProvider === 'resend' ? (
            <>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                  <Mail className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Resend</h3>
                  <p className="text-sm text-gray-500">Developer-friendly email API</p>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium text-gray-900">Setup Instructions:</h4>
                <ol className="space-y-3 text-sm text-gray-600">
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">1</span>
                    <span>Sign up at <a href="https://resend.com/signup" target="_blank" rel="noopener" className="text-rose-600 hover:underline">resend.com</a> (email verification only, no phone!)</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">2</span>
                    <span>Go to <a href="https://resend.com/api-keys" target="_blank" rel="noopener" className="text-rose-600 hover:underline">API Keys</a> and create a new key</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">3</span>
                    <span>Go to <a href="https://vercel.com/lumierecurves-projects/website/settings/environment-variables" target="_blank" rel="noopener" className="text-rose-600 hover:underline">Vercel settings</a></span>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">4</span>
                    <span>Add: <code className="bg-gray-100 px-2 py-0.5 rounded">RESEND_API_KEY</code> = your key</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">5</span>
                    <span>Redeploy for changes to take effect</span>
                  </li>
                </ol>
              </div>

              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h4 className="font-medium text-green-900 mb-1">Why Resend?</h4>
                <ul className="text-sm text-green-700 space-y-1">
                  <li>• No phone verification required</li>
                  <li>• Simple API, easy setup</li>
                  <li>• Great deliverability</li>
                  <li>• 3,000 emails/month free</li>
                </ul>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-blue-600 rounded-xl flex items-center justify-center">
                  <Mail className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Brevo (Sendinblue)</h3>
                  <p className="text-sm text-gray-500">Full marketing platform</p>
                </div>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium text-gray-900">Setup Instructions:</h4>
                <ol className="space-y-3 text-sm text-gray-600">
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">1</span>
                    <span>Sign up at <a href="https://www.brevo.com" target="_blank" rel="noopener" className="text-rose-600 hover:underline">brevo.com</a></span>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">2</span>
                    <span>Go to <a href="https://app.brevo.com/settings/keys/api" target="_blank" rel="noopener" className="text-rose-600 hover:underline">API Keys</a></span>
                  </li>
                  <li className="flex gap-3">
                    <span className="w-6 h-6 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center flex-shrink-0 font-medium">3</span>
                    <span>Add <code className="bg-gray-100 px-2 py-0.5 rounded">BREVO_API_KEY</code> to Vercel</span>
                  </li>
                </ol>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <h4 className="font-medium text-blue-900 mb-1">Free Plan:</h4>
                <ul className="text-sm text-blue-700 space-y-1">
                  <li>• 300 emails/day</li>
                  <li>• Contact management</li>
                  <li>• Email templates</li>
                </ul>
              </div>
            </>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={checkConnection}
            disabled={checking}
            className="px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50 flex items-center gap-2"
          >
            {checking ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Checking...
              </>
            ) : (
              <>
                <Link className="w-4 h-4" />
                Check Connection
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function EmailCampaigns() {
  const [campaigns, setCampaigns] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [showSetupModal, setShowSetupModal] = useState(false)
  const [editingCampaign, setEditingCampaign] = useState(null)
  const [filter, setFilter] = useState('all')
  const [brevoStatus, setBrevoStatus] = useState(null)
  const [sendingId, setSendingId] = useState(null)

  useEffect(() => {
    loadCampaigns()
    checkBrevoConnection()
  }, [])

  const checkBrevoConnection = async () => {
    try {
      const response = await fetch('/api/email/contacts?action=stats')
      if (response.ok) {
        const data = await response.json()
        if (data.email) {
          setBrevoStatus({
            connected: true,
            email: data.email,
            plan: data.plan?.[0]?.type || 'Free',
            credits: data.plan?.[0]?.credits || 0
          })
        }
      }
    } catch (err) {
      console.error('Brevo check failed:', err)
    }
  }

  const loadCampaigns = async () => {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('email_campaigns')
        .select('*')
        .order('created_at', { ascending: false })
      if (error) throw error
      setCampaigns(data || [])
    } catch (err) {
      console.error('Error loading campaigns:', err)
      setCampaigns([])
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this campaign?')) return
    try {
      await supabase.from('email_campaigns').delete().eq('id', id)
      loadCampaigns()
    } catch (err) {
      console.error('Error deleting campaign:', err)
    }
  }

  const handleSend = async (campaign) => {
    if (!brevoStatus?.connected) {
      setShowSetupModal(true)
      return
    }

    if (!confirm(`Send "${campaign.name}" to all subscribers now?`)) return

    setSendingId(campaign.id)
    try {
      // Get subscribers from database
      const { data: customers } = await supabase
        .from('customers')
        .select('email, first_name')
        .limit(100)

      if (!customers || customers.length === 0) {
        alert('No subscribers found')
        return
      }

      // Send via Brevo
      const response = await fetch('/api/email/send-campaign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: customers.map(c => ({ email: c.email, name: c.first_name || '' })),
          subject: campaign.subject,
          htmlContent: campaign.content || `<p>${campaign.subject}</p>`,
          from: 'Lumière Curves <hello@lumierecurves.shop>'
        })
      })

      const result = await response.json()

      if (response.ok) {
        // Update campaign status
        await supabase
          .from('email_campaigns')
          .update({
            status: 'sent',
            sent_at: new Date().toISOString(),
            total_sent: customers.length
          })
          .eq('id', campaign.id)

        loadCampaigns()
        alert(`Campaign sent to ${customers.length} subscribers!`)
      } else {
        alert(`Failed to send: ${result.error}`)
      }
    } catch (err) {
      console.error('Error sending campaign:', err)
      alert('Failed to send campaign')
    } finally {
      setSendingId(null)
    }
  }

  const filteredCampaigns = campaigns.filter(c => {
    if (filter === 'all') return true
    return c.status === filter
  })

  // Stats
  const totalSent = campaigns.filter(c => c.status === 'sent').reduce((sum, c) => sum + (c.total_sent || 0), 0)
  const totalOpened = campaigns.reduce((sum, c) => sum + (c.total_opened || 0), 0)
  const totalClicked = campaigns.reduce((sum, c) => sum + (c.total_clicked || 0), 0)
  const avgOpenRate = totalSent > 0 ? ((totalOpened / totalSent) * 100).toFixed(1) : 0

  const statusColors = {
    draft: 'bg-gray-100 text-gray-700',
    scheduled: 'bg-blue-100 text-blue-700',
    sending: 'bg-yellow-100 text-yellow-700',
    sent: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Email Campaigns</h1>
          <p className="text-gray-500 mt-1">Create and manage email marketing campaigns</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {brevoStatus?.connected ? (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-sm">
              <CheckCircle className="w-4 h-4" />
              {brevoStatus.provider === 'resend' ? 'Resend' : 'Brevo'} Connected
            </div>
          ) : (
            <button
              onClick={() => setShowSetupModal(true)}
              className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <Settings className="w-4 h-4" />
              Connect Brevo
            </button>
          )}
          <button
            onClick={() => { setEditingCampaign(null); setShowModal(true) }}
            className="flex items-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
          >
            <Plus className="w-4 h-4" />
            Create Campaign
          </button>
        </div>
      </div>

      {/* Brevo Warning */}
      {!brevoStatus?.connected && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-start gap-4">
          <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-medium text-yellow-800">Email Service Not Connected</h3>
            <p className="text-sm text-yellow-700 mt-1">
              Connect Brevo to send real email campaigns. You can still create and save campaigns as drafts.
            </p>
          </div>
          <button
            onClick={() => setShowSetupModal(true)}
            className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-sm"
          >
            Setup Now
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Mail className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{campaigns.length}</p>
              <p className="text-xs text-gray-500">Total Campaigns</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Send className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalSent.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Emails Sent</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Eye className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{avgOpenRate}%</p>
              <p className="text-xs text-gray-500">Avg. Open Rate</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
              <MousePointer className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalClicked.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Total Clicks</p>
            </div>
          </div>
        </div>
      </div>

      {/* Email Service Account Info */}
      {brevoStatus?.connected && (
        <div className={`rounded-xl p-6 text-white ${
          brevoStatus.provider === 'resend'
            ? 'bg-gradient-to-r from-gray-800 to-gray-900'
            : 'bg-gradient-to-r from-blue-500 to-indigo-600'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <Mail className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">
                  {brevoStatus.provider === 'resend' ? 'Resend' : 'Brevo'} Account
                </h3>
                <p className="text-white/80 text-sm">{brevoStatus.email} • {brevoStatus.plan} Plan</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold">{brevoStatus.credits?.toLocaleString() || '100'}</p>
              <p className="text-white/80 text-sm">emails/day</p>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          {['all', 'draft', 'scheduled', 'sent'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                filter === f
                  ? 'bg-rose-100 text-rose-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>
        <button
          onClick={loadCampaigns}
          className="ml-auto p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Campaigns List */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredCampaigns.length === 0 ? (
          <div className="text-center py-12">
            <Mail className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 mb-4">No campaigns yet</p>
            <button
              onClick={() => { setEditingCampaign(null); setShowModal(true) }}
              className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
            >
              Create Your First Campaign
            </button>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredCampaigns.map(campaign => {
              const typeConfig = campaignTypes.find(t => t.id === campaign.type) || campaignTypes[0]
              const TypeIcon = typeConfig.icon
              const isSending = sendingId === campaign.id

              return (
                <div key={campaign.id} className="p-4 hover:bg-gray-50">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 bg-${typeConfig.color}-100 rounded-xl flex items-center justify-center`}>
                      <TypeIcon className={`w-6 h-6 text-${typeConfig.color}-600`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900">{campaign.name}</h3>
                        <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[campaign.status]}`}>
                          {campaign.status}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500 truncate">{campaign.subject}</p>
                      <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
                        {campaign.scheduled_at && (
                          <span className="flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {new Date(campaign.scheduled_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                          </span>
                        )}
                        {campaign.total_sent > 0 && (
                          <>
                            <span>{campaign.total_sent} sent</span>
                            <span>{campaign.total_opened || 0} opened</span>
                            <span>{campaign.total_clicked || 0} clicked</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {campaign.status === 'draft' && (
                        <button
                          onClick={() => handleSend(campaign)}
                          disabled={isSending}
                          className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
                        >
                          {isSending ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4" />
                          )}
                          {isSending ? 'Sending...' : 'Send'}
                        </button>
                      )}
                      <button
                        onClick={() => { setEditingCampaign(campaign); setShowModal(true) }}
                        className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(campaign.id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Email Templates */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Email Templates</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {emailTemplates.map(template => (
            <div key={template.id} className="border border-gray-200 rounded-lg p-4 hover:border-rose-300 transition-colors">
              <h4 className="font-medium text-gray-900">{template.name}</h4>
              <p className="text-sm text-gray-500 mt-1">{template.subject}</p>
              <button
                onClick={() => {
                  setEditingCampaign(null)
                  setShowModal(true)
                }}
                className="mt-3 text-sm text-rose-600 hover:text-rose-700 font-medium"
              >
                Use Template →
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Modals */}
      {showModal && (
        <CreateCampaignModal
          campaign={editingCampaign}
          onClose={() => { setShowModal(false); setEditingCampaign(null) }}
          onSave={loadCampaigns}
          brevoConnected={brevoStatus?.connected}
        />
      )}

      {showSetupModal && (
        <EmailSetupModal
          onClose={() => setShowSetupModal(false)}
          onConnect={(status) => setBrevoStatus({ ...status, connected: true })}
        />
      )}
    </div>
  )
}
