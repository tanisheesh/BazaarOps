'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Order {
  order_id: string
  customer_name: string
  customer_phone: string
  total_amount: number
  status: string
  payment_status: string
  created_at: string
  notes: string
}

export default function Orders() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [storeId, setStoreId] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const ordersPerPage = 10
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'
  const CUSTOMER_BOT_TOKEN = process.env.NEXT_PUBLIC_CUSTOMER_BOT_TOKEN

  useEffect(() => {
    const store_id = localStorage.getItem('store_id')
    setStoreId(store_id)
    
    if (store_id) {
      fetchOrders(store_id)
      
      // Refresh every 10 seconds
      const interval = setInterval(() => fetchOrders(store_id), 10000)
      return () => clearInterval(interval)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchOrders = async (store_id: string) => {
    try {
      const response = await fetch(`${API_URL}/api/owner/orders/${store_id}`)
      const data = await response.json()
      setOrders(data.orders || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching orders:', error)
      setLoading(false)
    }
  }

  const updateOrderStatus = async (orderId: string, newStatus: string, customerPhone?: string) => {
    if (!storeId) return
    
    try {
      const response = await fetch(`${API_URL}/api/owner/orders/${orderId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      })
      
      if (response.ok) {
        // If order completed, send delivery message to customer
        if (newStatus === 'completed' && customerPhone) {
          await sendDeliveryNotification(customerPhone, orderId)
        }
        await fetchOrders(storeId)
      }
    } catch (error) {
      console.error('Error updating order:', error)
    }
  }

  const sendDeliveryNotification = async (phone: string, orderId: string) => {
    try {
      console.log('📱 Sending delivery notification to:', phone)
      
      // Get customer's telegram chat_id from database
      const response = await fetch(`${API_URL}/api/owner/customer-telegram/${phone}`)
      const data = await response.json()
      
      console.log('📱 Customer telegram data:', data)
      
      if (data.telegram_chat_id) {
        // Send message via Telegram bot
        const message = `✅ *Order Delivered!*\n\nYour order #${orderId.substring(0, 8)} has been successfully delivered.\n\nThank you for shopping with us! 🎉`
        
        console.log('📱 Sending message to chat_id:', data.telegram_chat_id)
        console.log('📱 Using bot token:', CUSTOMER_BOT_TOKEN ? 'Token present' : 'Token missing')
        
        const telegramResponse = await fetch(`https://api.telegram.org/bot${CUSTOMER_BOT_TOKEN}/sendMessage`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chat_id: data.telegram_chat_id,
            text: message,
            parse_mode: 'Markdown'
          })
        })
        
        const telegramResult = await telegramResponse.json()
        console.log('📱 Telegram API response:', telegramResult)
        
        if (telegramResult.ok) {
          console.log('✅ Message sent successfully!')
        } else {
          console.error('❌ Telegram API error:', telegramResult)
        }
      } else {
        console.log('⚠️ No telegram_chat_id found for customer')
      }
    } catch (error) {
      console.error('❌ Error sending delivery notification:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800'
      case 'confirmed': return 'bg-blue-100 text-blue-800'
      case 'completed': return 'bg-green-100 text-green-800'
      case 'cancelled': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredOrders = filter === 'all' 
    ? orders 
    : orders.filter(order => order.status === filter)

  // Pagination
  const indexOfLastOrder = currentPage * ordersPerPage
  const indexOfFirstOrder = indexOfLastOrder - ordersPerPage
  const currentOrders = filteredOrders.slice(indexOfFirstOrder, indexOfLastOrder)
  const totalPages = Math.ceil(filteredOrders.length / ordersPerPage)

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading orders...</div>
      </div>
    )
  }

  const confirmedCount = orders.filter(o => o.status === 'confirmed').length
  const completedCount = orders.filter(o => o.status === 'completed').length

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">🛒 Orders</h1>
              <p className="text-sm text-gray-600 mt-1">
                Manage customer orders
              </p>
            </div>
            <Link 
              href="/"
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
            <p className="text-sm text-gray-600 mb-1">Total Orders</p>
            <p className="text-3xl font-bold text-blue-600">{orders.length}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Confirmed</p>
            <p className="text-3xl font-bold text-blue-600">{confirmedCount}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <p className="text-sm text-gray-600 mb-1">Completed</p>
            <p className="text-3xl font-bold text-green-600">{completedCount}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="mb-6 flex space-x-2">
          {['all', 'confirmed', 'completed'].map(status => (
            <button
              key={status}
              onClick={() => {
                setFilter(status)
                setCurrentPage(1)
              }}
              className={`px-4 py-2 rounded-lg font-medium ${
                filter === status
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-50 border border-gray-300'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        {/* Orders List */}
        <div className="space-y-4">
          {currentOrders.length === 0 ? (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center text-gray-500">
              No orders found
            </div>
          ) : (
            currentOrders.map((order) => (
              <div key={order.order_id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Order #{order.order_id.substring(0, 8)}
                      </h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                        {order.status.toUpperCase()}
                      </span>
                      {order.payment_status === 'unpaid' && (
                        <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          CREDIT
                        </span>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div>
                        <p className="text-sm text-gray-600">Customer</p>
                        <p className="font-medium text-gray-900">{order.customer_name}</p>
                        <p className="text-sm text-gray-600">{order.customer_phone}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Total Amount</p>
                        <p className="text-2xl font-bold text-green-600">₹{order.total_amount.toFixed(2)}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Order Date</p>
                        <p className="font-medium text-gray-900">
                          {new Date(order.created_at).toLocaleString('en-IN')}
                        </p>
                      </div>
                      {order.notes && (
                        <div>
                          <p className="text-sm text-gray-600">Notes</p>
                          <p className="text-gray-900">{order.notes}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="ml-6 flex flex-col space-y-2">
                    {order.status === 'confirmed' && (
                      <button
                        onClick={() => updateOrderStatus(order.order_id, 'completed', order.customer_phone)}
                        className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium"
                      >
                        Mark as Delivered
                      </button>
                    )}
                    {order.status === 'completed' && (
                      <span className="px-4 py-2 bg-green-100 text-green-800 rounded-lg text-sm font-medium text-center">
                        ✓ Delivered
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-6 flex justify-center items-center space-x-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Previous
            </button>
            
            <span className="px-4 py-2 text-gray-700">
              Page {currentPage} of {totalPages}
            </span>
            
            <button
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
              className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
