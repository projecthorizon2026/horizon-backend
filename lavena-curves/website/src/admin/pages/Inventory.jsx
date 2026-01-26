import { useState, useEffect } from 'react'
import {
  Search,
  Download,
  AlertTriangle,
  Package,
  RefreshCw,
  Plus,
  Minus,
  History,
  X,
  Filter,
  ArrowUp,
  ArrowDown,
  Edit2,
  Boxes,
  TrendingDown,
  TrendingUp,
  BarChart3
} from 'lucide-react'
import { db, supabase } from '../lib/supabase'

function StockAdjustmentModal({ product, onClose, onUpdate }) {
  const [quantity, setQuantity] = useState('')
  const [type, setType] = useState('add')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  if (!product) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!quantity || parseInt(quantity) === 0) return

    setSaving(true)
    try {
      const change = type === 'add' ? parseInt(quantity) : -parseInt(quantity)
      await db.updateStock(product.id, change, 'adjustment', notes)
      onUpdate()
      onClose()
    } catch (err) {
      console.error('Error adjusting stock:', err)
      alert('Failed to adjust stock')
    } finally {
      setSaving(false)
    }
  }

  const newQuantity = type === 'add'
    ? product.stock_quantity + parseInt(quantity || 0)
    : product.stock_quantity - parseInt(quantity || 0)

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Adjust Stock</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Product Info */}
          <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-xl">
            <div className="w-16 h-16 bg-gray-200 rounded-lg overflow-hidden">
              {product.images?.[0] ? (
                <img src={product.images[0]} alt={product.name} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Package className="w-6 h-6 text-gray-400" />
                </div>
              )}
            </div>
            <div>
              <p className="font-medium text-gray-900">{product.name}</p>
              <p className="text-sm text-gray-500">SKU: {product.sku}</p>
              <p className="text-sm">
                Current Stock: <span className={`font-bold ${product.stock_quantity < product.low_stock_threshold ? 'text-red-600' : 'text-green-600'}`}>
                  {product.stock_quantity}
                </span>
              </p>
            </div>
          </div>

          {/* Adjustment Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Adjustment Type</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setType('add')}
                className={`p-3 rounded-xl border-2 flex items-center justify-center gap-2 transition-colors ${
                  type === 'add'
                    ? 'border-green-500 bg-green-50 text-green-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Plus className="w-5 h-5" />
                Add Stock
              </button>
              <button
                type="button"
                onClick={() => setType('remove')}
                className={`p-3 rounded-xl border-2 flex items-center justify-center gap-2 transition-colors ${
                  type === 'remove'
                    ? 'border-red-500 bg-red-50 text-red-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <Minus className="w-5 h-5" />
                Remove Stock
              </button>
            </div>
          </div>

          {/* Quantity */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Quantity</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              min="1"
              placeholder="Enter quantity"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-rose-500"
              required
            />
          </div>

          {/* New Stock Preview */}
          {quantity && (
            <div className={`p-3 rounded-xl ${type === 'add' ? 'bg-green-50' : 'bg-red-50'}`}>
              <div className="flex items-center justify-between text-sm">
                <span className={type === 'add' ? 'text-green-600' : 'text-red-600'}>New Stock Level:</span>
                <span className="font-bold text-gray-900">{Math.max(0, newQuantity)} units</span>
              </div>
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Notes (Optional)</label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Reason for adjustment..."
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-rose-500"
            />
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
              disabled={saving || !quantity}
              className={`px-6 py-2 text-white rounded-lg disabled:opacity-50 ${
                type === 'add' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
              }`}
            >
              {saving ? 'Saving...' : type === 'add' ? 'Add Stock' : 'Remove Stock'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function InventoryHistoryModal({ productId, productName, onClose }) {
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadTransactions()
  }, [productId])

  const loadTransactions = async () => {
    setLoading(true)
    try {
      const { data, error } = await supabase
        .from('inventory_transactions')
        .select('*')
        .eq('product_id', productId)
        .order('created_at', { ascending: false })
        .limit(50)
      if (error) throw error
      setTransactions(data || [])
    } catch (err) {
      console.error('Error loading transactions:', err)
    } finally {
      setLoading(false)
    }
  }

  const typeColors = {
    adjustment: 'bg-blue-100 text-blue-700',
    sale: 'bg-red-100 text-red-700',
    return: 'bg-green-100 text-green-700',
    purchase: 'bg-purple-100 text-purple-700',
    dropship_sync: 'bg-orange-100 text-orange-700'
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Inventory History</h2>
            <p className="text-sm text-gray-500">{productName}</p>
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
          ) : transactions.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">No inventory history</p>
            </div>
          ) : (
            <div className="space-y-3">
              {transactions.map(tx => (
                <div key={tx.id} className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    tx.quantity_change > 0 ? 'bg-green-100' : 'bg-red-100'
                  }`}>
                    {tx.quantity_change > 0 ? (
                      <ArrowUp className="w-5 h-5 text-green-600" />
                    ) : (
                      <ArrowDown className="w-5 h-5 text-red-600" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full capitalize ${typeColors[tx.type] || 'bg-gray-100 text-gray-700'}`}>
                        {tx.type}
                      </span>
                      <span className={`text-sm font-bold ${tx.quantity_change > 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {tx.quantity_change > 0 ? '+' : ''}{tx.quantity_change}
                      </span>
                    </div>
                    {tx.notes && <p className="text-sm text-gray-600 mt-1">{tx.notes}</p>}
                    <p className="text-xs text-gray-400 mt-1">
                      {tx.quantity_before} → {tx.quantity_after} units
                    </p>
                  </div>
                  <div className="text-right text-sm text-gray-500">
                    {new Date(tx.created_at).toLocaleDateString('en-IN', {
                      day: 'numeric',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Inventory() {
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState('all') // all, low, out
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [showHistory, setShowHistory] = useState(null)

  useEffect(() => {
    loadProducts()
  }, [])

  const loadProducts = async () => {
    setLoading(true)
    try {
      const { data, error } = await db.getProducts({ isActive: true, orderBy: 'stock_quantity', ascending: true })
      if (error) throw error
      setProducts(data || [])
    } catch (err) {
      console.error('Error loading products:', err)
    } finally {
      setLoading(false)
    }
  }

  const filteredProducts = products.filter(product => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      if (!product.name?.toLowerCase().includes(query) && !product.sku?.toLowerCase().includes(query)) {
        return false
      }
    }
    // Stock filter
    if (filter === 'low') {
      return product.stock_quantity > 0 && product.stock_quantity <= (product.low_stock_threshold || 5)
    }
    if (filter === 'out') {
      return product.stock_quantity === 0
    }
    return true
  })

  // Calculate stats
  const totalProducts = products.length
  const totalStock = products.reduce((sum, p) => sum + (p.stock_quantity || 0), 0)
  const lowStockCount = products.filter(p => p.stock_quantity > 0 && p.stock_quantity <= (p.low_stock_threshold || 5)).length
  const outOfStockCount = products.filter(p => p.stock_quantity === 0).length
  const stockValue = products.reduce((sum, p) => sum + ((p.stock_quantity || 0) * (parseFloat(p.cost_price) || parseFloat(p.price) * 0.6)), 0)

  const exportInventory = () => {
    const csv = [
      ['SKU', 'Product Name', 'Category', 'Stock Quantity', 'Low Stock Threshold', 'Price', 'Status'].join(','),
      ...filteredProducts.map(p => [
        p.sku,
        `"${p.name}"`,
        p.category,
        p.stock_quantity || 0,
        p.low_stock_threshold || 5,
        p.price,
        p.stock_quantity === 0 ? 'Out of Stock' : p.stock_quantity <= (p.low_stock_threshold || 5) ? 'Low Stock' : 'In Stock'
      ].join(','))
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `inventory-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
          <p className="text-gray-500 mt-1">Manage stock levels and track inventory</p>
        </div>
        <button
          onClick={exportInventory}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <Download className="w-4 h-4" />
          Export
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Boxes className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalProducts}</p>
              <p className="text-xs text-gray-500">Products</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Package className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{totalStock.toLocaleString()}</p>
              <p className="text-xs text-gray-500">Total Units</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              <TrendingDown className="w-5 h-5 text-yellow-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-yellow-600">{lowStockCount}</p>
              <p className="text-xs text-gray-500">Low Stock</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{outOfStockCount}</p>
              <p className="text-xs text-gray-500">Out of Stock</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">₹{stockValue.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
              <p className="text-xs text-gray-500">Stock Value</p>
            </div>
          </div>
        </div>
      </div>

      {/* Low Stock Alert */}
      {lowStockCount > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <div>
              <p className="font-medium text-yellow-800">{lowStockCount} products running low on stock</p>
              <p className="text-sm text-yellow-600">Consider restocking soon to avoid stockouts</p>
            </div>
            <button
              onClick={() => setFilter('low')}
              className="ml-auto px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 text-sm"
            >
              View Low Stock
            </button>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[200px] max-w-md relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name or SKU..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
          />
        </div>
        <div className="flex items-center gap-2">
          {['all', 'low', 'out'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === f
                  ? f === 'out' ? 'bg-red-100 text-red-700' :
                    f === 'low' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-rose-100 text-rose-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f === 'all' ? 'All Products' : f === 'low' ? 'Low Stock' : 'Out of Stock'}
            </button>
          ))}
        </div>
        <button
          onClick={loadProducts}
          className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <RefreshCw className="w-5 h-5 text-gray-600" />
        </button>
      </div>

      {/* Inventory Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="text-center py-12">
            <Package className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500">No products found</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">SKU</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stock</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map(product => {
                  const isLow = product.stock_quantity > 0 && product.stock_quantity <= (product.low_stock_threshold || 5)
                  const isOut = product.stock_quantity === 0

                  return (
                    <tr key={product.id} className={`border-b border-gray-100 hover:bg-gray-50 ${isOut ? 'bg-red-50' : isLow ? 'bg-yellow-50' : ''}`}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 bg-gray-200 rounded-lg overflow-hidden flex-shrink-0">
                            {product.images?.[0] ? (
                              <img src={product.images[0]} alt={product.name} className="w-full h-full object-cover" />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center">
                                <Package className="w-5 h-5 text-gray-400" />
                              </div>
                            )}
                          </div>
                          <p className="font-medium text-gray-900 line-clamp-1">{product.name}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 font-mono">{product.sku}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 capitalize">{product.category}</td>
                      <td className="px-4 py-3">
                        <span className={`text-lg font-bold ${isOut ? 'text-red-600' : isLow ? 'text-yellow-600' : 'text-gray-900'}`}>
                          {product.stock_quantity || 0}
                        </span>
                        <span className="text-xs text-gray-500 ml-1">/ min {product.low_stock_threshold || 5}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          isOut ? 'bg-red-100 text-red-700' :
                          isLow ? 'bg-yellow-100 text-yellow-700' :
                          'bg-green-100 text-green-700'
                        }`}>
                          {isOut ? 'Out of Stock' : isLow ? 'Low Stock' : 'In Stock'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-medium text-gray-900">
                        ₹{parseFloat(product.price).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setSelectedProduct(product)}
                            className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg"
                            title="Adjust Stock"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => setShowHistory(product)}
                            className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="View History"
                          >
                            <History className="w-4 h-4" />
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

      {/* Stock Adjustment Modal */}
      {selectedProduct && (
        <StockAdjustmentModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
          onUpdate={loadProducts}
        />
      )}

      {/* History Modal */}
      {showHistory && (
        <InventoryHistoryModal
          productId={showHistory.id}
          productName={showHistory.name}
          onClose={() => setShowHistory(null)}
        />
      )}
    </div>
  )
}
