import { useState, useEffect } from 'react'
import { AuthProvider, useAuth } from './hooks/useAuth.jsx'
import AdminNav from './components/AdminNav'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import Products from './pages/Products'
import Customers from './pages/Customers'
import Inventory from './pages/Inventory'
import Analytics from './pages/Analytics'
import Affiliates from './pages/Affiliates'
import Discounts from './pages/Discounts'
import Settings from './pages/Settings'
import Marketplace from './pages/Marketplace'
import EmailCampaigns from './pages/EmailCampaigns'
import SocialCommerce from './pages/SocialCommerce'
import Dropshipping from './pages/Dropshipping'
import SEO from './pages/SEO'
import { db } from './lib/supabase'

function AdminContent() {
  const { admin, login, logout, isAuthenticated, loading } = useAuth()
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [pendingOrders, setPendingOrders] = useState(0)
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      loadPendingOrders()
    }
  }, [isAuthenticated])

  const loadPendingOrders = async () => {
    try {
      const { data } = await db.getOrders({ status: 'pending', limit: 100 })
      setPendingOrders(data?.length || 0)
    } catch (err) {
      console.error('Error loading pending orders:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Login onLogin={login} />
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard onNavigate={setCurrentPage} />
      case 'orders':
        return <Orders />
      case 'products':
        return <Products />
      case 'inventory':
        return <Inventory />
      case 'customers':
        return <Customers />
      case 'discounts':
        return <Discounts />
      case 'affiliates':
        return <Affiliates />
      case 'email-campaigns':
        return <EmailCampaigns />
      case 'marketplace':
        return <Marketplace />
      case 'social':
        return <SocialCommerce />
      case 'dropshipping':
        return <Dropshipping />
      case 'analytics':
        return <Analytics />
      case 'seo':
        return <SEO />
      case 'settings':
        return <Settings />
      default:
        return <Dashboard onNavigate={setCurrentPage} />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <AdminNav
        currentPage={currentPage}
        onNavigate={setCurrentPage}
        admin={admin}
        onLogout={logout}
        pendingOrders={pendingOrders}
        isMobileOpen={isMobileOpen}
        setIsMobileOpen={setIsMobileOpen}
      />
      <main className="pt-16 lg:pt-0 lg:ml-64 p-4 lg:p-8">
        {renderPage()}
      </main>
    </div>
  )
}

export default function AdminApp() {
  return (
    <AuthProvider>
      <AdminContent />
    </AuthProvider>
  )
}
