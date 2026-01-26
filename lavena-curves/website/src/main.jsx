import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import AdminApp from './admin/AdminApp'
import './index.css'

// Check if we're on the admin route
const isAdminRoute = window.location.pathname.startsWith('/admin')

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      {isAdminRoute ? <AdminApp /> : <App />}
    </BrowserRouter>
  </React.StrictMode>,
)
