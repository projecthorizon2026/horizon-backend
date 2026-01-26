import { useState, useEffect } from 'react'
import {
  Truck,
  Plus,
  Search,
  RefreshCw,
  CheckCircle,
  XCircle,
  ExternalLink,
  Package,
  DollarSign,
  TrendingUp,
  AlertTriangle,
  Settings,
  Link,
  Unlink,
  X,
  MapPin,
  Clock,
  Star,
  ShoppingBag,
  Percent,
  ArrowRight,
  Eye,
  Copy,
  Edit2
} from 'lucide-react'
import { supabase } from '../lib/supabase'

const suppliers = [
  {
    id: 'glowroad',
    name: 'GlowRoad',
    logo: '🌟',
    description: 'India\'s largest reseller platform with 50,000+ products',
    categories: ['Fashion', 'Beauty', 'Home', 'Electronics'],
    avgDelivery: '3-7 days',
    minOrder: 'No minimum',
    commission: '15-30%',
    rating: 4.2,
    features: ['COD Support', 'Pan-India Delivery', 'Easy Returns', 'Real-time Tracking']
  },
  {
    id: 'meesho',
    name: 'Meesho',
    logo: '🛒',
    description: 'Social commerce platform with direct supplier connections',
    categories: ['Women\'s Fashion', 'Men\'s Fashion', 'Kids', 'Home'],
    avgDelivery: '4-8 days',
    minOrder: '₹99',
    commission: '10-25%',
    rating: 4.0,
    features: ['Zero Commission on some products', 'Quality Check', 'Supplier Verification']
  },
  {
    id: 'indiamart',
    name: 'IndiaMART',
    logo: '🏭',
    description: 'B2B marketplace for bulk orders and manufacturers',
    categories: ['All Categories', 'Manufacturing', 'Wholesale'],
    avgDelivery: '5-15 days',
    minOrder: 'Varies',
    commission: 'Negotiable',
    rating: 4.5,
    features: ['Bulk Pricing', 'Direct from Manufacturer', 'Custom Orders']
  },
  {
    id: 'tradeindia',
    name: 'TradeIndia',
    logo: '🇮🇳',
    description: 'B2B trade portal connecting buyers and suppliers',
    categories: ['Industrial', 'Consumer Goods', 'Textiles'],
    avgDelivery: '7-14 days',
    minOrder: 'Varies',
    commission: 'Negotiable',
    rating: 4.1,
    features: ['Verified Suppliers', 'Trade Assurance', 'Bulk Deals']
  },
  {
    id: 'shopsy',
    name: 'Shopsy (Flipkart)',
    logo: '🛍️',
    description: 'Flipkart\'s reseller platform with competitive pricing',
    categories: ['Fashion', 'Electronics', 'Home', 'Beauty'],
    avgDelivery: '2-5 days',
    minOrder: 'No minimum',
    commission: '5-15%',
    rating: 4.3,
    features: ['Flipkart Logistics', 'Quality Assurance', 'Easy Onboarding']
  }
]

function ConnectSupplierModal({ supplier, onClose, onConnect }) {
  const [formData, setFormData] = useState({
    apiKey: '',
    apiSecret: '',
    accountId: '',
    autoFulfill: false
  })
  const [connecting, setConnecting] = useState(false)

  const handleConnect = async () => {
    setConnecting(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 1500))
      onConnect({
        supplier_id: supplier.id,
        name: supplier.name,
        ...formData,
        status: 'connected',
        connected_at: new Date().toISOString()
      })
      onClose()
    } catch (err) {
      console.error('Error connecting:', err)
    } finally {
      setConnecting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-rose-100 rounded-xl flex items-center justify-center text-2xl">
              {supplier.logo}
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Connect {supplier.name}</h2>
              <p className="text-sm text-gray-500">{supplier.description}</p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Key / Seller ID
            </label>
            <input
              type="text"
              value={formData.apiKey}
              onChange={(e) => setFormData({ ...formData, apiKey: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="Enter your API key or seller ID"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Secret (if required)
            </label>
            <input
              type="password"
              value={formData.apiSecret}
              onChange={(e) => setFormData({ ...formData, apiSecret: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="Enter your API secret"
            />
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">Features</h4>
            <div className="flex flex-wrap gap-2">
              {supplier.features.map((feature, i) => (
                <span key={i} className="px-2 py-1 bg-white text-gray-600 rounded text-sm border border-gray-200">
                  {feature}
                </span>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:border-rose-300">
            <input
              type="checkbox"
              checked={formData.autoFulfill}
              onChange={(e) => setFormData({ ...formData, autoFulfill: e.target.checked })}
              className="w-4 h-4 text-rose-600 rounded focus:ring-rose-500"
            />
            <div>
              <p className="font-medium text-gray-900">Enable Auto-Fulfillment</p>
              <p className="text-sm text-gray-500">Automatically forward orders to supplier</p>
            </div>
          </label>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleConnect}
            disabled={connecting || !formData.apiKey}
            className="px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50 flex items-center gap-2"
          >
            {connecting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <Link className="w-4 h-4" />
                Connect Supplier
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

function ProductMappingModal({ onClose }) {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      const { data } = await supabase
        .from('products')
        .select('id, name, sku, price, images')
        .eq('is_active', true)
        .limit(20)
      setProducts(data || [])
    } catch (err) {
      console.error('Error loading products:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Map Products to Suppliers</h2>
            <p className="text-sm text-gray-500">Link your products with supplier SKUs for auto-fulfillment</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <RefreshCw className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          ) : (
            <div className="space-y-3">
              {products.map(product => (
                <div key={product.id} className="flex items-center gap-4 p-4 border border-gray-200 rounded-lg">
                  <img
                    src={product.images?.[0] || '/products/placeholder.jpg'}
                    alt={product.name}
                    className="w-16 h-16 object-cover rounded-lg"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{product.name}</p>
                    <p className="text-sm text-gray-500">SKU: {product.sku}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <select className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-rose-500">
                      <option value="">Select Supplier</option>
                      {suppliers.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      placeholder="Supplier SKU"
                      className="w-32 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-rose-500"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            Cancel
          </button>
          <button className="px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700">
            Save Mappings
          </button>
        </div>
      </div>
    </div>
  )
}

export default function Dropshipping() {
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(true)
  const [showConnectModal, setShowConnectModal] = useState(null)
  const [showMappingModal, setShowMappingModal] = useState(false)
  const [activeTab, setActiveTab] = useState('suppliers')
  const [stats, setStats] = useState({
    activeSuppliers: 0,
    productsLinked: 0,
    ordersForwarded: 0,
    totalSavings: 0
  })

  useEffect(() => {
    loadConnections()
  }, [])

  const loadConnections = async () => {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('dropship_suppliers')
        .select('*')
        .eq('is_active', true)
      setConnections(data || [])
      setStats(prev => ({ ...prev, activeSuppliers: data?.length || 0 }))
    } catch (err) {
      console.error('Error loading suppliers:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (connectionData) => {
    try {
      await supabase.from('dropship_suppliers').insert({
        name: connectionData.name,
        api_key: connectionData.apiKey,
        api_secret: connectionData.apiSecret,
        is_active: true,
        settings: { autoFulfill: connectionData.autoFulfill }
      })
      loadConnections()
      alert(`${connectionData.name} connected successfully!`)
    } catch (err) {
      console.error('Error saving connection:', err)
      // Add to local state anyway for demo
      setConnections([...connections, connectionData])
    }
  }

  const handleDisconnect = async (supplierId) => {
    if (!confirm('Are you sure you want to disconnect this supplier?')) return
    try {
      await supabase.from('dropship_suppliers').update({ is_active: false }).eq('id', supplierId)
      loadConnections()
    } catch (err) {
      console.error('Error disconnecting:', err)
    }
  }

  const isConnected = (supplierId) => {
    return connections.some(c => c.supplier_id === supplierId || c.name?.toLowerCase().includes(supplierId))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dropshipping</h1>
          <p className="text-gray-500 mt-1">Connect with Indian suppliers for direct fulfillment</p>
        </div>
        <button
          onClick={() => setShowMappingModal(true)}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
        >
          <Package className="w-4 h-4" />
          Map Products
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Truck className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{connections.length}</p>
              <p className="text-xs text-gray-500">Active Suppliers</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Package className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.productsLinked}</p>
              <p className="text-xs text-gray-500">Products Linked</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <ShoppingBag className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{stats.ordersForwarded}</p>
              <p className="text-xs text-gray-500">Orders Forwarded</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
              <Percent className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{(stats.totalSavings / 1000).toFixed(0)}K</p>
              <p className="text-xs text-gray-500">Total Savings</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-gray-200">
        {['suppliers', 'orders', 'inventory'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors capitalize ${
              activeTab === tab
                ? 'border-rose-500 text-rose-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'suppliers' && (
        <>
          {/* Info Banner */}
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl p-6 text-white">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                <Truck className="w-6 h-6" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg">How Dropshipping Works</h3>
                <p className="text-white/80 text-sm mt-1">
                  Connect with suppliers, map your products to their inventory, and orders will be automatically
                  forwarded for fulfillment. You keep the margin, they handle shipping!
                </p>
                <div className="flex items-center gap-6 mt-4 text-sm">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    No inventory needed
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    Pan-India delivery
                  </div>
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    COD available
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Supplier Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {suppliers.map(supplier => {
              const connected = isConnected(supplier.id)

              return (
                <div
                  key={supplier.id}
                  className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center text-2xl">
                          {supplier.logo}
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">{supplier.name}</h3>
                          <div className="flex items-center gap-1 text-sm text-yellow-600">
                            <Star className="w-4 h-4 fill-current" />
                            {supplier.rating}
                          </div>
                        </div>
                      </div>
                      {connected && (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium flex items-center gap-1">
                          <CheckCircle className="w-3 h-3" />
                          Connected
                        </span>
                      )}
                    </div>

                    <p className="text-sm text-gray-500 mb-4">{supplier.description}</p>

                    <div className="space-y-2 text-sm mb-4">
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Delivery</span>
                        <span className="text-gray-900">{supplier.avgDelivery}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Min Order</span>
                        <span className="text-gray-900">{supplier.minOrder}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500">Commission</span>
                        <span className="text-gray-900">{supplier.commission}</span>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1 mb-4">
                      {supplier.categories.slice(0, 3).map((cat, i) => (
                        <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {cat}
                        </span>
                      ))}
                    </div>

                    {connected ? (
                      <div className="flex items-center gap-2">
                        <button className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">
                          <Settings className="w-4 h-4 inline mr-2" />
                          Settings
                        </button>
                        <button
                          onClick={() => handleDisconnect(supplier.id)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                        >
                          <Unlink className="w-5 h-5" />
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setShowConnectModal(supplier)}
                        className="w-full px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 flex items-center justify-center gap-2"
                      >
                        <Link className="w-4 h-4" />
                        Connect
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {activeTab === 'orders' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
          <Package className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Dropship Orders Yet</h3>
          <p className="text-gray-500 mb-4">Orders will appear here once you connect suppliers and map products</p>
          <button
            onClick={() => setActiveTab('suppliers')}
            className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
          >
            Connect a Supplier
          </button>
        </div>
      )}

      {activeTab === 'inventory' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="p-6 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-900">Synced Inventory</h3>
              <button className="flex items-center gap-2 px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50 rounded-lg">
                <RefreshCw className="w-4 h-4" />
                Sync All
              </button>
            </div>
          </div>
          <div className="p-8 text-center">
            <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Products Mapped</h3>
            <p className="text-gray-500 mb-4">Map your products to supplier SKUs to enable inventory sync</p>
            <button
              onClick={() => setShowMappingModal(true)}
              className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
            >
              Map Products
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      {showConnectModal && (
        <ConnectSupplierModal
          supplier={showConnectModal}
          onClose={() => setShowConnectModal(null)}
          onConnect={handleConnect}
        />
      )}

      {showMappingModal && (
        <ProductMappingModal onClose={() => setShowMappingModal(false)} />
      )}
    </div>
  )
}
