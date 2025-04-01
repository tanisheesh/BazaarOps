'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface Customer {
  id: string
  name: string
  phone: string
  address: string
  created_at: string
}

export default function Customers() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [storeId, setStoreId] = useState<string | null>(null)
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

  useEffect(() => {
    const store_id = localStorage.getItem('store_id')
    setStoreId(store_id)
    
    if (store_id) {
      fetchCustomers(store_id)
    } else {
      setLoading(false)
    }
  }, [])

  const fetchCustomers = async (store_id: string) => {
    try {
      const response = await fetch(`${API_URL}/api/owner/customers/${store_id}`)
      const data = await response.json()
      setCustomers(data.customers || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching customers:', error)
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading customers...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">👥 Customers</h1>
              <p className="text-sm text-gray-600 mt-1">Your customer list</p>
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
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-lg font-semibold mb-4">Total Customers: {customers.length}</h2>
          <div className="space-y-3">
            {customers.map((customer) => (
              <div key={customer.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between">
                  <div>
                    <p className="font-semibold text-gray-900">{customer.name}</p>
                    <p className="text-sm text-gray-600">{customer.phone}</p>
                    {customer.address && (
                      <p className="text-sm text-gray-500 mt-1">{customer.address}</p>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    Joined: {new Date(customer.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
