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
  const [promoMessage, setPromoMessage] = useState('')
  const [sendingPromo, setSendingPromo] = useState(false)
  const [promoStatus, setPromoStatus] = useState('')

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

  const sendPromoMessage = async () => {
    if (!promoMessage.trim()) {
      alert('Please enter a message')
      return
    }

    setSendingPromo(true)
    setPromoStatus('')

    try {
      // Get all customers with telegram_chat_id
      const { data: customers, error } = await supabase
        .from('customers')
        .select('telegram_chat_id, name, phone')
        .eq('store_id', storeId)
        .not('telegram_chat_id', 'is', null)

      if (error) throw error

      if (!customers || customers.length === 0) {
        setPromoStatus('⚠️ No customers found with Telegram accounts')
        setSendingPromo(false)
        return
      }

      // Send message via backend API
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/owner/send-promo`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          store_id: storeId,
          message: promoMessage,
          customer_ids: customers.map(c => c.telegram_chat_id)
        })
      })

      const result = await response.json()

      if (result.success) {
        setPromoStatus(`✅ Message sent to ${customers.length} customers!`)
        setPromoMessage('')
      } else {
        setPromoStatus(`❌ Failed to send messages: ${result.message}`)
      }
    } catch (error) {
      console.error('Error sending promo:', error)
      setPromoStatus('❌ Error sending promotional message')
    } finally {
      setSendingPromo(false)
    }
  }

  const usePromoTemplate = () => {
    const template = `🎉 *Special Offer!* 🎉

Get *20% OFF* on all products today!

🛒 Order now: https://t.me/BazaarOpsCustomerHelpBot?start=${storeId}

📱 Contact: ${storeData?.phone || 'Your Phone'}
📍 ${storeData?.name || 'Your Store'}

_Hurry! Limited time offer!_`
    setPromoMessage(template)
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
          <h1 className="text-3xl font-bold text-gray-900 mb-2">⚙️ Settings</h1>
          <p className="text-gray-600">Manage your bots, templates, and store settings</p>
        </div>

        {/* Owner Bot Connection */}
        <div className="bg-gradient-to-r from-green-500 to-teal-600 rounded-lg shadow-lg p-6 mb-6 text-white">
          <h2 className="text-2xl font-bold mb-2">🤖 Owner Bot - AI Insights & Alerts</h2>
          <p className="mb-4 opacity-90">Connect to receive daily AI reports, inventory alerts, and business insights via Telegram!</p>
          
          <div className="bg-white/20 backdrop-blur rounded-lg p-4 mb-4">
            <p className="text-sm font-medium mb-2">What you'll get:</p>
            <ul className="text-sm space-y-1 opacity-90">
              <li>• 📊 Daily AI-powered business reports (9 PM)</li>
              <li>• 📦 Smart inventory alerts (10 AM, 4 PM)</li>
              <li>• 💳 Credit risk analysis (9:05 PM)</li>
              <li>• 🔔 Real-time order notifications</li>
            </ul>
          </div>
          
          <a
            href="https://t.me/BazaarOpsAdminBot"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block px-8 py-3 bg-white text-green-600 rounded-lg font-semibold hover:bg-green-50 transition-colors shadow-lg"
          >
            📱 Open Owner Bot & Send /start
          </a>
        </div>

        {/* Customer Bot Link */}
        <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg p-6 mb-6 text-white">
          <h2 className="text-2xl font-bold mb-2">📱 Customer Shopping Bot</h2>
          <p className="mb-4 opacity-90">Share this link with your customers to let them shop via Telegram!</p>
          
          <div className="bg-white/20 backdrop-blur rounded-lg p-4">
            <p className="text-sm mb-2 font-medium">Your Customer Bot Link:</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={`https://t.me/BazaarOpsCustomerHelpBot?start=${storeId}`}
                readOnly
                className="flex-1 px-4 py-2 bg-white/90 text-gray-900 rounded-lg font-mono text-sm"
              />
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`https://t.me/BazaarOpsCustomerHelpBot?start=${storeId}`)
                  alert('✅ Link copied to clipboard!')
                }}
                className="px-6 py-2 bg-white text-blue-600 rounded-lg font-semibold hover:bg-blue-50"
              >
                Copy Link
              </button>
            </div>
            <p className="text-xs mt-2 opacity-75">
              💡 Customers click this link → Bot opens → They can browse & order from your store!
            </p>
          </div>
        </div>

        {/* Promotional Message Sender */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <h2 className="text-2xl font-bold mb-4 text-gray-900">📢 Send Promotional Message</h2>
          <p className="text-gray-600 mb-4">Send promotional messages to all your customers via Telegram</p>
          
          <div className="space-y-4">
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm font-medium text-gray-700">
                  Message
                </label>
                <button
                  onClick={usePromoTemplate}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  📝 Use Template
                </button>
              </div>
              <textarea
                value={promoMessage}
                onChange={(e) => setPromoMessage(e.target.value)}
                placeholder="Enter your promotional message here..."
                className="w-full h-40 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              
              {/* Formatting Instructions */}
              <div className="mt-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <p className="text-xs font-semibold text-blue-900 mb-2">💡 Formatting Tips:</p>
                <div className="grid grid-cols-2 gap-2 text-xs text-blue-800">
                  <div>• <code className="bg-blue-100 px-1 rounded">*bold text*</code> → <strong>bold text</strong></div>
                  <div>• <code className="bg-blue-100 px-1 rounded">_italic text_</code> → <em>italic text</em></div>
                  <div>• <code className="bg-blue-100 px-1 rounded">`code text`</code> → <code>code text</code></div>
                  <div>• Use emojis: 🎉 🛒 📱 ✨ 💰</div>
                </div>
              </div>
            </div>
            
            <button
              onClick={sendPromoMessage}
              disabled={sendingPromo || !promoMessage.trim()}
              className="w-full bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-semibold disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {sendingPromo ? 'Sending...' : '📤 Send to All Customers'}
            </button>
            
            {promoStatus && (
              <div className={`p-4 rounded-lg ${promoStatus.includes('✅') ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
                {promoStatus}
              </div>
            )}
          </div>
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
