import { useState, useEffect } from 'react'
import {
  Store,
  Plus,
  Settings,
  RefreshCw,
  Check,
  X,
  AlertCircle,
  ExternalLink,
  Package,
  ShoppingBag,
  TrendingUp,
  IndianRupee,
  Link,
  Unlink,
  Eye,
  Edit2,
  Trash2,
  Clock,
  CheckCircle,
  XCircle,
  Upload,
  Download,
  Filter,
  ChevronRight
} from 'lucide-react'
import { db, supabase } from '../lib/supabase'

// Marketplace configurations
const marketplaceConfigs = [
  {
    id: 'amazon',
    name: 'Amazon India',
    logo: '🛒',
    color: 'orange',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-600',
    borderColor: 'border-orange-200',
    commission: '10-17%',
    description: 'Largest e-commerce platform in India',
    features: ['FBA fulfillment', 'Prime eligibility', 'Sponsored ads'],
    setupUrl: 'https://sellercentral.amazon.in',
    apiDocs: 'https://developer-docs.amazon.com/sp-api'
  },
  {
    id: 'flipkart',
    name: 'Flipkart',
    logo: '🛍️',
    color: 'blue',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-600',
    borderColor: 'border-blue-200',
    commission: '8-20%',
    description: 'India\'s leading marketplace by Walmart',
    features: ['Flipkart Fulfillment', 'SuperCoins rewards', 'Flipkart Ads'],
    setupUrl: 'https://seller.flipkart.com',
    apiDocs: 'https://seller.flipkart.com/api-docs'
  },
  {
    id: 'myntra',
    name: 'Myntra',
    logo: '👗',
    color: 'pink',
    bgColor: 'bg-pink-50',
    textColor: 'text-pink-600',
    borderColor: 'border-pink-200',
    commission: '15-25%',
    description: 'Fashion-focused platform by Flipkart',
    features: ['Fashion focus', 'Premium positioning', 'Style influencers'],
    setupUrl: 'https://partners.myntra.com',
    apiDocs: null
  },
  {
    id: 'ajio',
    name: 'Ajio',
    logo: '✨',
    color: 'purple',
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-600',
    borderColor: 'border-purple-200',
    commission: '20-30%',
    description: 'Reliance\'s fashion marketplace',
    features: ['Premium brands', 'AJIO Luxe', 'Good margins'],
    setupUrl: 'https://sellers.ajio.com',
    apiDocs: null
  },
  {
    id: 'nykaa',
    name: 'Nykaa Fashion',
    logo: '💄',
    color: 'rose',
    bgColor: 'bg-rose-50',
    textColor: 'text-rose-600',
    borderColor: 'border-rose-200',
    commission: '15-20%',
    description: 'Women-focused beauty & fashion',
    features: ['Women audience', 'Beauty cross-sell', 'Growing fast'],
    setupUrl: 'https://brands.nykaa.com',
    apiDocs: null
  },
  {
    id: 'meesho',
    name: 'Meesho',
    logo: '📱',
    color: 'indigo',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-600',
    borderColor: 'border-indigo-200',
    commission: '0%',
    description: 'Zero commission social commerce',
    features: ['Zero commission', 'Tier 2/3 reach', 'Reseller network'],
    setupUrl: 'https://supplier.meesho.com',
    apiDocs: 'https://supplier.meesho.com/api-docs'
  }
]

function ConnectMarketplaceModal({ marketplace, connection, onClose, onSave }) {
  const [formData, setFormData] = useState({
    seller_id: connection?.seller_id || '',
    api_key: connection?.api_credentials?.api_key || '',
    api_secret: connection?.api_credentials?.api_secret || '',
    sync_inventory: connection?.sync_inventory !== false,
    sync_orders: connection?.sync_orders !== false,
    is_active: connection?.is_active !== false
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      const payload = {
        marketplace: marketplace.id,
        display_name: marketplace.name,
        seller_id: formData.seller_id,
        api_credentials: {
          api_key: formData.api_key,
          api_secret: formData.api_secret
        },
        sync_inventory: formData.sync_inventory,
        sync_orders: formData.sync_orders,
        is_active: formData.is_active,
        sync_status: 'pending'
      }

      if (connection) {
        const { error: updateError } = await supabase
          .from('marketplace_connections')
          .update(payload)
          .eq('id', connection.id)
        if (updateError) throw updateError
      } else {
        const { error: insertError } = await supabase
          .from('marketplace_connections')
          .insert(payload)
        if (insertError) throw insertError
      }

      onSave()
      onClose()
    } catch (err) {
      console.error('Error saving connection:', err)
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 ${marketplace.bgColor} rounded-xl flex items-center justify-center text-2xl`}>
              {marketplace.logo}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">
                {connection ? 'Edit' : 'Connect'} {marketplace.name}
              </h2>
              <p className="text-sm text-gray-500">Commission: {marketplace.commission}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <div className="bg-gray-50 rounded-xl p-4">
            <h3 className="font-medium text-gray-900 mb-2">Setup Instructions</h3>
            <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
              <li>Register as a seller on {marketplace.name}</li>
              <li>Get your Seller ID from the dashboard</li>
              <li>Generate API credentials (if available)</li>
              <li>Enter the details below</li>
            </ol>
            <a
              href={marketplace.setupUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={`inline-flex items-center gap-1 mt-3 text-sm ${marketplace.textColor} hover:underline`}
            >
              Go to {marketplace.name} Seller Portal <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Seller ID *</label>
            <input
              type="text"
              value={formData.seller_id}
              onChange={(e) => setFormData({ ...formData, seller_id: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="Your seller/merchant ID"
              required
            />
          </div>

          {marketplace.apiDocs && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                <input
                  type="text"
                  value={formData.api_key}
                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                  placeholder="API key (optional)"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
                <input
                  type="password"
                  value={formData.api_secret}
                  onChange={(e) => setFormData({ ...formData, api_secret: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                  placeholder="API secret (optional)"
                />
              </div>
            </>
          )}

          <div className="space-y-3">
            <h3 className="font-medium text-gray-900">Sync Settings</h3>
            <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer">
              <div>
                <p className="font-medium text-gray-900">Sync Inventory</p>
                <p className="text-xs text-gray-500">Keep stock levels synchronized</p>
              </div>
              <input
                type="checkbox"
                checked={formData.sync_inventory}
                onChange={(e) => setFormData({ ...formData, sync_inventory: e.target.checked })}
                className="w-5 h-5 text-rose-600 rounded focus:ring-rose-500"
              />
            </label>
            <label className="flex items-center justify-between p-3 bg-gray-50 rounded-lg cursor-pointer">
              <div>
                <p className="font-medium text-gray-900">Sync Orders</p>
                <p className="text-xs text-gray-500">Import orders from marketplace</p>
              </div>
              <input
                type="checkbox"
                checked={formData.sync_orders}
                onChange={(e) => setFormData({ ...formData, sync_orders: e.target.checked })}
                className="w-5 h-5 text-rose-600 rounded focus:ring-rose-500"
              />
            </label>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 text-rose-600 rounded focus:ring-rose-500"
            />
            <label htmlFor="is_active" className="text-sm text-gray-700">Connection active</label>
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
              {saving ? 'Saving...' : connection ? 'Save Changes' : 'Connect'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function MarketplaceOrdersModal({ marketplace, onClose }) {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadOrders()
  }, [marketplace])

  const loadOrders = async () => {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('marketplace_orders')
        .select('*')
        .eq('marketplace', marketplace.id)
        .order('created_at', { ascending: false })
        .limit(50)
      if (error) throw error
      setOrders(data || [])
    } catch (err) {
      console.error('Error loading orders:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 ${marketplace.bgColor} rounded-xl flex items-center justify-center text-xl`}>
              {marketplace.logo}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">{marketplace.name} Orders</h2>
              <p className="text-sm text-gray-500">{orders.length} orders found</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : orders.length === 0 ? (
            <div className="text-center py-12">
              <ShoppingBag className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No orders from {marketplace.name} yet</p>
              <p className="text-sm text-gray-400 mt-1">Orders will appear here once synced</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Order ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Items</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map(order => (
                    <tr key={order.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-sm">{order.marketplace_order_id}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{order.buyer_name || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {order.items?.length || 0} items
                      </td>
                      <td className="px-4 py-3 font-medium">₹{parseFloat(order.total || 0).toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          order.marketplace_status === 'delivered' ? 'bg-green-100 text-green-700' :
                          order.marketplace_status === 'shipped' ? 'bg-blue-100 text-blue-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {order.marketplace_status || 'pending'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(order.created_at).toLocaleDateString('en-IN', { dateStyle: 'short' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ProductSyncModal({ marketplace, onClose }) {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [selectedProducts, setSelectedProducts] = useState([])

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('products')
        .select('*')
        .eq('is_active', true)
        .order('name')
      if (error) throw error
      setProducts(data || [])
    } catch (err) {
      console.error('Error loading products:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    // Simulate sync - in production, this would call marketplace APIs
    await new Promise(resolve => setTimeout(resolve, 2000))
    setSyncing(false)
    alert(`${selectedProducts.length || products.length} products queued for sync to ${marketplace.name}`)
    onClose()
  }

  const toggleProduct = (id) => {
    if (selectedProducts.includes(id)) {
      setSelectedProducts(selectedProducts.filter(p => p !== id))
    } else {
      setSelectedProducts([...selectedProducts, id])
    }
  }

  const toggleAll = () => {
    if (selectedProducts.length === products.length) {
      setSelectedProducts([])
    } else {
      setSelectedProducts(products.map(p => p.id))
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 ${marketplace.bgColor} rounded-xl flex items-center justify-center text-xl`}>
              {marketplace.logo}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Sync Products to {marketplace.name}</h2>
              <p className="text-sm text-gray-500">Select products to sync</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {loading ? (
            <div className="flex items-center justify-center h-48">
              <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedProducts.length === products.length}
                  onChange={toggleAll}
                  className="w-5 h-5 text-rose-600 rounded focus:ring-rose-500"
                />
                <span className="font-medium text-gray-900">Select All ({products.length} products)</span>
              </label>

              {products.map(product => (
                <label key={product.id} className="flex items-center gap-3 p-3 bg-white border border-gray-100 rounded-lg cursor-pointer hover:bg-gray-50">
                  <input
                    type="checkbox"
                    checked={selectedProducts.includes(product.id)}
                    onChange={() => toggleProduct(product.id)}
                    className="w-5 h-5 text-rose-600 rounded focus:ring-rose-500"
                  />
                  <div className="w-12 h-12 bg-gray-100 rounded-lg overflow-hidden flex-shrink-0">
                    {product.images?.[0] ? (
                      <img src={product.images[0]} alt={product.name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Package className="w-5 h-5 text-gray-400" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{product.name}</p>
                    <p className="text-sm text-gray-500">SKU: {product.sku} | ₹{product.price}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    product.stock_quantity > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {product.stock_quantity > 0 ? `${product.stock_quantity} in stock` : 'Out of stock'}
                  </span>
                </label>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <p className="text-sm text-gray-500">
            {selectedProducts.length > 0 ? `${selectedProducts.length} products selected` : 'All products will be synced'}
          </p>
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
            >
              <Upload className="w-4 h-4" />
              {syncing ? 'Syncing...' : 'Sync Products'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Marketplace() {
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(true)
  const [connectingMarketplace, setConnectingMarketplace] = useState(null)
  const [editingConnection, setEditingConnection] = useState(null)
  const [viewingOrders, setViewingOrders] = useState(null)
  const [syncingProducts, setSyncingProducts] = useState(null)
  const [syncing, setSyncing] = useState(null)

  useEffect(() => {
    loadConnections()
  }, [])

  const loadConnections = async () => {
    setLoading(true)
    try {
      const { data, error } = await db.getMarketplaceConnections()
      if (error) throw error
      setConnections(data || [])
    } catch (err) {
      console.error('Error loading connections:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDisconnect = async (connectionId) => {
    if (!confirm('Are you sure you want to disconnect this marketplace?')) return

    try {
      await supabase.from('marketplace_connections').delete().eq('id', connectionId)
      loadConnections()
    } catch (err) {
      console.error('Error disconnecting:', err)
    }
  }

  const handleSync = async (connection) => {
    setSyncing(connection.id)
    try {
      // Simulate sync
      await new Promise(resolve => setTimeout(resolve, 2000))
      await supabase
        .from('marketplace_connections')
        .update({
          last_sync_at: new Date().toISOString(),
          sync_status: 'success'
        })
        .eq('id', connection.id)
      loadConnections()
    } catch (err) {
      console.error('Error syncing:', err)
    } finally {
      setSyncing(null)
    }
  }

  const getConnection = (marketplaceId) => {
    return connections.find(c => c.marketplace === marketplaceId)
  }

  // Calculate stats
  const connectedCount = connections.filter(c => c.is_active).length
  const totalOrders = 0 // Would come from marketplace_orders count
  const totalRevenue = 0 // Would come from marketplace_orders sum

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Marketplace Integrations</h1>
          <p className="text-gray-500 mt-1">Connect and manage your sales channels</p>
        </div>
        <button
          onClick={loadConnections}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Link className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{connectedCount}</p>
              <p className="text-xs text-gray-500">Connected</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Store className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{marketplaceConfigs.length}</p>
              <p className="text-xs text-gray-500">Available</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <ShoppingBag className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalOrders}</p>
              <p className="text-xs text-gray-500">Marketplace Orders</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
              <IndianRupee className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{totalRevenue.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Revenue</p>
            </div>
          </div>
        </div>
      </div>

      {/* Marketplaces Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {marketplaceConfigs.map(marketplace => {
          const connection = getConnection(marketplace.id)
          const isConnected = connection?.is_active
          const isSyncing = syncing === connection?.id

          return (
            <div
              key={marketplace.id}
              className={`bg-white rounded-xl border-2 overflow-hidden transition-all ${
                isConnected ? marketplace.borderColor : 'border-gray-100'
              }`}
            >
              {/* Header */}
              <div className={`p-4 ${isConnected ? marketplace.bgColor : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="text-3xl">{marketplace.logo}</div>
                    <div>
                      <h3 className="font-bold text-gray-900">{marketplace.name}</h3>
                      <p className="text-xs text-gray-500">Commission: {marketplace.commission}</p>
                    </div>
                  </div>
                  {isConnected && (
                    <span className="flex items-center gap-1 px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                      <CheckCircle className="w-3 h-3" />
                      Connected
                    </span>
                  )}
                </div>
              </div>

              {/* Body */}
              <div className="p-4">
                <p className="text-sm text-gray-600 mb-3">{marketplace.description}</p>

                {/* Features */}
                <div className="flex flex-wrap gap-1 mb-4">
                  {marketplace.features.map((feature, i) => (
                    <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
                      {feature}
                    </span>
                  ))}
                </div>

                {/* Connection Status */}
                {isConnected && (
                  <div className="bg-gray-50 rounded-lg p-3 mb-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Seller ID</span>
                      <span className="font-mono">{connection.seller_id}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm mt-1">
                      <span className="text-gray-500">Last Sync</span>
                      <span className="text-gray-900">
                        {connection.last_sync_at
                          ? new Date(connection.last_sync_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })
                          : 'Never'
                        }
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm mt-1">
                      <span className="text-gray-500">Status</span>
                      <span className={`flex items-center gap-1 ${
                        connection.sync_status === 'success' ? 'text-green-600' :
                        connection.sync_status === 'error' ? 'text-red-600' :
                        'text-yellow-600'
                      }`}>
                        {connection.sync_status === 'success' ? <CheckCircle className="w-3 h-3" /> :
                         connection.sync_status === 'error' ? <XCircle className="w-3 h-3" /> :
                         <Clock className="w-3 h-3" />
                        }
                        {connection.sync_status || 'pending'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="space-y-2">
                  {isConnected ? (
                    <>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSync(connection)}
                          disabled={isSyncing}
                          className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 ${marketplace.bgColor} ${marketplace.textColor} rounded-lg hover:opacity-80 disabled:opacity-50`}
                        >
                          <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} />
                          {isSyncing ? 'Syncing...' : 'Sync Now'}
                        </button>
                        <button
                          onClick={() => setViewingOrders(marketplace)}
                          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
                          title="View Orders"
                        >
                          <ShoppingBag className="w-4 h-4 text-gray-600" />
                        </button>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => setSyncingProducts(marketplace)}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700"
                        >
                          <Upload className="w-4 h-4" />
                          Sync Products
                        </button>
                        <button
                          onClick={() => { setEditingConnection(connection); setConnectingMarketplace(marketplace) }}
                          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
                          title="Settings"
                        >
                          <Settings className="w-4 h-4 text-gray-600" />
                        </button>
                        <button
                          onClick={() => handleDisconnect(connection.id)}
                          className="p-2 border border-red-200 rounded-lg hover:bg-red-50"
                          title="Disconnect"
                        >
                          <Unlink className="w-4 h-4 text-red-600" />
                        </button>
                      </div>
                    </>
                  ) : (
                    <button
                      onClick={() => { setEditingConnection(null); setConnectingMarketplace(marketplace) }}
                      className={`w-full flex items-center justify-center gap-2 px-4 py-2 ${marketplace.bgColor} ${marketplace.textColor} rounded-lg hover:opacity-80`}
                    >
                      <Plus className="w-4 h-4" />
                      Connect {marketplace.name}
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Info Panel */}
      <div className="bg-gradient-to-r from-rose-500 to-rose-600 rounded-xl p-6 text-white">
        <h3 className="text-lg font-semibold mb-3">Multi-Channel Selling Tips</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/10 rounded-lg p-4">
            <h4 className="font-medium mb-1">Keep Inventory Synced</h4>
            <p className="text-sm opacity-90">Enable auto-sync to prevent overselling across channels</p>
          </div>
          <div className="bg-white/10 rounded-lg p-4">
            <h4 className="font-medium mb-1">Optimize Listings</h4>
            <p className="text-sm opacity-90">Each marketplace has different requirements for titles & images</p>
          </div>
          <div className="bg-white/10 rounded-lg p-4">
            <h4 className="font-medium mb-1">Monitor Fees</h4>
            <p className="text-sm opacity-90">Commission rates vary by category and marketplace</p>
          </div>
        </div>
      </div>

      {/* Connect Modal */}
      {connectingMarketplace && (
        <ConnectMarketplaceModal
          marketplace={connectingMarketplace}
          connection={editingConnection}
          onClose={() => { setConnectingMarketplace(null); setEditingConnection(null) }}
          onSave={loadConnections}
        />
      )}

      {/* Orders Modal */}
      {viewingOrders && (
        <MarketplaceOrdersModal
          marketplace={viewingOrders}
          onClose={() => setViewingOrders(null)}
        />
      )}

      {/* Product Sync Modal */}
      {syncingProducts && (
        <ProductSyncModal
          marketplace={syncingProducts}
          onClose={() => setSyncingProducts(null)}
        />
      )}
    </div>
  )
}
