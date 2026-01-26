import { useState, useEffect } from 'react'
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Users,
  BarChart3,
  Settings,
  LogOut,
  Store,
  Percent,
  Users2,
  Mail,
  Search,
  TrendingUp,
  Globe,
  Instagram,
  ChevronDown,
  ChevronRight,
  Boxes,
  Truck,
  Menu,
  X
} from 'lucide-react'

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'orders', label: 'Orders', icon: ShoppingCart, badge: 'orders' },
  { id: 'products', label: 'Products', icon: Package },
  { id: 'inventory', label: 'Inventory', icon: Boxes },
  { id: 'customers', label: 'Customers', icon: Users },
  {
    id: 'marketing',
    label: 'Marketing',
    icon: TrendingUp,
    children: [
      { id: 'discounts', label: 'Discount Codes', icon: Percent },
      { id: 'affiliates', label: 'Affiliates', icon: Users2 },
      { id: 'email-campaigns', label: 'Email Campaigns', icon: Mail },
    ]
  },
  {
    id: 'channels',
    label: 'Sales Channels',
    icon: Globe,
    children: [
      { id: 'marketplace', label: 'Marketplaces', icon: Store },
      { id: 'social', label: 'Social Commerce', icon: Instagram },
      { id: 'dropshipping', label: 'Dropshipping', icon: Truck },
    ]
  },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'seo', label: 'SEO & Keywords', icon: Search },
  { id: 'settings', label: 'Settings', icon: Settings },
]

export default function AdminNav({ currentPage, onNavigate, admin, onLogout, pendingOrders = 0, isMobileOpen, setIsMobileOpen }) {
  const [expandedMenus, setExpandedMenus] = useState(['marketing', 'channels'])

  // Close mobile menu when navigating
  const handleNavigate = (id) => {
    onNavigate(id)
    setIsMobileOpen(false)
  }

  const toggleMenu = (menuId) => {
    setExpandedMenus(prev =>
      prev.includes(menuId)
        ? prev.filter(id => id !== menuId)
        : [...prev, menuId]
    )
  }

  const renderMenuItem = (item, isChild = false) => {
    const Icon = item.icon
    const isActive = currentPage === item.id
    const hasChildren = item.children?.length > 0
    const isExpanded = expandedMenus.includes(item.id)

    if (hasChildren) {
      return (
        <div key={item.id}>
          <button
            onClick={() => toggleMenu(item.id)}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
              ${isExpanded ? 'bg-rose-50 text-rose-700' : 'text-gray-600 hover:bg-gray-100'}`}
          >
            <div className="flex items-center gap-3">
              <Icon className="w-5 h-5" />
              <span>{item.label}</span>
            </div>
            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </button>
          {isExpanded && (
            <div className="ml-4 mt-1 space-y-1 border-l-2 border-gray-200 pl-3">
              {item.children.map(child => renderMenuItem(child, true))}
            </div>
          )}
        </div>
      )
    }

    return (
      <button
        key={item.id}
        onClick={() => handleNavigate(item.id)}
        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
          ${isActive
            ? 'bg-rose-600 text-white shadow-sm'
            : isChild
              ? 'text-gray-500 hover:bg-gray-100 hover:text-gray-700'
              : 'text-gray-600 hover:bg-gray-100'
          }`}
      >
        <div className="flex items-center gap-3">
          <Icon className={`w-5 h-5 ${isChild ? 'w-4 h-4' : ''}`} />
          <span>{item.label}</span>
        </div>
        {item.badge === 'orders' && pendingOrders > 0 && (
          <span className={`px-2 py-0.5 text-xs font-bold rounded-full ${isActive ? 'bg-white text-rose-600' : 'bg-rose-100 text-rose-600'}`}>
            {pendingOrders}
          </span>
        )}
      </button>
    )
  }

  return (
    <>
      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4 z-40">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-rose-500 to-pink-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">LC</span>
          </div>
          <h1 className="font-bold text-gray-900 text-sm">Lumière Curves</h1>
        </div>
        <button
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
        >
          {isMobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Overlay */}
      {isMobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        w-64 bg-white border-r border-gray-200 flex flex-col h-screen fixed left-0 top-0 z-50
        transition-transform duration-300 ease-in-out
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full'}
        lg:translate-x-0
      `}>
        {/* Logo */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-rose-500 to-pink-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-lg">LC</span>
              </div>
              <div>
                <h1 className="font-bold text-gray-900">Lumière Curves</h1>
                <p className="text-xs text-gray-500">Admin Dashboard</p>
              </div>
            </div>
            <button
              onClick={() => setIsMobileOpen(false)}
              className="lg:hidden p-1 rounded hover:bg-gray-100"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {menuItems.map(item => renderMenuItem(item))}
        </nav>

        {/* Admin Profile */}
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 bg-gradient-to-br from-gray-400 to-gray-500 rounded-full flex items-center justify-center">
              <span className="text-white font-medium text-sm">
                {admin?.name?.charAt(0) || admin?.email?.charAt(0) || 'A'}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{admin?.name || 'Admin'}</p>
              <p className="text-xs text-gray-500 truncate">{admin?.email}</p>
            </div>
          </div>
          <button
            onClick={onLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  )
}
