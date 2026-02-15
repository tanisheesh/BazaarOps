'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@supabase/supabase-js'
import { Plus, Package, AlertTriangle, TrendingUp, Edit2, Trash2 } from 'lucide-react'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_KEY || ''
)

export default function Inventory() {
  const [storeId, setStoreId] = useState<string>('')
  const [categories, setCategories] = useState<any[]>([])
  const [products, setProducts] = useState<any[]>([])
  const [inventory, setInventory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  
  // Modal states
  const [showCategoryModal, setShowCategoryModal] = useState(false)
  const [showProductModal, setShowProductModal] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('')
  
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
      // Load categories
      const { data: cats } = await supabase
        .from('categories')
        .select('*')
        .eq('store_id', store_id)
        .order('name')
      
      setCategories(cats || [])

      // Load products with inventory
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
      
      // Force reload after a small delay
      setTimeout(() => {
        loadData(storeId)
      }, 500)
      
      alert('Category added successfully!')
    } catch (error) {
      console.error('Error adding category:', error)
      alert('Failed to add category')
    }
  }

  const handleAddProduct = async () => {
    if (!productForm.name.trim() || !productForm.category_id) {
      alert('Please fill required fields')
      return
    }

    try {
      // Create product
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

      // Create inventory entry
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

      // Reset form
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
    } catch (error) {
      console.error('Error adding product:', error)
      alert('Failed to add product')
    }
  }

  const updateQuantity = async (invId: string, newQuantity: number) => {
    try {
      const { error } = await supabase
        .from('inventory')
        .update({ quantity: newQuantity })
        .eq('id', invId)

      if (error) throw error
      loadData(storeId)
    } catch (error) {
      console.error('Error updating quantity:', error)
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
      <div className="max-w-7xl mx-auto">
        {/* Header */}
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Supplier</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {inventory.map((item) => {
                const isLowStock = parseFloat(item.quantity) <= parseFloat(item.reorder_threshold)
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
                        onChange={(e) => updateQuantity(item.id, parseFloat(e.target.value))}
                        className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
                      />
                      <span className="ml-1 text-sm text-gray-500">{item.products.unit}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      ₹{parseFloat(item.unit_price).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {item.products.supplier_name || '-'}
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
                className="w-full px-4 py-2 border border-gray-300 rounded-lg mb-4"
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
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Description</label>
                  <textarea
                    value={productForm.description}
                    onChange={(e) => setProductForm({...productForm, description: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                    rows={2}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Category *</label>
                  <select
                    value={productForm.category_id}
                    onChange={(e) => setProductForm({...productForm, category_id: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Selling Price *</label>
                  <input
                    type="number"
                    value={productForm.unit_price}
                    onChange={(e) => setProductForm({...productForm, unit_price: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Initial Quantity</label>
                  <input
                    type="number"
                    value={productForm.quantity}
                    onChange={(e) => setProductForm({...productForm, quantity: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Reorder Threshold</label>
                  <input
                    type="number"
                    value={productForm.reorder_threshold}
                    onChange={(e) => setProductForm({...productForm, reorder_threshold: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Reorder Quantity</label>
                  <input
                    type="number"
                    value={productForm.reorder_quantity}
                    onChange={(e) => setProductForm({...productForm, reorder_quantity: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div className="col-span-2">
                  <label className="block text-sm font-medium mb-1">Supplier Name</label>
                  <input
                    type="text"
                    value={productForm.supplier_name}
                    onChange={(e) => setProductForm({...productForm, supplier_name: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Supplier Phone</label>
                  <input
                    type="tel"
                    value={productForm.supplier_phone}
                    onChange={(e) => setProductForm({...productForm, supplier_phone: e.target.value})}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">Supplier WhatsApp</label>
                  <input
                    type="tel"
                    value={productForm.supplier_whatsapp}
                    onChange={(e) => setProductForm({...productForm, supplier_whatsapp: e.target.value})}
                    placeholder="919876543210"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg"
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
      </div>
    </div>
  )
}
