'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface CreditOrder {
  order_id: string
  customer_name: string
  customer_phone: string
  total_amount: number
  status: string
  created_at: string
  days_pending: number
}

export default function CreditManagement() {
  const [creditOrders, setCreditOrders] = useState<CreditOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [storeId, setStoreId] = useState<string | null>(null)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

  useEffect(() => {
    const store_id = localStorage.getItem('store_id')
    setStoreId(store_id)
    
    if (store_id) {
      fetchCreditOrders(store_id)
      const interval = setInterval(() => fetchCreditOrders(store_id), 30000)
      return () => clearInterval(interval)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchCreditOrders = async (store_id: string) => {
    try {
      const response = await fetch(`${API_URL}/api/owner/orders/${store_id}`)
      const data = await response.json()
      
      // Filter unpaid orders and calculate days pending
      const unpaidOrders = (data.orders || [])
        .filter((order: any) => order.payment_status === 'unpaid')
        .map((order: any) => ({
          ...order,
          days_pending: Math.floor(
            (Date.now() - new Date(order.created_at).getTime()) / (1000 * 60 * 60 * 24)
          )
        }))
      
      setCreditOrders(unpaidOrders)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching credit orders:', error)
      setLoading(false)
    }
  }

  const markAsPaid = async (orderId: string) => {
    if (!storeId) return
    
    try {
      const response = await fetch(`${API_URL}/api/owner/orders/${orderId}/payment`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ payment_status: 'paid' })
      })
      
      if (response.ok) {
        await fetchCreditOrders(storeId)
        alert('✅ Payment marked as received!')
      }
    } catch (error) {
      console.error('Error updating payment:', error)
      alert('❌ Failed to update payment status')
    }
  }

  const totalCredit = creditOrders.reduce((sum, order) => sum + order.total_amount, 0)
  
  // Group by customer
  const customerCredits = creditOrders.reduce((acc: any, order) => {
    if (!acc[order.customer_phone]) {
      acc[order.customer_phone] = {
        name: order.customer_name,
        phone: order.customer_phone,
        total: 0,
        orders: []
      }
    }
    acc[order.customer_phone].total += order.total_amount
    acc[order.customer_phone].orders.push(order)
    return acc
  }, {})

  const customerList = Object.values(customerCredits).sort((a: any, b: any) => b.total - a.total)

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading credit data...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">💳 Credit Management</h1>
              <p className="text-sm text-gray-600 mt-1">Track and manage unpaid orders</p>
            </div>
            <Link 
              href="/dashboard"
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              ← Back to Dashboard
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Total Credit Outstanding</p>
            <p className="text-3xl font-bold text-red-600">₹{totalCredit.toFixed(2)}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Unpaid Orders</p>
            <p className="text-3xl font-bold text-orange-600">{creditOrders.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Customers with Credit</p>
            <p className="text-3xl font-bold text-purple-600">{customerList.length}</p>
          </div>
        </div>

        {creditOrders.length === 0 ? (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">🎉</div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">No Outstanding Credit!</h3>
            <p className="text-gray-600">All orders have been paid. Great job!</p>
          </div>
        ) : (
          <>
            {/* Customer-wise Breakdown */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-8">
              <h2 className="text-lg font-semibold mb-4">Customer-wise Credit</h2>
              <div className="space-y-3">
                {customerList.map((customer: any, index: number) => (
                  <div key={index} className="flex justify-between items-center p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div>
                      <p className="font-semibold text-gray-900">{customer.name}</p>
                      <p className="text-sm text-gray-600">{customer.phone}</p>
                      <p className="text-xs text-gray-500 mt-1">{customer.orders.length} unpaid order(s)</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-red-600">₹{customer.total.toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* All Credit Orders */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold mb-4">All Unpaid Orders</h2>
              <div className="space-y-4">
                {creditOrders.map((order) => (
                  <div key={order.order_id} className="border border-red-200 rounded-lg p-4 bg-red-50">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="font-semibold text-gray-900">
                            Order #{order.order_id.substring(0, 8)}
                          </h3>
                          <span className="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs font-medium">
                            UNPAID
                          </span>
                          {order.days_pending > 7 && (
                            <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-medium">
                              ⚠️ {order.days_pending} days overdue
                            </span>
                          )}
                        </div>
                        
                        <div className="grid grid-cols-3 gap-4 mt-3">
                          <div>
                            <p className="text-xs text-gray-600">Customer</p>
                            <p className="font-medium text-gray-900">{order.customer_name}</p>
                            <p className="text-sm text-gray-600">{order.customer_phone}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-600">Amount</p>
                            <p className="text-xl font-bold text-red-600">₹{order.total_amount.toFixed(2)}</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-600">Order Date</p>
                            <p className="text-sm text-gray-900">
                              {new Date(order.created_at).toLocaleDateString('en-IN')}
                            </p>
                            <p className="text-xs text-gray-600">{order.days_pending} days ago</p>
                          </div>
                        </div>
                      </div>
                      
                      <button
                        onClick={() => markAsPaid(order.order_id)}
                        className="ml-4 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium"
                      >
                        💰 Mark as Paid
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
