import { useState, useEffect } from 'react'
import {
  Search,
  Download,
  Eye,
  Mail,
  Phone,
  MapPin,
  ShoppingBag,
  Calendar,
  Tag,
  X,
  RefreshCw,
  User,
  IndianRupee,
  TrendingUp,
  Filter,
  Plus,
  Edit2,
  Trash2,
  ChevronRight
} from 'lucide-react'
import { db, supabase } from '../lib/supabase'

const tagColors = {
  'VIP': 'bg-purple-100 text-purple-700',
  'New': 'bg-blue-100 text-blue-700',
  'Loyal': 'bg-green-100 text-green-700',
  'At Risk': 'bg-orange-100 text-orange-700',
  'Churned': 'bg-red-100 text-red-700',
  'High Value': 'bg-yellow-100 text-yellow-700'
}

function CustomerDetailModal({ customer, onClose, onUpdate }) {
  const [orders, setOrders] = useState([])
  const [loadingOrders, setLoadingOrders] = useState(true)
  const [notes, setNotes] = useState(customer?.notes || '')
  const [tags, setTags] = useState(customer?.tags || [])
  const [newTag, setNewTag] = useState('')
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (customer?.id) {
      loadCustomerOrders()
    }
  }, [customer?.id])

  const loadCustomerOrders = async () => {
    setLoadingOrders(true)
    try {
      const { data, error } = await supabase
        .from('orders')
        .select('*, order_items(*)')
        .eq('customer_id', customer.id)
        .order('created_at', { ascending: false })
      if (error) throw error
      setOrders(data || [])
    } catch (err) {
      console.error('Error loading customer orders:', err)
    } finally {
      setLoadingOrders(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await supabase
        .from('customers')
        .update({ notes, tags, updated_at: new Date().toISOString() })
        .eq('id', customer.id)
      onUpdate()
      onClose()
    } catch (err) {
      console.error('Error updating customer:', err)
    } finally {
      setSaving(false)
    }
  }

  const addTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()])
      setNewTag('')
    }
  }

  const removeTag = (tagToRemove) => {
    setTags(tags.filter(t => t !== tagToRemove))
  }

  if (!customer) return null

  const defaultAddress = customer.addresses?.[customer.default_address_index || 0]

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-rose-500 to-rose-600 rounded-full flex items-center justify-center text-white text-xl font-bold">
              {customer.first_name?.[0]}{customer.last_name?.[0] || ''}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {customer.first_name} {customer.last_name}
              </h2>
              <p className="text-sm text-gray-500">Customer since {new Date(customer.created_at).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' })}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-200">
          <div className="flex gap-6 px-6">
            {['overview', 'orders', 'notes'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-3 border-b-2 text-sm font-medium capitalize transition-colors ${
                  activeTab === tab
                    ? 'border-rose-500 text-rose-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Stats Cards */}
              <div className="md:col-span-2 grid grid-cols-3 gap-4">
                <div className="bg-gradient-to-br from-rose-50 to-rose-100 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-rose-600 mb-1">
                    <ShoppingBag className="w-4 h-4" />
                    <span className="text-xs font-medium">Total Orders</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">{customer.total_orders || 0}</p>
                </div>
                <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-green-600 mb-1">
                    <IndianRupee className="w-4 h-4" />
                    <span className="text-xs font-medium">Total Spent</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">₹{parseFloat(customer.total_spent || 0).toLocaleString()}</p>
                </div>
                <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4">
                  <div className="flex items-center gap-2 text-blue-600 mb-1">
                    <TrendingUp className="w-4 h-4" />
                    <span className="text-xs font-medium">Avg. Order</span>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">₹{parseFloat(customer.average_order_value || 0).toLocaleString()}</p>
                </div>
              </div>

              {/* Contact Info */}
              <div className="bg-gray-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Contact Information</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-3 text-sm">
                    <Mail className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-600">{customer.email}</span>
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <Phone className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-600">{customer.phone || 'Not provided'}</span>
                  </div>
                  {customer.date_of_birth && (
                    <div className="flex items-center gap-3 text-sm">
                      <Calendar className="w-4 h-4 text-gray-400" />
                      <span className="text-gray-600">{new Date(customer.date_of_birth).toLocaleDateString('en-IN')}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Default Address */}
              <div className="bg-gray-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Default Address</h3>
                {defaultAddress ? (
                  <div className="flex items-start gap-3 text-sm">
                    <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                    <div className="text-gray-600">
                      <p>{defaultAddress.address}</p>
                      <p>{defaultAddress.city}, {defaultAddress.state}</p>
                      <p>{defaultAddress.pincode}</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No address saved</p>
                )}
              </div>

              {/* Tags */}
              <div className="md:col-span-2 bg-gray-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Customer Tags</h3>
                <div className="flex flex-wrap gap-2 mb-3">
                  {tags.map(tag => (
                    <span
                      key={tag}
                      className={`inline-flex items-center gap-1 px-3 py-1 text-sm font-medium rounded-full ${tagColors[tag] || 'bg-gray-100 text-gray-700'}`}
                    >
                      {tag}
                      <button onClick={() => removeTag(tag)} className="hover:text-red-500">
                        <X className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && addTag()}
                    placeholder="Add tag..."
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-rose-500"
                  />
                  <button
                    onClick={addTag}
                    className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 text-sm"
                  >
                    Add
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {Object.keys(tagColors).filter(t => !tags.includes(t)).map(presetTag => (
                    <button
                      key={presetTag}
                      onClick={() => setTags([...tags, presetTag])}
                      className={`px-2 py-1 text-xs rounded-full border-2 border-dashed ${tagColors[presetTag]} opacity-50 hover:opacity-100`}
                    >
                      + {presetTag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Activity Timeline */}
              <div className="md:col-span-2 bg-gray-50 rounded-xl p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Activity</h3>
                <div className="space-y-3 text-sm">
                  {customer.last_order_at && (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                        <ShoppingBag className="w-4 h-4 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">Last Order</p>
                        <p className="text-gray-500">{new Date(customer.last_order_at).toLocaleDateString('en-IN', { dateStyle: 'full' })}</p>
                      </div>
                    </div>
                  )}
                  {customer.first_order_at && (
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                        <Calendar className="w-4 h-4 text-blue-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">First Order</p>
                        <p className="text-gray-500">{new Date(customer.first_order_at).toLocaleDateString('en-IN', { dateStyle: 'full' })}</p>
                      </div>
                    </div>
                  )}
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-purple-100 rounded-full flex items-center justify-center">
                      <User className="w-4 h-4 text-purple-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Account Created</p>
                      <p className="text-gray-500">{new Date(customer.created_at).toLocaleDateString('en-IN', { dateStyle: 'full' })}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'orders' && (
            <div>
              {loadingOrders ? (
                <div className="flex items-center justify-center h-48">
                  <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
              ) : orders.length === 0 ? (
                <div className="text-center py-12">
                  <ShoppingBag className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500">No orders yet</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {orders.map(order => (
                    <div key={order.id} className="bg-gray-50 rounded-xl p-4 hover:bg-gray-100 transition-colors">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-gray-900">{order.order_number}</span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                            order.status === 'delivered' ? 'bg-green-100 text-green-700' :
                            order.status === 'shipped' ? 'bg-blue-100 text-blue-700' :
                            order.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                            'bg-yellow-100 text-yellow-700'
                          }`}>
                            {order.status}
                          </span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {new Date(order.created_at).toLocaleDateString('en-IN', { dateStyle: 'medium' })}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">{order.order_items?.length || 0} items</span>
                        <span className="font-semibold text-gray-900">₹{parseFloat(order.total).toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {activeTab === 'notes' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Customer Notes</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes about this customer..."
                rows={6}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-rose-500 resize-none"
              />
              <p className="text-xs text-gray-500 mt-2">Notes are only visible to admins</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={() => window.location.href = `mailto:${customer.email}`}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <Mail className="w-4 h-4" />
            Send Email
          </button>
          <div className="flex items-center gap-3">
            <button onClick={onClose} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Customers() {
  const [customers, setCustomers] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCustomer, setSelectedCustomer] = useState(null)
  const [sortBy, setSortBy] = useState('created_at')
  const [filterTag, setFilterTag] = useState('')

  useEffect(() => {
    loadCustomers()
  }, [])

  const loadCustomers = async () => {
    setLoading(true)
    try {
      const { data, error } = await db.getCustomers()
      if (error) throw error
      setCustomers(data || [])
    } catch (err) {
      console.error('Error loading customers:', err)
    } finally {
      setLoading(false)
    }
  }

  const filteredCustomers = customers
    .filter(customer => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        const match = (
          customer.email?.toLowerCase().includes(query) ||
          customer.first_name?.toLowerCase().includes(query) ||
          customer.last_name?.toLowerCase().includes(query) ||
          customer.phone?.includes(query)
        )
        if (!match) return false
      }
      if (filterTag && !customer.tags?.includes(filterTag)) return false
      return true
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'total_spent':
          return (parseFloat(b.total_spent) || 0) - (parseFloat(a.total_spent) || 0)
        case 'total_orders':
          return (b.total_orders || 0) - (a.total_orders || 0)
        case 'name':
          return (a.first_name || '').localeCompare(b.first_name || '')
        default:
          return new Date(b.created_at) - new Date(a.created_at)
      }
    })

  const exportCustomers = () => {
    const csv = [
      ['Email', 'First Name', 'Last Name', 'Phone', 'Total Orders', 'Total Spent', 'Tags', 'Created At'].join(','),
      ...filteredCustomers.map(c => [
        c.email,
        c.first_name,
        c.last_name,
        c.phone,
        c.total_orders || 0,
        c.total_spent || 0,
        (c.tags || []).join(';'),
        c.created_at
      ].join(','))
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `customers-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  // Get stats
  const totalCustomers = customers.length
  const totalRevenue = customers.reduce((sum, c) => sum + (parseFloat(c.total_spent) || 0), 0)
  const avgOrderValue = totalRevenue / (customers.reduce((sum, c) => sum + (c.total_orders || 0), 0) || 1)
  const newThisMonth = customers.filter(c => {
    const created = new Date(c.created_at)
    const now = new Date()
    return created.getMonth() === now.getMonth() && created.getFullYear() === now.getFullYear()
  }).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Customers</h1>
          <p className="text-gray-500 mt-1">Manage your customer relationships</p>
        </div>
        <button
          onClick={exportCustomers}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
              <User className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalCustomers}</p>
              <p className="text-xs text-gray-500">Total Customers</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <IndianRupee className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{totalRevenue.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Total Revenue</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{avgOrderValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
              <p className="text-xs text-gray-500">Avg. Order Value</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Plus className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{newThisMonth}</p>
              <p className="text-xs text-gray-500">New This Month</p>
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
            placeholder="Search customers..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
          />
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500"
        >
          <option value="created_at">Newest First</option>
          <option value="total_spent">Highest Spent</option>
          <option value="total_orders">Most Orders</option>
          <option value="name">Name (A-Z)</option>
        </select>
        <select
          value={filterTag}
          onChange={(e) => setFilterTag(e.target.value)}
          className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500"
        >
          <option value="">All Tags</option>
          {Object.keys(tagColors).map(tag => (
            <option key={tag} value={tag}>{tag}</option>
          ))}
        </select>
        <button
          onClick={loadCustomers}
          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Customers Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredCustomers.length === 0 ? (
          <div className="text-center py-12">
            <User className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No customers found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Contact</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Orders</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total Spent</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tags</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Order</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filteredCustomers.map(customer => (
                  <tr key={customer.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-rose-500 to-rose-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                          {customer.first_name?.[0]}{customer.last_name?.[0] || ''}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{customer.first_name} {customer.last_name}</p>
                          <p className="text-xs text-gray-500">ID: {customer.id}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm text-gray-900">{customer.email}</p>
                      <p className="text-xs text-gray-500">{customer.phone || '-'}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-medium text-gray-900">{customer.total_orders || 0}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm font-medium text-gray-900">
                        ₹{parseFloat(customer.total_spent || 0).toLocaleString()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {customer.tags?.slice(0, 2).map(tag => (
                          <span
                            key={tag}
                            className={`px-2 py-0.5 text-xs font-medium rounded-full ${tagColors[tag] || 'bg-gray-100 text-gray-700'}`}
                          >
                            {tag}
                          </span>
                        ))}
                        {customer.tags?.length > 2 && (
                          <span className="px-2 py-0.5 text-xs text-gray-500">+{customer.tags.length - 2}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {customer.last_order_at
                        ? new Date(customer.last_order_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: '2-digit' })
                        : '-'
                      }
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSelectedCustomer(customer)}
                        className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Customer Detail Modal */}
      {selectedCustomer && (
        <CustomerDetailModal
          customer={selectedCustomer}
          onClose={() => setSelectedCustomer(null)}
          onUpdate={loadCustomers}
        />
      )}
    </div>
  )
}
