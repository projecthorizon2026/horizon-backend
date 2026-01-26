import { useState, useEffect, createContext, useContext } from 'react'
import { supabase } from '../lib/supabase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [admin, setAdmin] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for existing session
    const storedAdmin = localStorage.getItem('admin')
    if (storedAdmin) {
      try {
        setAdmin(JSON.parse(storedAdmin))
      } catch (e) {
        localStorage.removeItem('admin')
      }
    }
    setLoading(false)
  }, [])

  const login = async (email, password) => {
    try {
      // For demo, check against admins table
      // In production, use proper password hashing
      const { data: adminData, error } = await supabase
        .from('admins')
        .select('*')
        .eq('email', email.toLowerCase())
        .eq('is_active', true)
        .single()

      if (error || !adminData) {
        return { error: 'Invalid credentials' }
      }

      // Update last login
      await supabase
        .from('admins')
        .update({ last_login_at: new Date().toISOString() })
        .eq('id', adminData.id)

      const adminSession = {
        id: adminData.id,
        email: adminData.email,
        name: adminData.name,
        role: adminData.role,
        avatar_url: adminData.avatar_url
      }

      setAdmin(adminSession)
      localStorage.setItem('admin', JSON.stringify(adminSession))

      return { data: adminSession }
    } catch (err) {
      return { error: err.message }
    }
  }

  const logout = () => {
    setAdmin(null)
    localStorage.removeItem('admin')
  }

  const value = {
    admin,
    loading,
    login,
    logout,
    isAuthenticated: !!admin
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default useAuth
