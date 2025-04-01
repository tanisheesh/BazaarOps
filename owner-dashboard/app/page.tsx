'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface DashboardStats {
  today_orders: number
  today_revenue: number
  today_profit: number
  low_stock_count: number
  low_stock_items: Array<{
    name: string
    quantity: number
    threshold: number
  }>
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [storeId, setStoreId] = useState<string | null>(null)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

  useEffect(() => {
    // Get store_id from localStorage
    const storedStoreId = localStorage.getItem('store_id')
    setStoreId(storedStoreId)
    
    if (storedStoreId) {
      fetchStats(storedStoreId)
      
      // Refresh every 30 seconds
      const interval = setInterval(() => fetchStats(storedStoreId), 30000)
      return () => clearInterval(interval)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchStats = async (store_id: string) => {
    try {
      const response = await fetch(`${API_URL}/api/owner/dashboard/${store_id}`)
      const data = await response.json()
      setStats(data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching stats:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading dashboard...</div>
      </div>
    )
  }

  if (!storeId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-xl text-red-600 mb-4">Store ID not found</div>
          <Link href="/auth" className="text-blue-600 hover:underline">
            Please login again
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                🛒 BazaarOps Dashboard
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Welcome back! Here's your store overview
              </p>
            </div>
            <button
              onClick={() => {
                localStorage.removeItem('auth_token')
                localStorage.removeItem('user')
                localStorage.removeItem('store_id')
                document.cookie = 'auth_token=; path=/; max-age=0'
                window.location.href = '/auth'
              }}
              className="px-4 py-2 text-sm text-red-600 hover:text-red-800 font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {/* Today's Orders */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Today's Orders</p>
                <p className="text-3xl font-bold text-blue-600">
                  {stats?.today_orders || 0}
                </p>
              </div>
              <div className="text-4xl">📦</div>
            </div>
          </div>

          {/* Today's Revenue */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Today's Revenue</p>
                <p className="text-3xl font-bold text-green-600">
                  ₹{stats?.today_revenue.toFixed(2) || 0}
                </p>
              </div>
              <div className="text-4xl">💰</div>
            </div>
          </div>

          {/* Today's Profit */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Today's Profit</p>
                <p className="text-3xl font-bold text-emerald-600">
                  ₹{stats?.today_profit?.toFixed(2) || '0.00'}
                </p>
              </div>
              <div className="text-4xl">📈</div>
            </div>
          </div>

          {/* Low Stock */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 mb-1">Low Stock Items</p>
                <p className="text-3xl font-bold text-orange-600">
                  {stats?.low_stock_count || 0}
                </p>
              </div>
              <div className="text-4xl">⚠️</div>
            </div>
          </div>
        </div>

        {/* Low Stock Alert */}
        {stats && stats.low_stock_count > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-6 mb-8">
            <h3 className="text-lg font-semibold text-orange-900 mb-4 flex items-center">
              <span className="text-2xl mr-2">⚠️</span>
              Low Stock Alert
            </h3>
            <div className="space-y-3">
              {stats.low_stock_items.map((item, index) => (
                <div 
                  key={index}
                  className="flex justify-between items-center bg-white p-3 rounded border border-orange-200"
                >
                  <span className="font-medium text-orange-900">{item.name}</span>
                  <span className="text-orange-700">
                    {item.quantity.toFixed(1)} / {item.threshold.toFixed(1)} (threshold)
                  </span>
                </div>
              ))}
            </div>
            <Link 
              href="/inventory"
              className="inline-block mt-4 text-orange-700 hover:text-orange-900 font-medium"
            >
              Go to Inventory →
            </Link>
          </div>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <Link 
            href="/inventory" 
            className="bg-blue-600 hover:bg-blue-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">📦</div>
            <div className="font-semibold">Inventory</div>
          </Link>
          
          <Link 
            href="/orders" 
            className="bg-green-600 hover:bg-green-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">🛒</div>
            <div className="font-semibold">Orders</div>
          </Link>
          
          <Link 
            href="/credit" 
            className="bg-red-600 hover:bg-red-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">💳</div>
            <div className="font-semibold">Credit</div>
          </Link>
          
          <Link 
            href="/customers" 
            className="bg-purple-600 hover:bg-purple-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">👥</div>
            <div className="font-semibold">Customers</div>
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-1 gap-4">
          <Link 
            href="/settings" 
            className="bg-orange-600 hover:bg-orange-700 text-white p-6 rounded-lg text-center transition-colors"
          >
            <div className="text-4xl mb-3">⚙️</div>
            <div className="font-semibold">Settings</div>
          </Link>
        </div>
      </main>
    </div>
  )
}
