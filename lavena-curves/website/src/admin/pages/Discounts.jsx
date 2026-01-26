import { useState, useEffect } from 'react'
import {
  Search,
  Plus,
  Edit2,
  Trash2,
  X,
  RefreshCw,
  Percent,
  IndianRupee,
  Calendar,
  Copy,
  Check,
  Tag,
  Users,
  ShoppingBag,
  Clock,
  AlertCircle
} from 'lucide-react'
import { db, supabase } from '../lib/supabase'

function CreateDiscountModal({ discount, onClose, onSave }) {
  const [formData, setFormData] = useState({
    code: discount?.code || '',
    description: discount?.description || '',
    type: discount?.type || 'percentage',
    value: discount?.value || 10,
    min_order_value: discount?.min_order_value || 0,
    max_discount_amount: discount?.max_discount_amount || '',
    max_uses: discount?.max_uses || '',
    max_uses_per_customer: discount?.max_uses_per_customer || 1,
    valid_from: discount?.valid_from ? discount.valid_from.split('T')[0] : new Date().toISOString().split('T')[0],
    valid_until: discount?.valid_until ? discount.valid_until.split('T')[0] : '',
    is_active: discount?.is_active !== false
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const generateCode = () => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    let code = ''
    for (let i = 0; i < 8; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length))
    }
    setFormData({ ...formData, code })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    const payload = {
      ...formData,
      code: formData.code.toUpperCase(),
      max_discount_amount: formData.max_discount_amount || null,
      max_uses: formData.max_uses || null,
      valid_until: formData.valid_until || null
    }

    try {
      if (discount) {
        // Update existing
        const { error: updateError } = await supabase
          .from('discount_codes')
          .update(payload)
          .eq('id', discount.id)
        if (updateError) throw updateError
      } else {
        // Create new
        const { error: insertError } = await supabase
          .from('discount_codes')
          .insert(payload)
        if (insertError) throw insertError
      }
      onSave()
      onClose()
    } catch (err) {
      console.error('Error saving discount:', err)
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const previewDiscount = () => {
    if (formData.type === 'percentage') {
      return `${formData.value}% off`
    } else {
      return `₹${formData.value} off`
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">
            {discount ? 'Edit Discount' : 'Create Discount Code'}
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto max-h-[calc(90vh-140px)] space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          {/* Preview Card */}
          <div className="bg-gradient-to-r from-rose-500 to-rose-600 rounded-xl p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90">Discount Preview</p>
                <p className="text-2xl font-bold">{previewDiscount()}</p>
              </div>
              <div className="text-right">
                <p className="font-mono text-lg">{formData.code || 'CODE'}</p>
                {formData.min_order_value > 0 && (
                  <p className="text-sm opacity-90">Min. ₹{formData.min_order_value}</p>
                )}
              </div>
            </div>
          </div>

          {/* Code */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Discount Code *</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500 uppercase font-mono"
                placeholder="e.g., SAVE20"
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

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="e.g., 20% off for new customers"
            />
          </div>

          {/* Type & Value */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Discount Type</label>
              <select
                value={formData.type}
                onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              >
                <option value="percentage">Percentage (%)</option>
                <option value="fixed">Fixed Amount (₹)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Value {formData.type === 'percentage' ? '(%)' : '(₹)'} *
              </label>
              <input
                type="number"
                value={formData.value}
                onChange={(e) => setFormData({ ...formData, value: parseFloat(e.target.value) })}
                min="0"
                max={formData.type === 'percentage' ? 100 : undefined}
                step={formData.type === 'percentage' ? '1' : '10'}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                required
              />
            </div>
          </div>

          {/* Minimum Order & Max Discount */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Minimum Order (₹)</label>
              <input
                type="number"
                value={formData.min_order_value}
                onChange={(e) => setFormData({ ...formData, min_order_value: parseFloat(e.target.value) || 0 })}
                min="0"
                step="100"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                placeholder="0 = no minimum"
              />
            </div>
            {formData.type === 'percentage' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max Discount (₹)</label>
                <input
                  type="number"
                  value={formData.max_discount_amount}
                  onChange={(e) => setFormData({ ...formData, max_discount_amount: e.target.value })}
                  min="0"
                  step="100"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                  placeholder="No limit"
                />
              </div>
            )}
          </div>

          {/* Usage Limits */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Total Uses</label>
              <input
                type="number"
                value={formData.max_uses}
                onChange={(e) => setFormData({ ...formData, max_uses: e.target.value })}
                min="1"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                placeholder="Unlimited"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Per Customer</label>
              <input
                type="number"
                value={formData.max_uses_per_customer}
                onChange={(e) => setFormData({ ...formData, max_uses_per_customer: parseInt(e.target.value) || 1 })}
                min="1"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              />
            </div>
          </div>

          {/* Validity Dates */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valid From *</label>
              <input
                type="date"
                value={formData.valid_from}
                onChange={(e) => setFormData({ ...formData, valid_from: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Valid Until</label>
              <input
                type="date"
                value={formData.valid_until}
                onChange={(e) => setFormData({ ...formData, valid_until: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                min={formData.valid_from}
              />
            </div>
          </div>

          {/* Active Toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 text-rose-600 rounded focus:ring-rose-500"
            />
            <label htmlFor="is_active" className="text-sm text-gray-700">Active discount code</label>
          </div>

          {/* Actions */}
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
              {saving ? 'Saving...' : discount ? 'Save Changes' : 'Create Discount'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Discounts() {
  const [discounts, setDiscounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingDiscount, setEditingDiscount] = useState(null)
  const [copiedCode, setCopiedCode] = useState(null)
  const [filter, setFilter] = useState('all') // all, active, expired

  useEffect(() => {
    loadDiscounts()
  }, [])

  const loadDiscounts = async () => {
    setLoading(true)
    try {
      const { data, error } = await db.getDiscountCodes()
      if (error) throw error
      setDiscounts(data || [])
    } catch (err) {
      console.error('Error loading discounts:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this discount code?')) return

    try {
      await supabase.from('discount_codes').delete().eq('id', id)
      loadDiscounts()
    } catch (err) {
      console.error('Error deleting discount:', err)
    }
  }

  const copyCode = (code) => {
    navigator.clipboard.writeText(code)
    setCopiedCode(code)
    setTimeout(() => setCopiedCode(null), 2000)
  }

  const toggleActive = async (discount) => {
    try {
      await supabase
        .from('discount_codes')
        .update({ is_active: !discount.is_active })
        .eq('id', discount.id)
      loadDiscounts()
    } catch (err) {
      console.error('Error toggling discount:', err)
    }
  }

  const isExpired = (discount) => {
    if (!discount.valid_until) return false
    return new Date(discount.valid_until) < new Date()
  }

  const isUpcoming = (discount) => {
    return new Date(discount.valid_from) > new Date()
  }

  const filteredDiscounts = discounts.filter(d => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      if (!d.code?.toLowerCase().includes(query) && !d.description?.toLowerCase().includes(query)) {
        return false
      }
    }
    // Status filter
    if (filter === 'active') return d.is_active && !isExpired(d)
    if (filter === 'expired') return isExpired(d)
    return true
  })

  // Calculate stats
  const activeCount = discounts.filter(d => d.is_active && !isExpired(d)).length
  const totalUsed = discounts.reduce((sum, d) => sum + (d.used_count || 0), 0)
  const expiredCount = discounts.filter(d => isExpired(d)).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Discount Codes</h1>
          <p className="text-gray-500 mt-1">Create and manage promotional discount codes</p>
        </div>
        <button
          onClick={() => { setEditingDiscount(null); setShowModal(true) }}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
        >
          <Plus className="w-4 h-4" />
          Create Discount
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
              <Tag className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{discounts.length}</p>
              <p className="text-xs text-gray-500">Total Codes</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Check className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">{activeCount}</p>
              <p className="text-xs text-gray-500">Active</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <ShoppingBag className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalUsed}</p>
              <p className="text-xs text-gray-500">Times Used</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <Clock className="w-5 h-5 text-gray-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-500">{expiredCount}</p>
              <p className="text-xs text-gray-500">Expired</p>
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
            placeholder="Search discount codes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
          />
        </div>
        <div className="flex items-center gap-2">
          {['all', 'active', 'expired'].map(f => (
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
          onClick={loadDiscounts}
          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Discounts Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredDiscounts.length === 0 ? (
          <div className="text-center py-12">
            <Percent className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 mb-4">No discount codes found</p>
            <button
              onClick={() => { setEditingDiscount(null); setShowModal(true) }}
              className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
            >
              Create Your First Discount
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Discount</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Min Order</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Uses</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Validity</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filteredDiscounts.map(discount => {
                  const expired = isExpired(discount)
                  const upcoming = isUpcoming(discount)

                  return (
                    <tr key={discount.id} className={`border-b border-gray-100 hover:bg-gray-50 ${expired ? 'opacity-60' : ''}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copyCode(discount.code)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-gray-100 rounded-lg text-sm font-mono hover:bg-gray-200"
                          >
                            {discount.code}
                            {copiedCode === discount.code ? (
                              <Check className="w-3 h-3 text-green-600" />
                            ) : (
                              <Copy className="w-3 h-3 text-gray-400" />
                            )}
                          </button>
                        </div>
                        {discount.description && (
                          <p className="text-xs text-gray-500 mt-1">{discount.description}</p>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className="font-semibold text-rose-600">
                          {discount.type === 'percentage'
                            ? `${discount.value}% off`
                            : `₹${discount.value} off`
                          }
                        </span>
                        {discount.max_discount_amount && (
                          <p className="text-xs text-gray-500">Max ₹{discount.max_discount_amount}</p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {discount.min_order_value > 0 ? `₹${discount.min_order_value}` : 'No minimum'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {discount.used_count || 0}
                        {discount.max_uses && <span className="text-gray-400"> / {discount.max_uses}</span>}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        <div>
                          {new Date(discount.valid_from).toLocaleDateString('en-IN', { dateStyle: 'short' })}
                          {discount.valid_until && (
                            <span> - {new Date(discount.valid_until).toLocaleDateString('en-IN', { dateStyle: 'short' })}</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {expired ? (
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
                            Expired
                          </span>
                        ) : upcoming ? (
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-700">
                            Upcoming
                          </span>
                        ) : discount.is_active ? (
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-700">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">
                            Inactive
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => toggleActive(discount)}
                            className={`p-2 rounded-lg ${
                              discount.is_active
                                ? 'text-green-600 hover:bg-green-50'
                                : 'text-gray-400 hover:bg-gray-100'
                            }`}
                            title={discount.is_active ? 'Deactivate' : 'Activate'}
                          >
                            {discount.is_active ? (
                              <Check className="w-4 h-4" />
                            ) : (
                              <X className="w-4 h-4" />
                            )}
                          </button>
                          <button
                            onClick={() => { setEditingDiscount(discount); setShowModal(true) }}
                            className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(discount.id)}
                            className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <CreateDiscountModal
          discount={editingDiscount}
          onClose={() => { setShowModal(false); setEditingDiscount(null) }}
          onSave={loadDiscounts}
        />
      )}
    </div>
  )
}
