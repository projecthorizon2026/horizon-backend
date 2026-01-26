import { useState, useEffect } from 'react'
import {
  Search,
  Download,
  Plus,
  Edit2,
  Trash2,
  X,
  RefreshCw,
  Users2,
  MousePointer,
  ShoppingBag,
  IndianRupee,
  Copy,
  Check,
  TrendingUp,
  Link,
  Eye,
  ExternalLink
} from 'lucide-react'
import { db, supabase } from '../lib/supabase'

function CreateAffiliateModal({ affiliate, onClose, onSave }) {
  const [formData, setFormData] = useState({
    name: affiliate?.name || '',
    email: affiliate?.email || '',
    phone: affiliate?.phone || '',
    affiliate_code: affiliate?.affiliate_code || '',
    commission_type: affiliate?.commission_type || 'percentage',
    commission_value: affiliate?.commission_value || 10,
    is_active: affiliate?.is_active !== false
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const generateCode = () => {
    const code = formData.name
      .split(' ')[0]
      .toUpperCase()
      .substring(0, 6) + Math.floor(Math.random() * 100)
    setFormData({ ...formData, affiliate_code: code })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      if (affiliate) {
        // Update existing
        const { error: updateError } = await supabase
          .from('affiliates')
          .update({
            ...formData,
            updated_at: new Date().toISOString()
          })
          .eq('id', affiliate.id)
        if (updateError) throw updateError
      } else {
        // Create new
        const { error: insertError } = await supabase
          .from('affiliates')
          .insert(formData)
        if (insertError) throw insertError
      }
      onSave()
      onClose()
    } catch (err) {
      console.error('Error saving affiliate:', err)
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">
            {affiliate ? 'Edit Affiliate' : 'Add New Affiliate'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Affiliate Code *</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={formData.affiliate_code}
                onChange={(e) => setFormData({ ...formData, affiliate_code: e.target.value.toUpperCase() })}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500 uppercase"
                required
              />
              <button
                type="button"
                onClick={generateCode}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
              >
                Generate
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Commission Type</label>
              <select
                value={formData.commission_type}
                onChange={(e) => setFormData({ ...formData, commission_type: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              >
                <option value="percentage">Percentage</option>
                <option value="fixed">Fixed Amount</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Commission {formData.commission_type === 'percentage' ? '(%)' : '(₹)'}
              </label>
              <input
                type="number"
                value={formData.commission_value}
                onChange={(e) => setFormData({ ...formData, commission_value: parseFloat(e.target.value) })}
                min="0"
                step={formData.commission_type === 'percentage' ? '0.1' : '1'}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                required
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 text-rose-600 rounded focus:ring-rose-500"
            />
            <label htmlFor="is_active" className="text-sm text-gray-700">Active affiliate</label>
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
              {saving ? 'Saving...' : affiliate ? 'Save Changes' : 'Create Affiliate'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function AffiliateDetailModal({ affiliate, onClose }) {
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    loadEvents()
  }, [affiliate.id])

  const loadEvents = async () => {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('affiliate_events')
        .select('*, orders(order_number, total)')
        .eq('affiliate_id', affiliate.id)
        .order('created_at', { ascending: false })
        .limit(50)
      if (error) throw error
      setEvents(data || [])
    } catch (err) {
      console.error('Error loading events:', err)
    } finally {
      setLoading(false)
    }
  }

  const affiliateLink = `${window.location.origin}?ref=${affiliate.affiliate_code}`

  const copyLink = () => {
    navigator.clipboard.writeText(affiliateLink)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{affiliate.name}</h2>
            <p className="text-sm text-gray-500">{affiliate.email}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Stats Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-blue-50 rounded-xl p-4 text-center">
              <MousePointer className="w-5 h-5 text-blue-600 mx-auto mb-1" />
              <p className="text-2xl font-bold text-gray-900">{affiliate.total_clicks || 0}</p>
              <p className="text-xs text-gray-500">Total Clicks</p>
            </div>
            <div className="bg-green-50 rounded-xl p-4 text-center">
              <ShoppingBag className="w-5 h-5 text-green-600 mx-auto mb-1" />
              <p className="text-2xl font-bold text-gray-900">{affiliate.total_conversions || 0}</p>
              <p className="text-xs text-gray-500">Conversions</p>
            </div>
            <div className="bg-purple-50 rounded-xl p-4 text-center">
              <IndianRupee className="w-5 h-5 text-purple-600 mx-auto mb-1" />
              <p className="text-2xl font-bold text-gray-900">₹{parseFloat(affiliate.total_revenue || 0).toLocaleString()}</p>
              <p className="text-xs text-gray-500">Revenue</p>
            </div>
            <div className="bg-rose-50 rounded-xl p-4 text-center">
              <TrendingUp className="w-5 h-5 text-rose-600 mx-auto mb-1" />
              <p className="text-2xl font-bold text-gray-900">₹{parseFloat(affiliate.total_commission_earned || 0).toLocaleString()}</p>
              <p className="text-xs text-gray-500">Commission</p>
            </div>
          </div>

          {/* Affiliate Link */}
          <div className="bg-gray-50 rounded-xl p-4 mb-6">
            <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
              <Link className="w-4 h-4" />
              Affiliate Link
            </h3>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={affiliateLink}
                readOnly
                className="flex-1 px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm"
              />
              <button
                onClick={copyLink}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  copied ? 'bg-green-600 text-white' : 'bg-rose-600 text-white hover:bg-rose-700'
                }`}
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Code: <span className="font-mono font-bold">{affiliate.affiliate_code}</span> |
              Commission: {affiliate.commission_type === 'percentage'
                ? `${affiliate.commission_value}%`
                : `₹${affiliate.commission_value}`
              } per sale
            </p>
          </div>

          {/* Payout Summary */}
          <div className="bg-gradient-to-r from-rose-500 to-rose-600 rounded-xl p-4 text-white mb-6">
            <h3 className="font-semibold mb-3">Payout Summary</h3>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-sm opacity-90">Total Earned</p>
                <p className="text-xl font-bold">₹{parseFloat(affiliate.total_commission_earned || 0).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm opacity-90">Paid Out</p>
                <p className="text-xl font-bold">₹{parseFloat(affiliate.total_commission_paid || 0).toLocaleString()}</p>
              </div>
              <div>
                <p className="text-sm opacity-90">Pending</p>
                <p className="text-xl font-bold">
                  ₹{((affiliate.total_commission_earned || 0) - (affiliate.total_commission_paid || 0)).toLocaleString()}
                </p>
              </div>
            </div>
          </div>

          {/* Activity Log */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">Recent Activity</h3>
            {loading ? (
              <div className="flex items-center justify-center h-32">
                <div className="w-6 h-6 border-2 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : events.length === 0 ? (
              <div className="text-center py-8 text-gray-500">No activity yet</div>
            ) : (
              <div className="space-y-2">
                {events.map(event => (
                  <div key={event.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      event.event_type === 'conversion' ? 'bg-green-100' : 'bg-blue-100'
                    }`}>
                      {event.event_type === 'conversion' ? (
                        <ShoppingBag className="w-4 h-4 text-green-600" />
                      ) : (
                        <MousePointer className="w-4 h-4 text-blue-600" />
                      )}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 capitalize">{event.event_type}</p>
                      {event.orders && (
                        <p className="text-sm text-gray-500">
                          Order: {event.orders.order_number} | Value: ₹{parseFloat(event.order_value || 0).toLocaleString()}
                        </p>
                      )}
                    </div>
                    {event.commission_amount > 0 && (
                      <span className="text-green-600 font-semibold">+₹{parseFloat(event.commission_amount).toLocaleString()}</span>
                    )}
                    <span className="text-xs text-gray-400">
                      {new Date(event.created_at).toLocaleDateString('en-IN', { dateStyle: 'medium' })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Affiliates() {
  const [affiliates, setAffiliates] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingAffiliate, setEditingAffiliate] = useState(null)
  const [viewingAffiliate, setViewingAffiliate] = useState(null)
  const [copiedCode, setCopiedCode] = useState(null)

  useEffect(() => {
    loadAffiliates()
  }, [])

  const loadAffiliates = async () => {
    setLoading(true)
    try {
      const { data, error } = await db.getAffiliates()
      if (error) throw error
      setAffiliates(data || [])
    } catch (err) {
      console.error('Error loading affiliates:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this affiliate?')) return

    try {
      await supabase.from('affiliates').delete().eq('id', id)
      loadAffiliates()
    } catch (err) {
      console.error('Error deleting affiliate:', err)
    }
  }

  const copyCode = (code) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const filteredAffiliates = affiliates.filter(a => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      a.name?.toLowerCase().includes(query) ||
      a.email?.toLowerCase().includes(query) ||
      a.affiliate_code?.toLowerCase().includes(query)
    )
  })

  // Calculate totals
  const totalClicks = affiliates.reduce((sum, a) => sum + (a.total_clicks || 0), 0)
  const totalConversions = affiliates.reduce((sum, a) => sum + (a.total_conversions || 0), 0)
  const totalRevenue = affiliates.reduce((sum, a) => sum + parseFloat(a.total_revenue || 0), 0)
  const totalCommission = affiliates.reduce((sum, a) => sum + parseFloat(a.total_commission_earned || 0), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Affiliates</h1>
          <p className="text-gray-500 mt-1">Manage your affiliate marketing program</p>
        </div>
        <button
          onClick={() => { setEditingAffiliate(null); setShowModal(true) }}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
        >
          <Plus className="w-4 h-4" />
          Add Affiliate
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <MousePointer className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalClicks.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Total Clicks</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <ShoppingBag className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalConversions.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Conversions</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <IndianRupee className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{totalRevenue.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Revenue Generated</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{totalCommission.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Commission Paid</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[200px] max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search affiliates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
          />
        </div>
        <button
          onClick={loadAffiliates}
          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Affiliates Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredAffiliates.length === 0 ? (
          <div className="text-center py-12">
            <Users2 className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 mb-4">No affiliates found</p>
            <button
              onClick={() => { setEditingAffiliate(null); setShowModal(true) }}
              className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
            >
              Add Your First Affiliate
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Affiliate</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commission</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Clicks</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Conversions</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Revenue</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Earned</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filteredAffiliates.map(affiliate => (
                  <tr key={affiliate.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium text-gray-900">{affiliate.name}</p>
                        <p className="text-xs text-gray-500">{affiliate.email}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => copyCode(affiliate.affiliate_code)}
                        className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm font-mono hover:bg-gray-200"
                      >
                        {affiliate.affiliate_code}
                        {copiedCode === affiliate.affiliate_code ? (
                          <Check className="w-3 h-3 text-green-600" />
                        ) : (
                          <Copy className="w-3 h-3 text-gray-400" />
                        )}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {affiliate.commission_type === 'percentage'
                        ? `${affiliate.commission_value}%`
                        : `₹${affiliate.commission_value}`
                      }
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{affiliate.total_clicks || 0}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{affiliate.total_conversions || 0}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">
                      ₹{parseFloat(affiliate.total_revenue || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 font-medium text-green-600">
                      ₹{parseFloat(affiliate.total_commission_earned || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        affiliate.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                      }`}>
                        {affiliate.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setViewingAffiliate(affiliate)}
                          className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => { setEditingAffiliate(affiliate); setShowModal(true) }}
                          className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg"
                          title="Edit"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(affiliate.id)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <CreateAffiliateModal
          affiliate={editingAffiliate}
          onClose={() => { setShowModal(false); setEditingAffiliate(null) }}
          onSave={loadAffiliates}
        />
      )}

      {/* View Details Modal */}
      {viewingAffiliate && (
        <AffiliateDetailModal
          affiliate={viewingAffiliate}
          onClose={() => setViewingAffiliate(null)}
        />
      )}
    </div>
  )
}
