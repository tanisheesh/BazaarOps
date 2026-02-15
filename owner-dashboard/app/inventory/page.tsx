'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@supabase/supabase-js'
import { Plus, Package, AlertTriangle, TrendingUp, Edit2, X } from 'lucide-react'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_KEY || ''
)

// Toast notification component
function Toast({ message, type, onClose }: { message: string, type: 'success' | 'error', onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 3000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={`fixed bottom-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg flex items-center gap-3 animate-slide-up ${
      type === 'success' ? 'bg-green-600' : 'bg-red-600'
    } text-white`}>
      <span>{message}</span>
      <button onClick={onClose} className="hover:opacity-80">
        <X size={18} />
      </button>
    </div>
  )
}

export default function Inventory() {
  const [storeId, setStoreId] = useState<string>('')
  const [categories, setCategories] = useState<any[]>([])
  const [inventory, setInventory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{ message: string, type: 'success' | 'error' } | null>(null)
  
  // Modal states
  const [showCategoryModal, setShowCategoryModal] = useState(false)
  const [showProductModal, setShowProductModal] = useState(false)
  const [editingItem, setEditingItem] = useState<string | null>(null)
  
  // Form states
  const [categoryName, setCategoryName] = useState('')
  const [productForm, setProductForm] = useState({
    name: '',
    description: '',
    category_id: '',
    unit: 'kg',
    cost_price: '',
    unit_price: '',
    quantity: '',
    reorder_threshold: '',
    reorder_quantity: '',
    supplier_name: '',
    supplier_phone: '',
    supplier_whatsapp: ''
  })

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
  }

  useEffect(() => {
    const store_id = localStorage.getItem('store_id')
    if (store_id) {
      setStoreId(store_id)
      loadData(store_id)
    }
  }, [])

  const loadData = async (store_id: string) => {
    setLoading(true)
    try {
      const { data: cats } = await supabase
        .from('categories')
        .select('*')
        .eq('store_id', store_id)
        .order('name')
      
      setCategories(cats || [])

      const { data: inv } = await supabase
        .from('inventory')
        .select('*, products(*, categories(name))')
        .eq('store_id', store_id)
        .order('products(name)')
      
      setInventory(inv || [])
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddCategory = async () => {
    if (!categoryName.trim()) return

    try {
      const { error } = await supabase
        .from('categories')
        .insert({
          store_id: storeId,
          name: categoryName
        })

      if (error) throw error

      setCategoryName('')
      setShowCategoryModal(false)
      setTimeout(() => loadData(storeId), 500)
      showToast('Category added successfully!', 'success')
    } catch (error) {
      console.error('Error adding category:', error)
      showToast('Failed to add category', 'error')
    }
  }

  const handleAddProduct = async () => {
    if (!productForm.name.trim() || !productForm.category_id) {
      showToast('Please fill required fields', 'error')
      return
    }

    try {
      const { data: product, error: productError } = await supabase
        .from('products')
        .insert({
          store_id: storeId,
          name: productForm.name,
          description: productForm.description,
          category_id: productForm.category_id,
          unit: productForm.unit,
          cost_price: parseFloat(productForm.cost_price) || 0,
          supplier_name: productForm.supplier_name,
          supplier_phone: productForm.supplier_phone,
          supplier_whatsapp: productForm.supplier_whatsapp,
          sales_velocity: 'normal'
        })
        .select()
        .single()

      if (productError) throw productError

      const { error: invError } = await supabase
        .from('inventory')
        .insert({
          store_id: storeId,
          product_id: product.id,
          quantity: parseFloat(productForm.quantity) || 0,
          unit_price: parseFloat(productForm.unit_price) || 0,
          reorder_threshold: parseFloat(productForm.reorder_threshold) || 10,
          reorder_quantity: parseFloat(productForm.reorder_quantity) || 20
        })

      if (invError) throw invError

      setProductForm({
        name: '',
        description: '',
        category_id: '',
        unit: 'kg',
        cost_price: '',
        unit_price: '',
        quantity: '',
        reorder_threshold: '',
        reorder_quantity: '',
        supplier_name: '',
        supplier_phone: '',
        supplier_whatsapp: ''
      })
      setShowProductModal(false)
      loadData(storeId)
      showToast('Product added successfully!', 'success')
    } catch (error) {
      console.error('Error adding product:', error)
      showToast('Failed to add product', 'error')
    }
  }

  const updateInventory = async (invId: string, field: string, value: number) => {
    try {
      const { error } = await supabase
        .from('inventory')
        .update({ [field]: value })
        .eq('id', invId)

      if (error) throw error
      loadData(storeId)
      showToast('Updated successfully!', 'success')
    } catch (error) {
      console.error('Error updating:', error)
      showToast('Failed to update', 'error')
    }
  }

  const getLowStockItems = () => {
    return inventory.filter(item => 
      parseFloat(item.quantity) <= parseFloat(item.reorder_threshold)
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading inventory...</p>
        </div>
      </div>
    )
  }

  const lowStockItems = getLowStockItems()

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <style jsx global>{`
        input[type="number"]::-webkit-inner-spin-button,
        input[type="number"]::-webkit-outer-spin-button {
          -webkit-appearance: none;
          margin: 0;
        }
        input[type="number"] {
          -moz-appearance: textfield;
        }
        @keyframes slide-up {
          from {
            transform: translateY(100%);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>

      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Inventory Management</h1>
          <p className="text-gray-600">Manage your products and stock levels</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Products</p>
                <p className="text-2xl font-bold text-gray-900">{inventory.length}</p>
              </div>
              <Package className="w-12 h-12 text-blue-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Categories</p>
                <p className="text-2xl font-bold text-gray-900">{categories.length}</p>
              </div>
              <TrendingUp className="w-12 h-12 text-green-600" />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Low Stock Items</p>
                <p className="text-2xl font-bold text-red-600">{lowStockItems.length}</p>
              </div>
              <AlertTriangle className="w-12 h-12 text-red-600" />
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setShowCategoryModal(true)}
            className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus size={20} />
            Add Category
          </button>
          <button
            onClick={() => setShowProductModal(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center gap-2"
          >
            <Plus size={20} />
            Add Product
          </button>
        </div>

        {/* Low Stock Alert */}
        {lowStockItems.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
              <div>
                <h3 className="font-semibold text-red-900">Low Stock Alert</h3>
                <p className="text-sm text-red-700">
                  {lowStockItems.length} items need restocking
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Inventory Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stock</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Threshold</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {inventory.map((item) => {
                const isLowStock = parseFloat(item.quantity) <= parseFloat(item.reorder_threshold)
                const isEditing = editingItem === item.id
                
                return (
                  <tr key={item.id} className={isLowStock ? 'bg-red-50' : ''}>
                    <td className="px-6 py-4">
                      <div className="font-medium text-gray-900">{item.products.name}</div>
                      <div className="text-sm text-gray-500">{item.products.description}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {item.products.categories?.name || 'Uncategorized'}
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="number"
                        value={item.quantity}
                        onChange={(e) => updateInventory(item.id, 'quantity', parseFloat(e.target.value))}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                      <span className="ml-1 text-sm text-gray-500">{item.products.unit}</span>
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="number"
                        value={item.unit_price}
                        onChange={(e) => updateInventory(item.id, 'unit_price', parseFloat(e.target.value))}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="number"
                        value={item.reorder_threshold}
                        onChange={(e) => updateInventory(item.id, 'reorder_threshold', parseFloat(e.target.value))}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      />
                    </td>
                    <td className="px-6 py-4">
                      {isLowStock ? (
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">
                          Low Stock
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">
                          In Stock
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setEditingItem(isEditing ? null : item.id)}
                          className="text-blue-600 hover:text-blue-800"
                          title="Edit"
                        >
                          <Edit2 size={18} />
                        </button>
                        {isLowStock && item.products.supplier_whatsapp && (
                          <button
                            onClick={() => {
                              const message = `Hi, I need to reorder *${item.products.name}*.\n\nCurrent Stock: ${item.quantity} ${item.products.unit}\nReorder Quantity: ${item.reorder_quantity} ${item.products.unit}\n\nPlease confirm availability and price.`
                              const whatsappUrl = `https://wa.me/${item.products.supplier_whatsapp}?text=${encodeURIComponent(message)}`
                              window.open(whatsappUrl, '_blank')
                            }}
                            className="text-green-600 hover:text-green-800"
                            title="Contact Supplier on WhatsApp"
                          >
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                            </svg>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Category Modal */}
        {showCategoryModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4">Add Category</h2>
              <input
                type="text"
                value={categoryName}
                onChange={(e) => setCategoryName(e.target.value)}
                placeholder="Category name"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleAddCategory}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg"
                >
                  Add
                </button>
                <button
                  onClick={() => setShowCategoryModal(false)}
                  className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 py-2 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Product Modal */}
        {showProductModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 overflow-y-auto">
            <div className="bg-white rounded-lg p-6 w-full max-w-2xl m-4">
              <h2 className="text-xl font-bold mb-4">Add Product</h2>
              
              <div className="grid grid-cols-2 gap-4 max-h-96 overflow-y-auto">
                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Product Name *</label>
                  <input
                    type="text"
                    value={productForm.name}
                    onChange={(e) => setProductForm({...productForm, name: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    value={productForm.description}
                    onChange={(e) => setProductForm({...productForm, description: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={2}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Category *</label>
                  <select
                    value={productForm.category_id}
                    onChange={(e) => setProductForm({...productForm, category_id: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Select category</option>
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Unit</label>
                  <select
                    value={productForm.unit}
                    onChange={(e) => setProductForm({...productForm, unit: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="kg">Kg</option>
                    <option value="liter">Liter</option>
                    <option value="piece">Piece</option>
                    <option value="box">Box</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Cost Price</label>
                  <input
                    type="number"
                    value={productForm.cost_price}
                    onChange={(e) => setProductForm({...productForm, cost_price: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Selling Price *</label>
                  <input
                    type="number"
                    value={productForm.unit_price}
                    onChange={(e) => setProductForm({...productForm, unit_price: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Initial Quantity</label>
                  <input
                    type="number"
                    value={productForm.quantity}
                    onChange={(e) => setProductForm({...productForm, quantity: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Reorder Threshold</label>
                  <input
                    type="number"
                    value={productForm.reorder_threshold}
                    onChange={(e) => setProductForm({...productForm, reorder_threshold: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Reorder Quantity</label>
                  <input
                    type="number"
                    value={productForm.reorder_quantity}
                    onChange={(e) => setProductForm({...productForm, reorder_quantity: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Supplier Name</label>
                  <input
                    type="text"
                    value={productForm.supplier_name}
                    onChange={(e) => setProductForm({...productForm, supplier_name: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Supplier Phone</label>
                  <input
                    type="tel"
                    value={productForm.supplier_phone}
                    onChange={(e) => setProductForm({...productForm, supplier_phone: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Supplier WhatsApp</label>
                  <input
                    type="tel"
                    value={productForm.supplier_whatsapp}
                    onChange={(e) => setProductForm({...productForm, supplier_whatsapp: e.target.value})}
                    placeholder="919876543210"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="flex gap-2 mt-6">
                <button
                  onClick={handleAddProduct}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg"
                >
                  Add Product
                </button>
                <button
                  onClick={() => setShowProductModal(false)}
                  className="flex-1 bg-gray-200 hover:bg-gray-300 text-gray-800 py-2 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Toast Notification */}
        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
      </div>
    </div>
  )
}
