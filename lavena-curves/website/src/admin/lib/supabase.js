import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://xarkrwgpyltlgtajnnfc.supabase.co'
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inhhcmtyd2dweWx0bGd0YWpubmZjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc1OTM4MzIsImV4cCI6MjA4MzE2OTgzMn0._YX-scuMAxfBg5-_vwxQsWkZYwuWgLLHBFWquSLNz1c'

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Helper functions for common operations
export const db = {
  // Products
  async getProducts(options = {}) {
    let query = supabase.from('products').select('*')
    if (options.isActive !== undefined) query = query.eq('is_active', options.isActive)
    if (options.category) query = query.eq('category', options.category)
    if (options.limit) query = query.limit(options.limit)
    if (options.orderBy) query = query.order(options.orderBy, { ascending: options.ascending ?? false })
    return query
  },

  async getProduct(id) {
    return supabase.from('products').select('*, product_variants(*)').eq('id', id).single()
  },

  async createProduct(data) {
    return supabase.from('products').insert(data).select().single()
  },

  async updateProduct(id, data) {
    return supabase.from('products').update({ ...data, updated_at: new Date().toISOString() }).eq('id', id).select().single()
  },

  async deleteProduct(id) {
    return supabase.from('products').delete().eq('id', id)
  },

  // Orders
  async getOrders(options = {}) {
    let query = supabase.from('orders').select('*, order_items(*), customers(email, first_name, last_name)')
    if (options.status) query = query.eq('status', options.status)
    if (options.paymentStatus) query = query.eq('payment_status', options.paymentStatus)
    if (options.limit) query = query.limit(options.limit)
    query = query.order('created_at', { ascending: false })
    return query
  },

  async getOrder(id) {
    return supabase.from('orders').select('*, order_items(*, products(name, images)), customers(*)').eq('id', id).single()
  },

  async updateOrderStatus(id, status, notes = null) {
    const { data: order } = await supabase.from('orders').update({ status, updated_at: new Date().toISOString() }).eq('id', id).select().single()
    if (order) {
      await supabase.from('order_status_history').insert({ order_id: id, status, notes })
    }
    return { data: order }
  },

  async updateOrderTracking(id, trackingNumber, courierName, trackingUrl) {
    return supabase.from('orders').update({
      tracking_number: trackingNumber,
      courier_name: courierName,
      tracking_url: trackingUrl,
      updated_at: new Date().toISOString()
    }).eq('id', id).select().single()
  },

  // Customers
  async getCustomers(options = {}) {
    let query = supabase.from('customers').select('*')
    if (options.search) {
      query = query.or(`email.ilike.%${options.search}%,first_name.ilike.%${options.search}%,last_name.ilike.%${options.search}%,phone.ilike.%${options.search}%`)
    }
    if (options.limit) query = query.limit(options.limit)
    query = query.order('created_at', { ascending: false })
    return query
  },

  async getCustomer(id) {
    return supabase.from('customers').select('*, orders(*)').eq('id', id).single()
  },

  // Analytics
  async getDailySales(days = 30) {
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - days)
    return supabase
      .from('orders')
      .select('created_at, total, payment_status')
      .eq('payment_status', 'paid')
      .gte('created_at', startDate.toISOString())
      .order('created_at', { ascending: true })
  },

  async getStats() {
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const thisMonth = new Date(today.getFullYear(), today.getMonth(), 1)

    const [
      { count: totalOrders },
      { count: todayOrders },
      { data: revenue },
      { count: totalCustomers },
      { data: lowStock }
    ] = await Promise.all([
      supabase.from('orders').select('*', { count: 'exact', head: true }).eq('payment_status', 'paid'),
      supabase.from('orders').select('*', { count: 'exact', head: true }).eq('payment_status', 'paid').gte('created_at', today.toISOString()),
      supabase.from('orders').select('total').eq('payment_status', 'paid').gte('created_at', thisMonth.toISOString()),
      supabase.from('customers').select('*', { count: 'exact', head: true }),
      supabase.from('products').select('id, name, stock_quantity').eq('is_active', true).lt('stock_quantity', 5)
    ])

    const monthlyRevenue = revenue?.reduce((sum, o) => sum + parseFloat(o.total), 0) || 0

    return {
      totalOrders,
      todayOrders,
      monthlyRevenue,
      totalCustomers,
      lowStockProducts: lowStock || []
    }
  },

  // Inventory
  async updateStock(productId, quantity, type = 'adjustment', notes = '') {
    const { data: product } = await supabase.from('products').select('stock_quantity').eq('id', productId).single()
    if (!product) return { error: 'Product not found' }

    const newQuantity = product.stock_quantity + quantity
    await supabase.from('products').update({ stock_quantity: newQuantity, updated_at: new Date().toISOString() }).eq('id', productId)

    await supabase.from('inventory_transactions').insert({
      product_id: productId,
      type,
      quantity_change: quantity,
      quantity_before: product.stock_quantity,
      quantity_after: newQuantity,
      notes
    })

    return { data: { newQuantity } }
  },

  // Affiliates
  async getAffiliates() {
    return supabase.from('affiliates').select('*').order('created_at', { ascending: false })
  },

  async createAffiliate(data) {
    return supabase.from('affiliates').insert(data).select().single()
  },

  // Discount Codes
  async getDiscountCodes() {
    return supabase.from('discount_codes').select('*').order('created_at', { ascending: false })
  },

  async createDiscountCode(data) {
    return supabase.from('discount_codes').insert(data).select().single()
  },

  // Sessions & Analytics
  async getRecentSessions(limit = 50) {
    return supabase.from('sessions').select('*').order('started_at', { ascending: false }).limit(limit)
  },

  async getAbandonedCarts(recovered = false) {
    return supabase.from('abandoned_carts').select('*').eq('recovered', recovered).order('created_at', { ascending: false })
  },

  // Marketplace
  async getMarketplaceConnections() {
    return supabase.from('marketplace_connections').select('*').order('created_at', { ascending: false })
  },

  async getMarketplaceOrders(marketplace = null) {
    let query = supabase.from('marketplace_orders').select('*')
    if (marketplace) query = query.eq('marketplace', marketplace)
    return query.order('created_at', { ascending: false })
  }
}

export default supabase
