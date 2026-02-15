'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@supabase/supabase-js'
import { Save, Eye } from 'lucide-react'

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || '',
  process.env.NEXT_PUBLIC_SUPABASE_KEY || ''
)

export default function Settings() {
  const [storeId, setStoreId] = useState<string>('')
  const [storeData, setStoreData] = useState<any>(null)
  const [template, setTemplate] = useState('')
  const [preview, setPreview] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const AVAILABLE_VARIABLES = [
    { var: '{{shop_name}}', desc: 'Your shop name' },
    { var: '{{shop_phone}}', desc: 'Shop phone number' },
    { var: '{{shop_address}}', desc: 'Shop address' },
    { var: '{{customer_name}}', desc: 'Customer name' },
    { var: '{{customer_phone}}', desc: 'Customer phone' }
  ]

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
      // Load store data
      const { data: store } = await supabase
        .from('stores')
        .select('*')
        .eq('id', store_id)
        .single()
      
      setStoreData(store)

      // Load template
      const { data: templateData } = await supabase
        .from('customer_welcome_templates')
        .select('*')
        .eq('store_id', store_id)
        .single()
      
      if (templateData) {
        setTemplate(templateData.template_text)
        generatePreview(templateData.template_text, store)
      } else {
        // Default template
        const defaultTemplate = `Welcome to {{shop_name}}! 🎉

We're glad to have you here!

📱 Contact: {{shop_phone}}
📍 Address: {{shop_address}}

Feel free to browse and order anytime!`
        setTemplate(defaultTemplate)
        generatePreview(defaultTemplate, store)
      }
    } catch (error) {
      console.error('Error loading data:', error)
    } finally {
      setLoading(false)
    }
  }

  const generatePreview = (text: string, store: any) => {
    if (!store) return

    let previewText = text
      .replace(/\{\{shop_name\}\}/g, store.name || '[Shop Name]')
      .replace(/\{\{shop_phone\}\}/g, store.phone || '[Phone]')
      .replace(/\{\{shop_address\}\}/g, store.address || '[Address]')
      .replace(/\{\{customer_name\}\}/g, 'John Doe')
      .replace(/\{\{customer_phone\}\}/g, '+919876543210')
    
    setPreview(previewText)
  }

  const handleTemplateChange = (text: string) => {
    setTemplate(text)
    generatePreview(text, storeData)
  }

  const insertVariable = (variable: string) => {
    setTemplate(template + ' ' + variable)
    generatePreview(template + ' ' + variable, storeData)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // Check if template exists
      const { data: existing } = await supabase
        .from('customer_welcome_templates')
        .select('id')
        .eq('store_id', storeId)
        .single()

      if (existing) {
        // Update
        await supabase
          .from('customer_welcome_templates')
          .update({
            template_text: template,
            updated_at: new Date().toISOString()
          })
          .eq('store_id', storeId)
      } else {
        // Insert
        await supabase
          .from('customer_welcome_templates')
          .insert({
            store_id: storeId,
            template_text: template
          })
      }

      alert('✅ Template saved successfully!')
    } catch (error) {
      console.error('Error saving template:', error)
      alert('❌ Failed to save template')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading settings...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Settings</h1>
          <p className="text-gray-600">Customize your customer welcome message</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Editor */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-bold mb-4">Welcome Message Template</h2>
            
            {/* Available Variables */}
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Available Variables:</p>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_VARIABLES.map((v) => (
                  <button
                    key={v.var}
                    onClick={() => insertVariable(v.var)}
                    className="px-3 py-1 bg-blue-100 text-blue-700 rounded text-sm hover:bg-blue-200"
                    title={v.desc}
                  >
                    {v.var}
                  </button>
                ))}
              </div>
            </div>

            {/* Template Editor */}
            <textarea
              value={template}
              onChange={(e) => handleTemplateChange(e.target.value)}
              className="w-full h-64 px-4 py-3 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter your welcome message..."
            />

            <div className="mt-4 flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg flex items-center justify-center gap-2 disabled:bg-gray-400"
              >
                <Save size={20} />
                {saving ? 'Saving...' : 'Save Template'}
              </button>
            </div>
          </div>

          {/* Preview */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center gap-2 mb-4">
              <Eye size={20} className="text-gray-600" />
              <h2 className="text-xl font-bold">Preview</h2>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="bg-white rounded-lg p-4 shadow-sm">
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
                    B
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">BazaarOps Admin</p>
                    <p className="text-xs text-gray-500">Just now</p>
                  </div>
                </div>
                <div className="whitespace-pre-wrap text-gray-800 text-sm">
                  {preview}
                </div>
              </div>
            </div>

            <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <p className="text-sm text-blue-900 font-medium mb-2">💡 Tips:</p>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Use variables to personalize messages</li>
                <li>• Keep it short and friendly</li>
                <li>• Add emojis for better engagement</li>
                <li>• Include contact info and address</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
