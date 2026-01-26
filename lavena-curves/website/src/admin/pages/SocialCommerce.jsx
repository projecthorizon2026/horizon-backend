import { useState, useEffect } from 'react'
import {
  Instagram,
  Facebook,
  MessageCircle,
  ShoppingBag,
  Plus,
  Link,
  CheckCircle,
  XCircle,
  ExternalLink,
  RefreshCw,
  Image,
  Eye,
  Heart,
  Share2,
  TrendingUp,
  Users,
  DollarSign,
  Settings,
  Unlink,
  AlertTriangle,
  Camera,
  Send,
  Clock
} from 'lucide-react'
import { supabase } from '../lib/supabase'

const platforms = [
  {
    id: 'instagram',
    name: 'Instagram Shopping',
    icon: Instagram,
    color: 'bg-gradient-to-br from-purple-600 via-pink-600 to-orange-500',
    description: 'Tag products in posts and stories, enable checkout',
    features: ['Product Tagging', 'Shop Tab', 'Checkout', 'Stories Shopping'],
    requirements: ['Business Account', 'Facebook Page', 'Product Catalog']
  },
  {
    id: 'facebook',
    name: 'Facebook Shops',
    icon: Facebook,
    color: 'bg-blue-600',
    description: 'Create a storefront on Facebook with product collections',
    features: ['Shop Tab', 'Messenger Sales', 'Live Shopping', 'Ads Integration'],
    requirements: ['Business Page', 'Commerce Manager', 'Payment Setup']
  },
  {
    id: 'whatsapp',
    name: 'WhatsApp Business',
    icon: MessageCircle,
    color: 'bg-green-500',
    description: 'Product catalog and quick order via WhatsApp',
    features: ['Product Catalog', 'Quick Replies', 'Order Messages', 'Payment Links'],
    requirements: ['Business Account', 'Phone Number', 'WhatsApp Business App']
  },
  {
    id: 'pinterest',
    name: 'Pinterest',
    icon: Image,
    color: 'bg-red-600',
    description: 'Buyable pins and visual product discovery',
    features: ['Rich Pins', 'Shop the Look', 'Catalogs', 'Ads'],
    requirements: ['Business Account', 'Verified Website', 'Product Feed']
  }
]

function ConnectPlatformModal({ platform, onClose, onConnect }) {
  const [step, setStep] = useState(1)
  const [connecting, setConnecting] = useState(false)
  const [formData, setFormData] = useState({
    accountId: '',
    accessToken: '',
    pageId: '',
    catalogId: ''
  })

  const handleConnect = async () => {
    setConnecting(true)
    try {
      // In real implementation, this would use OAuth
      await new Promise(resolve => setTimeout(resolve, 1500))
      onConnect({
        platform: platform.id,
        ...formData,
        connected_at: new Date().toISOString()
      })
      onClose()
    } catch (err) {
      console.error('Error connecting:', err)
    } finally {
      setConnecting(false)
    }
  }

  const PlatformIcon = platform.icon

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 ${platform.color} rounded-xl flex items-center justify-center`}>
              <PlatformIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Connect {platform.name}</h2>
              <p className="text-sm text-gray-500">{platform.description}</p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {step === 1 && (
            <>
              <div>
                <h3 className="font-medium text-gray-900 mb-3">Requirements</h3>
                <ul className="space-y-2">
                  {platform.requirements.map((req, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-gray-600">
                      <CheckCircle className="w-4 h-4 text-green-500" />
                      {req}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="font-medium text-gray-900 mb-3">Features You'll Get</h3>
                <div className="flex flex-wrap gap-2">
                  {platform.features.map((feature, i) => (
                    <span key={i} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm">
                      {feature}
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setStep(2)}
                className="w-full py-3 bg-rose-600 text-white rounded-lg font-medium hover:bg-rose-700"
              >
                Continue Setup
              </button>
            </>
          )}

          {step === 2 && (
            <>
              {platform.id === 'instagram' || platform.id === 'facebook' ? (
                <div className="space-y-4">
                  <p className="text-sm text-gray-600">
                    You'll be redirected to {platform.name} to authorize the connection.
                  </p>
                  <button
                    onClick={handleConnect}
                    disabled={connecting}
                    className={`w-full py-3 ${platform.color} text-white rounded-lg font-medium flex items-center justify-center gap-2`}
                  >
                    {connecting ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin" />
                        Connecting...
                      </>
                    ) : (
                      <>
                        <PlatformIcon className="w-5 h-5" />
                        Connect with {platform.name.split(' ')[0]}
                      </>
                    )}
                  </button>
                </div>
              ) : platform.id === 'whatsapp' ? (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      WhatsApp Business Phone
                    </label>
                    <input
                      type="tel"
                      value={formData.accountId}
                      onChange={(e) => setFormData({ ...formData, accountId: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                      placeholder="+91 9876543210"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Business API Token
                    </label>
                    <input
                      type="password"
                      value={formData.accessToken}
                      onChange={(e) => setFormData({ ...formData, accessToken: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                      placeholder="Your API token"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Get this from WhatsApp Business API dashboard
                    </p>
                  </div>
                  <button
                    onClick={handleConnect}
                    disabled={connecting || !formData.accountId}
                    className="w-full py-3 bg-green-500 text-white rounded-lg font-medium hover:bg-green-600 disabled:opacity-50"
                  >
                    {connecting ? 'Connecting...' : 'Connect WhatsApp'}
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Pinterest Business Account ID
                    </label>
                    <input
                      type="text"
                      value={formData.accountId}
                      onChange={(e) => setFormData({ ...formData, accountId: e.target.value })}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
                      placeholder="Your account ID"
                    />
                  </div>
                  <button
                    onClick={handleConnect}
                    disabled={connecting}
                    className="w-full py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50"
                  >
                    {connecting ? 'Connecting...' : 'Connect Pinterest'}
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
          {step > 1 && (
            <button
              onClick={() => setStep(step - 1)}
              className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
            >
              Back
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg ml-auto"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

function CatalogSyncModal({ connection, onClose, onSync }) {
  const [syncing, setSyncing] = useState(false)
  const [products, setProducts] = useState([])
  const [selectedProducts, setSelectedProducts] = useState([])

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    try {
      const { data } = await supabase
        .from('products')
        .select('id, name, price, images, sku')
        .eq('is_active', true)
        .limit(50)
      setProducts(data || [])
      setSelectedProducts(data?.map(p => p.id) || [])
    } catch (err) {
      console.error('Error loading products:', err)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 2000))
      onSync(selectedProducts.length)
      onClose()
    } catch (err) {
      console.error('Error syncing:', err)
    } finally {
      setSyncing(false)
    }
  }

  const toggleProduct = (id) => {
    setSelectedProducts(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Sync Product Catalog</h2>
          <p className="text-sm text-gray-500">Select products to sync with {connection?.platform}</p>
        </div>

        <div className="p-6 overflow-y-auto max-h-[50vh]">
          <div className="flex items-center justify-between mb-4">
            <span className="text-sm text-gray-600">
              {selectedProducts.length} of {products.length} products selected
            </span>
            <button
              onClick={() => setSelectedProducts(
                selectedProducts.length === products.length ? [] : products.map(p => p.id)
              )}
              className="text-sm text-rose-600 hover:text-rose-700"
            >
              {selectedProducts.length === products.length ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          <div className="space-y-2">
            {products.map(product => (
              <label
                key={product.id}
                className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedProducts.includes(product.id)
                    ? 'border-rose-300 bg-rose-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedProducts.includes(product.id)}
                  onChange={() => toggleProduct(product.id)}
                  className="w-4 h-4 text-rose-600 rounded focus:ring-rose-500"
                />
                <img
                  src={product.images?.[0] || '/products/placeholder.jpg'}
                  alt={product.name}
                  className="w-12 h-12 object-cover rounded-lg"
                />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">{product.name}</p>
                  <p className="text-sm text-gray-500">SKU: {product.sku}</p>
                </div>
                <span className="font-medium text-gray-900">
                  ₹{product.price?.toLocaleString('en-IN')}
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleSync}
            disabled={syncing || selectedProducts.length === 0}
            className="px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50 flex items-center gap-2"
          >
            {syncing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Syncing...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                Sync {selectedProducts.length} Products
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function SocialCommerce() {
  const [connections, setConnections] = useState([])
  const [loading, setLoading] = useState(true)
  const [showConnectModal, setShowConnectModal] = useState(null)
  const [showSyncModal, setShowSyncModal] = useState(null)
  const [socialStats, setSocialStats] = useState({
    totalFollowers: 12500,
    totalEngagements: 3420,
    socialRevenue: 145000,
    conversionRate: 3.2
  })

  useEffect(() => {
    loadConnections()
  }, [])

  const loadConnections = async () => {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('social_catalog')
        .select('*')

      // Group by platform
      const platformConnections = {}
      data?.forEach(item => {
        if (!platformConnections[item.platform]) {
          platformConnections[item.platform] = {
            platform: item.platform,
            status: item.status,
            products_synced: 0,
            last_sync_at: item.last_sync_at
          }
        }
        platformConnections[item.platform].products_synced++
      })

      setConnections(Object.values(platformConnections))
    } catch (err) {
      console.error('Error loading connections:', err)
      // Use mock data
      setConnections([
        {
          platform: 'instagram',
          status: 'connected',
          products_synced: 24,
          last_sync_at: new Date(Date.now() - 3600000).toISOString()
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (connectionData) => {
    try {
      // Save connection (in real app, this would be more sophisticated)
      setConnections([...connections, {
        ...connectionData,
        status: 'connected',
        products_synced: 0
      }])
      alert(`${connectionData.platform} connected successfully!`)
    } catch (err) {
      console.error('Error saving connection:', err)
    }
  }

  const handleDisconnect = async (platformId) => {
    if (!confirm('Are you sure you want to disconnect this platform?')) return
    setConnections(connections.filter(c => c.platform !== platformId))
  }

  const handleSync = (count) => {
    alert(`${count} products synced successfully!`)
    loadConnections()
  }

  const isConnected = (platformId) => {
    return connections.some(c => c.platform === platformId && c.status === 'connected')
  }

  const getConnection = (platformId) => {
    return connections.find(c => c.platform === platformId)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Social Commerce</h1>
          <p className="text-gray-500 mt-1">Sell directly on Instagram, Facebook, WhatsApp & Pinterest</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Users className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{socialStats.totalFollowers.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Total Followers</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-pink-100 rounded-lg flex items-center justify-center">
              <Heart className="w-5 h-5 text-pink-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{socialStats.totalEngagements.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Engagements (30d)</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{(socialStats.socialRevenue / 1000).toFixed(0)}K</p>
              <p className="text-xs text-gray-500">Social Revenue</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{socialStats.conversionRate}%</p>
              <p className="text-xs text-gray-500">Conversion Rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Platform Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {platforms.map(platform => {
          const connected = isConnected(platform.id)
          const connection = getConnection(platform.id)
          const PlatformIcon = platform.icon

          return (
            <div
              key={platform.id}
              className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden"
            >
              <div className={`${platform.color} px-6 py-4`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <PlatformIcon className="w-8 h-8 text-white" />
                    <div>
                      <h3 className="font-semibold text-white text-lg">{platform.name}</h3>
                      <p className="text-white/80 text-sm">{platform.description}</p>
                    </div>
                  </div>
                  {connected && (
                    <span className="px-3 py-1 bg-white/20 text-white rounded-full text-sm flex items-center gap-1">
                      <CheckCircle className="w-4 h-4" />
                      Connected
                    </span>
                  )}
                </div>
              </div>

              <div className="p-6">
                {connected ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Products Synced</span>
                      <span className="font-medium text-gray-900">{connection.products_synced}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-500">Last Sync</span>
                      <span className="font-medium text-gray-900">
                        {connection.last_sync_at
                          ? new Date(connection.last_sync_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })
                          : 'Never'
                        }
                      </span>
                    </div>

                    <div className="flex items-center gap-2 pt-2">
                      <button
                        onClick={() => setShowSyncModal(connection)}
                        className="flex-1 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 flex items-center justify-center gap-2"
                      >
                        <RefreshCw className="w-4 h-4" />
                        Sync Catalog
                      </button>
                      <button
                        onClick={() => handleDisconnect(platform.id)}
                        className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg"
                        title="Disconnect"
                      >
                        <Unlink className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-600 mb-2">Features:</p>
                      <div className="flex flex-wrap gap-2">
                        {platform.features.map((feature, i) => (
                          <span
                            key={i}
                            className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs"
                          >
                            {feature}
                          </span>
                        ))}
                      </div>
                    </div>

                    <button
                      onClick={() => setShowConnectModal(platform)}
                      className={`w-full py-2 ${platform.color} text-white rounded-lg font-medium flex items-center justify-center gap-2 hover:opacity-90`}
                    >
                      <Link className="w-4 h-4" />
                      Connect {platform.name.split(' ')[0]}
                    </button>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Content Ideas */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Content Ideas for Social Selling</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="w-10 h-10 bg-pink-100 rounded-lg flex items-center justify-center mb-3">
              <Camera className="w-5 h-5 text-pink-600" />
            </div>
            <h4 className="font-medium text-gray-900">Product Showcases</h4>
            <p className="text-sm text-gray-500 mt-1">
              Feature your bestsellers with lifestyle photos and styling tips
            </p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-3">
              <Users className="w-5 h-5 text-purple-600" />
            </div>
            <h4 className="font-medium text-gray-900">Customer Stories</h4>
            <p className="text-sm text-gray-500 mt-1">
              Share UGC and testimonials from happy customers
            </p>
          </div>
          <div className="border border-gray-200 rounded-lg p-4">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-3">
              <Send className="w-5 h-5 text-blue-600" />
            </div>
            <h4 className="font-medium text-gray-900">Behind the Scenes</h4>
            <p className="text-sm text-gray-500 mt-1">
              Show your brand story, production process, and team
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-pink-500 to-purple-600 rounded-xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
              <Instagram className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Schedule Social Posts</h3>
              <p className="text-white/80 text-sm">Plan and schedule your product posts across all platforms</p>
            </div>
          </div>
          <button className="px-4 py-2 bg-white text-purple-600 rounded-lg font-medium hover:bg-white/90 flex items-center gap-2">
            <Clock className="w-4 h-4" />
            Create Post
          </button>
        </div>
      </div>

      {/* Modals */}
      {showConnectModal && (
        <ConnectPlatformModal
          platform={showConnectModal}
          onClose={() => setShowConnectModal(null)}
          onConnect={handleConnect}
        />
      )}

      {showSyncModal && (
        <CatalogSyncModal
          connection={showSyncModal}
          onClose={() => setShowSyncModal(null)}
          onSync={handleSync}
        />
      )}
    </div>
  )
}
