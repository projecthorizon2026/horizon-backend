import { useState, useEffect } from 'react'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  ShoppingCart,
  Users,
  Package,
  Calendar,
  Eye,
  MousePointer,
  Target,
  IndianRupee,
  ArrowRight,
  RefreshCw,
  Download,
  BarChart3,
  PieChart,
  Activity
} from 'lucide-react'
import { db, supabase } from '../lib/supabase'

// Simple bar chart component
function SimpleBarChart({ data, maxValue, label }) {
  return (
    <div className="space-y-2">
      {data.map((item, index) => (
        <div key={index} className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-16 text-right">{item.label}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
            <div
              className="bg-gradient-to-r from-rose-500 to-rose-600 h-full rounded-full flex items-center justify-end px-2"
              style={{ width: `${(item.value / maxValue) * 100}%` }}
            >
              <span className="text-xs text-white font-medium">{item.display || item.value}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// Mini sparkline chart
function Sparkline({ data, color = 'rose' }) {
  if (!data || data.length === 0) return null

  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1
  const height = 40
  const width = 120
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return `${x},${y}`
  }).join(' ')

  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline
        fill="none"
        stroke={color === 'rose' ? '#f43f5e' : color === 'green' ? '#22c55e' : '#3b82f6'}
        strokeWidth="2"
        points={points}
      />
    </svg>
  )
}

// Conversion funnel component
function ConversionFunnel({ data }) {
  return (
    <div className="space-y-3">
      {data.map((step, index) => (
        <div key={index} className="relative">
          <div
            className="bg-gradient-to-r from-rose-500 to-rose-400 text-white px-4 py-3 rounded-lg"
            style={{
              width: `${step.percentage}%`,
              minWidth: '120px'
            }}
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">{step.label}</span>
              <span className="text-sm opacity-90">{step.count.toLocaleString()}</span>
            </div>
          </div>
          {index < data.length - 1 && (
            <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-full px-2">
              <span className="text-xs text-gray-500">
                {((data[index + 1].count / step.count) * 100).toFixed(1)}% →
              </span>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default function Analytics() {
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState('30d')
  const [stats, setStats] = useState({
    totalRevenue: 0,
    totalOrders: 0,
    totalCustomers: 0,
    averageOrderValue: 0,
    revenueGrowth: 0,
    ordersGrowth: 0,
    customersGrowth: 0
  })
  const [dailyRevenue, setDailyRevenue] = useState([])
  const [topProducts, setTopProducts] = useState([])
  const [recentOrders, setRecentOrders] = useState([])
  const [categoryBreakdown, setCategoryBreakdown] = useState([])
  const [customerSegments, setCustomerSegments] = useState([])

  useEffect(() => {
    loadAnalytics()
  }, [dateRange])

  const getDays = () => {
    switch (dateRange) {
      case '7d': return 7
      case '30d': return 30
      case '90d': return 90
      case '365d': return 365
      default: return 30
    }
  }

  const loadAnalytics = async () => {
    setLoading(true)
    try {
      const days = getDays()
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - days)

      const prevStartDate = new Date(startDate)
      prevStartDate.setDate(prevStartDate.getDate() - days)

      // Get current period orders
      const { data: currentOrders } = await supabase
        .from('orders')
        .select('*, order_items(*, products(name, category))')
        .eq('payment_status', 'paid')
        .gte('created_at', startDate.toISOString())
        .order('created_at', { ascending: true })

      // Get previous period orders for comparison
      const { data: prevOrders } = await supabase
        .from('orders')
        .select('total')
        .eq('payment_status', 'paid')
        .gte('created_at', prevStartDate.toISOString())
        .lt('created_at', startDate.toISOString())

      // Get customers
      const { data: currentCustomers } = await supabase
        .from('customers')
        .select('id, total_spent, total_orders, created_at')
        .gte('created_at', startDate.toISOString())

      const { data: prevCustomers } = await supabase
        .from('customers')
        .select('id')
        .gte('created_at', prevStartDate.toISOString())
        .lt('created_at', startDate.toISOString())

      // Calculate stats
      const totalRevenue = currentOrders?.reduce((sum, o) => sum + parseFloat(o.total), 0) || 0
      const prevRevenue = prevOrders?.reduce((sum, o) => sum + parseFloat(o.total), 0) || 0
      const totalOrders = currentOrders?.length || 0
      const prevOrdersCount = prevOrders?.length || 0
      const totalCustomers = currentCustomers?.length || 0
      const prevCustomersCount = prevCustomers?.length || 0
      const avgOrderValue = totalOrders > 0 ? totalRevenue / totalOrders : 0

      // Calculate growth percentages
      const revenueGrowth = prevRevenue > 0 ? ((totalRevenue - prevRevenue) / prevRevenue) * 100 : 0
      const ordersGrowth = prevOrdersCount > 0 ? ((totalOrders - prevOrdersCount) / prevOrdersCount) * 100 : 0
      const customersGrowth = prevCustomersCount > 0 ? ((totalCustomers - prevCustomersCount) / prevCustomersCount) * 100 : 0

      setStats({
        totalRevenue,
        totalOrders,
        totalCustomers,
        averageOrderValue: avgOrderValue,
        revenueGrowth,
        ordersGrowth,
        customersGrowth
      })

      // Calculate daily revenue
      const dailyData = {}
      currentOrders?.forEach(order => {
        const date = new Date(order.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
        if (!dailyData[date]) {
          dailyData[date] = { revenue: 0, orders: 0 }
        }
        dailyData[date].revenue += parseFloat(order.total)
        dailyData[date].orders += 1
      })
      setDailyRevenue(Object.entries(dailyData).map(([date, data]) => ({
        date,
        revenue: data.revenue,
        orders: data.orders
      })))

      // Calculate top products
      const productSales = {}
      currentOrders?.forEach(order => {
        order.order_items?.forEach(item => {
          const key = item.product_name
          if (!productSales[key]) {
            productSales[key] = { name: key, revenue: 0, units: 0, category: item.products?.category || 'Unknown' }
          }
          productSales[key].revenue += parseFloat(item.total_price)
          productSales[key].units += item.quantity
        })
      })
      const sortedProducts = Object.values(productSales).sort((a, b) => b.revenue - a.revenue).slice(0, 5)
      setTopProducts(sortedProducts)

      // Calculate category breakdown
      const categoryData = {}
      currentOrders?.forEach(order => {
        order.order_items?.forEach(item => {
          const category = item.products?.category || 'Other'
          if (!categoryData[category]) {
            categoryData[category] = 0
          }
          categoryData[category] += parseFloat(item.total_price)
        })
      })
      setCategoryBreakdown(Object.entries(categoryData).map(([name, value]) => ({
        name,
        value,
        percentage: totalRevenue > 0 ? (value / totalRevenue) * 100 : 0
      })).sort((a, b) => b.value - a.value))

      // Set recent orders
      setRecentOrders((currentOrders || []).slice(-10).reverse())

      // Calculate customer segments
      const allCustomers = await supabase.from('customers').select('id, total_spent, total_orders')
      const customers = allCustomers.data || []

      const segments = {
        'New (1 order)': customers.filter(c => c.total_orders === 1).length,
        'Returning (2-3)': customers.filter(c => c.total_orders >= 2 && c.total_orders <= 3).length,
        'Loyal (4-10)': customers.filter(c => c.total_orders >= 4 && c.total_orders <= 10).length,
        'VIP (10+)': customers.filter(c => c.total_orders > 10).length
      }
      setCustomerSegments(Object.entries(segments).map(([name, count]) => ({
        name,
        count,
        percentage: customers.length > 0 ? (count / customers.length) * 100 : 0
      })))

    } catch (err) {
      console.error('Error loading analytics:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value) => `₹${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`

  const exportReport = () => {
    const report = {
      period: dateRange,
      generatedAt: new Date().toISOString(),
      stats,
      topProducts,
      categoryBreakdown
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `analytics-report-${dateRange}-${new Date().toISOString().split('T')[0]}.json`
    a.click()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-rose-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-500">Loading analytics...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-500 mt-1">Track your store performance and insights</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-rose-500"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="365d">Last year</option>
          </select>
          <button
            onClick={loadAnalytics}
            className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="w-5 h-5 text-gray-600" />
          </button>
          <button
            onClick={exportReport}
            className="flex items-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
          >
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Total Revenue */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-green-100 rounded-xl flex items-center justify-center">
              <IndianRupee className="w-6 h-6 text-green-600" />
            </div>
            <span className={`flex items-center gap-1 text-sm font-medium ${stats.revenueGrowth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.revenueGrowth >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {Math.abs(stats.revenueGrowth).toFixed(1)}%
            </span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{formatCurrency(stats.totalRevenue)}</p>
          <p className="text-sm text-gray-500 mt-1">Total Revenue</p>
          <Sparkline data={dailyRevenue.map(d => d.revenue)} color="green" />
        </div>

        {/* Total Orders */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <ShoppingCart className="w-6 h-6 text-blue-600" />
            </div>
            <span className={`flex items-center gap-1 text-sm font-medium ${stats.ordersGrowth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.ordersGrowth >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {Math.abs(stats.ordersGrowth).toFixed(1)}%
            </span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.totalOrders}</p>
          <p className="text-sm text-gray-500 mt-1">Total Orders</p>
          <Sparkline data={dailyRevenue.map(d => d.orders)} color="blue" />
        </div>

        {/* Average Order Value */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-purple-600" />
            </div>
          </div>
          <p className="text-3xl font-bold text-gray-900">{formatCurrency(stats.averageOrderValue)}</p>
          <p className="text-sm text-gray-500 mt-1">Average Order Value</p>
        </div>

        {/* New Customers */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="w-12 h-12 bg-rose-100 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-rose-600" />
            </div>
            <span className={`flex items-center gap-1 text-sm font-medium ${stats.customersGrowth >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.customersGrowth >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {Math.abs(stats.customersGrowth).toFixed(1)}%
            </span>
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.totalCustomers}</p>
          <p className="text-sm text-gray-500 mt-1">New Customers</p>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Over Time */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Revenue Over Time</h3>
          {dailyRevenue.length > 0 ? (
            <div className="space-y-3">
              {dailyRevenue.slice(-10).map((day, index) => (
                <div key={index} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-16">{day.date}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-8 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-green-500 to-green-600 h-full rounded-full flex items-center px-3"
                      style={{ width: `${Math.max(10, (day.revenue / Math.max(...dailyRevenue.map(d => d.revenue))) * 100)}%` }}
                    >
                      <span className="text-xs text-white font-medium">{formatCurrency(day.revenue)}</span>
                    </div>
                  </div>
                  <span className="text-xs text-gray-500 w-12">{day.orders} orders</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">No data available</div>
          )}
        </div>

        {/* Top Products */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Selling Products</h3>
          {topProducts.length > 0 ? (
            <div className="space-y-4">
              {topProducts.map((product, index) => (
                <div key={index} className="flex items-center gap-4">
                  <span className="w-6 h-6 bg-rose-100 rounded-full flex items-center justify-center text-xs font-bold text-rose-600">
                    {index + 1}
                  </span>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 line-clamp-1">{product.name}</p>
                    <p className="text-xs text-gray-500">{product.units} units sold</p>
                  </div>
                  <p className="font-semibold text-gray-900">{formatCurrency(product.revenue)}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">No sales data</div>
          )}
        </div>
      </div>

      {/* Category & Customer Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Breakdown */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Sales by Category</h3>
          {categoryBreakdown.length > 0 ? (
            <div className="space-y-4">
              {categoryBreakdown.map((category, index) => (
                <div key={index}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-900 capitalize">{category.name}</span>
                    <span className="text-sm text-gray-600">{formatCurrency(category.value)}</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-3">
                    <div
                      className="bg-gradient-to-r from-rose-500 to-rose-400 h-full rounded-full"
                      style={{ width: `${category.percentage}%` }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{category.percentage.toFixed(1)}% of total</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">No category data</div>
          )}
        </div>

        {/* Customer Segments */}
        <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Customer Segments</h3>
          {customerSegments.length > 0 ? (
            <div className="space-y-4">
              {customerSegments.map((segment, index) => {
                const colors = ['bg-blue-500', 'bg-green-500', 'bg-purple-500', 'bg-yellow-500']
                return (
                  <div key={index} className="flex items-center gap-4">
                    <div className={`w-4 h-4 rounded-full ${colors[index % colors.length]}`} />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-gray-900">{segment.name}</span>
                        <span className="text-gray-600">{segment.count} customers</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2 mt-2">
                        <div
                          className={`${colors[index % colors.length]} h-full rounded-full`}
                          style={{ width: `${segment.percentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">No customer data</div>
          )}
        </div>
      </div>

      {/* Recent Orders */}
      <div className="bg-white rounded-xl p-6 border border-gray-100 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Orders</h3>
        {recentOrders.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Order</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Items</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map(order => (
                  <tr key={order.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{order.order_number}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{order.customer_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{order.order_items?.length || 0}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{formatCurrency(parseFloat(order.total))}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                        order.status === 'delivered' ? 'bg-green-100 text-green-700' :
                        order.status === 'shipped' ? 'bg-blue-100 text-blue-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {order.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500">
                      {new Date(order.created_at).toLocaleDateString('en-IN', { dateStyle: 'medium' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">No recent orders</div>
        )}
      </div>

      {/* Insights Panel */}
      <div className="bg-gradient-to-r from-rose-500 to-rose-600 rounded-xl p-6 text-white">
        <div className="flex items-center gap-3 mb-4">
          <Activity className="w-6 h-6" />
          <h3 className="text-lg font-semibold">Quick Insights</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white/10 rounded-lg p-4">
            <p className="text-sm opacity-90">Best Selling Day</p>
            <p className="text-xl font-bold mt-1">
              {dailyRevenue.length > 0
                ? dailyRevenue.reduce((best, day) => day.revenue > best.revenue ? day : best).date
                : 'N/A'
              }
            </p>
          </div>
          <div className="bg-white/10 rounded-lg p-4">
            <p className="text-sm opacity-90">Highest Order</p>
            <p className="text-xl font-bold mt-1">
              {recentOrders.length > 0
                ? formatCurrency(Math.max(...recentOrders.map(o => parseFloat(o.total))))
                : 'N/A'
              }
            </p>
          </div>
          <div className="bg-white/10 rounded-lg p-4">
            <p className="text-sm opacity-90">Conversion Rate</p>
            <p className="text-xl font-bold mt-1">
              {stats.totalOrders > 0 && stats.totalCustomers > 0
                ? `${((stats.totalOrders / (stats.totalCustomers * 3)) * 100).toFixed(1)}%`
                : 'N/A'
              }
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
