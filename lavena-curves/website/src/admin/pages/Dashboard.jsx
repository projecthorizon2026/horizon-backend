import { useState, useEffect } from 'react'
import {
  ShoppingCart,
  IndianRupee,
  Users,
  TrendingUp,
  Package,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  CheckCircle2,
  Truck,
  Eye
} from 'lucide-react'
import { db } from '../lib/supabase'

function StatCard({ title, value, change, changeType, icon: Icon, color, onClick }) {
  const colors = {
    rose: 'from-rose-500 to-pink-600',
    blue: 'from-blue-500 to-indigo-600',
    green: 'from-green-500 to-emerald-600',
    purple: 'from-purple-500 to-violet-600',
    orange: 'from-orange-500 to-amber-600'
  }

  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
          {change !== undefined && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${changeType === 'up' ? 'text-green-600' : 'text-red-600'}`}>
              {changeType === 'up' ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
              <span>{change}% vs last month</span>
            </div>
          )}
        </div>
        <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colors[color]} flex items-center justify-center`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
      </div>
    </div>
  )
}

function RecentOrderRow({ order, onView }) {
  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-700',
    confirmed: 'bg-blue-100 text-blue-700',
    processing: 'bg-purple-100 text-purple-700',
    shipped: 'bg-indigo-100 text-indigo-700',
    delivered: 'bg-green-100 text-green-700',
    cancelled: 'bg-red-100 text-red-700'
  }

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm font-medium text-gray-900">{order.order_number}</td>
      <td className="px-4 py-3 text-sm text-gray-600">{order.customer_name || order.customer_email}</td>
      <td className="px-4 py-3">
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[order.status] || 'bg-gray-100 text-gray-700'}`}>
          {order.status}
        </span>
      </td>
      <td className="px-4 py-3 text-sm font-medium text-gray-900">₹{parseFloat(order.total).toLocaleString()}</td>
      <td className="px-4 py-3 text-sm text-gray-500">
        {new Date(order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
      </td>
      <td className="px-4 py-3">
        <button onClick={() => onView(order)} className="text-rose-600 hover:text-rose-700">
          <Eye className="w-4 h-4" />
        </button>
      </td>
    </tr>
  )
}

function LowStockItem({ product }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
          <Package className="w-5 h-5 text-gray-400" />
        </div>
        <div>
          <p className="text-sm font-medium text-gray-900">{product.name}</p>
          <p className="text-xs text-gray-500">{product.sku}</p>
        </div>
      </div>
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${product.stock_quantity <= 0 ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>
        {product.stock_quantity} left
      </span>
    </div>
  )
}

export default function Dashboard({ onNavigate }) {
  const [stats, setStats] = useState(null)
  const [recentOrders, setRecentOrders] = useState([])
  const [lowStockProducts, setLowStockProducts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      const [statsData, ordersResult] = await Promise.all([
        db.getStats(),
        db.getOrders({ limit: 10 })
      ])

      setStats(statsData)
      setRecentOrders(ordersResult.data || [])
      setLowStockProducts(statsData.lowStockProducts || [])
    } catch (err) {
      console.error('Error loading dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  const pendingOrders = recentOrders.filter(o => o.status === 'pending').length
  const shippedToday = recentOrders.filter(o => o.status === 'shipped' && new Date(o.updated_at).toDateString() === new Date().toDateString()).length

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Welcome back! Here's what's happening with your store.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Today's Orders"
          value={stats?.todayOrders || 0}
          icon={ShoppingCart}
          color="rose"
          onClick={() => onNavigate('orders')}
        />
        <StatCard
          title="Monthly Revenue"
          value={`₹${(stats?.monthlyRevenue || 0).toLocaleString()}`}
          change={12}
          changeType="up"
          icon={IndianRupee}
          color="green"
        />
        <StatCard
          title="Total Customers"
          value={stats?.totalCustomers || 0}
          change={8}
          changeType="up"
          icon={Users}
          color="blue"
          onClick={() => onNavigate('customers')}
        />
        <StatCard
          title="Conversion Rate"
          value="3.2%"
          change={0.5}
          changeType="up"
          icon={TrendingUp}
          color="purple"
          onClick={() => onNavigate('analytics')}
        />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-center gap-4">
          <div className="w-12 h-12 bg-yellow-100 rounded-full flex items-center justify-center">
            <Clock className="w-6 h-6 text-yellow-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-yellow-700">{pendingOrders}</p>
            <p className="text-sm text-yellow-600">Orders Pending</p>
          </div>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center gap-4">
          <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
            <Truck className="w-6 h-6 text-green-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-green-700">{shippedToday}</p>
            <p className="text-sm text-green-600">Shipped Today</p>
          </div>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-4">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-red-700">{lowStockProducts.length}</p>
            <p className="text-sm text-red-600">Low Stock Items</p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Orders */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Recent Orders</h2>
            <button
              onClick={() => onNavigate('orders')}
              className="text-sm text-rose-600 hover:text-rose-700 font-medium"
            >
              View All
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Order</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-4 py-8 text-center text-gray-500">
                      No orders yet. Orders will appear here once customers start purchasing.
                    </td>
                  </tr>
                ) : (
                  recentOrders.slice(0, 5).map(order => (
                    <RecentOrderRow key={order.id} order={order} onView={() => onNavigate('orders', order.id)} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Low Stock Alert */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">Low Stock Alert</h2>
            <button
              onClick={() => onNavigate('inventory')}
              className="text-sm text-rose-600 hover:text-rose-700 font-medium"
            >
              Manage
            </button>
          </div>
          <div className="p-4">
            {lowStockProducts.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <p className="text-gray-500">All products are well stocked!</p>
              </div>
            ) : (
              <div className="space-y-1">
                {lowStockProducts.slice(0, 5).map(product => (
                  <LowStockItem key={product.id} product={product} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-rose-500 to-pink-600 rounded-xl p-6 text-white">
        <h3 className="text-lg font-semibold mb-2">Quick Actions</h3>
        <p className="text-rose-100 text-sm mb-4">Common tasks to manage your store</p>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => onNavigate('products', 'new')}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
          >
            + Add Product
          </button>
          <button
            onClick={() => onNavigate('discounts')}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
          >
            Create Discount
          </button>
          <button
            onClick={() => onNavigate('email-campaigns')}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
          >
            Send Campaign
          </button>
          <button
            onClick={() => onNavigate('analytics')}
            className="px-4 py-2 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition-colors"
          >
            View Reports
          </button>
        </div>
      </div>
    </div>
  )
}
