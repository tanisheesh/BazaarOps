'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  TrendingUp, TrendingDown, AlertTriangle, BarChart2,
  DollarSign, Users, Package, RefreshCw
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'

interface TrendData {
  this_week_revenue: number
  last_week_revenue: number
  change_percentage: number
  trend: string
  top_products: { name: string; revenue: number }[]
  bottom_products: { name: string; revenue: number }[]
  insights: string[]
}

interface ForecastData {
  revenue_forecast: {
    next_7_days_total: number
    confidence: string
    daily_forecast: { day: number; date: string; predicted_revenue: number }[]
  }
  stockout_predictions: {
    product_name: string
    days_until_stockout: number
    risk: string
    current_stock: number
  }[]
  churn_forecast: {
    predicted_churn_30d: number
    high_risk_count: number
    medium_risk_count: number
    predicted_churn_rate_pct: number
  }
}

interface AnomalyData {
  anomalies: { type: string; severity: string; message: string }[]
  count: number
}

interface ProfitabilityData {
  product_profitability: { name: string; revenue: number; profit: number; margin_pct: number }[]
  low_margin_products: { name: string; margin_pct: number }[]
  recommendations: string[]
}

function MetricCard({
  title, value, subtitle, icon: Icon, color
}: {
  title: string; value: string; subtitle?: string; icon: any; color: string
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <div className={`p-2 rounded-lg ${color}`}>
          <Icon size={20} className="text-white" />
        </div>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {subtitle && <p className="text-sm text-gray-500 mt-1">{subtitle}</p>}
    </div>
  )
}

function SimpleBarChart({ data }: { data: { label: string; value: number }[] }) {
  const max = Math.max(...data.map(d => d.value), 1)
  return (
    <div className="space-y-2">
      {data.map((item, i) => (
        <div key={i} className="flex items-center gap-3">
          <span className="text-xs text-gray-500 w-20 truncate">{item.label}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${(item.value / max) * 100}%` }}
            />
          </div>
          <span className="text-xs font-medium text-gray-700 w-16 text-right">
            ₹{item.value.toLocaleString('en-IN')}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const [storeId, setStoreId] = useState<string>('')
  const [trends, setTrends] = useState<TrendData | null>(null)
  const [forecast, setForecast] = useState<ForecastData | null>(null)
  const [anomalies, setAnomalies] = useState<AnomalyData | null>(null)
  const [profitability, setProfitability] = useState<ProfitabilityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  useEffect(() => {
    const id = localStorage.getItem('store_id')
    if (id) {
      setStoreId(id)
      loadAll(id)
    } else {
      setLoading(false)
    }
  }, [])

  const loadAll = async (id: string) => {
    setLoading(true)
    try {
      const [trendsRes, forecastRes, anomaliesRes, profitRes] = await Promise.allSettled([
        fetch(`${API_URL}/api/owner/analytics/trends/${id}`).then(r => r.json()),
        fetch(`${API_URL}/api/owner/analytics/forecast/${id}`).then(r => r.json()),
        fetch(`${API_URL}/api/owner/analytics/anomalies/${id}`).then(r => r.json()),
        fetch(`${API_URL}/api/owner/analytics/profitability/${id}`).then(r => r.json()),
      ])

      if (trendsRes.status === 'fulfilled') setTrends(trendsRes.value)
      if (forecastRes.status === 'fulfilled') setForecast(forecastRes.value)
      if (anomaliesRes.status === 'fulfilled') setAnomalies(anomaliesRes.value)
      if (profitRes.status === 'fulfilled') setProfitability(profitRes.value)
      setLastUpdated(new Date())
    } catch (e) {
      console.error('Failed to load analytics:', e)
    } finally {
      setLoading(false)
    }
  }

  if (!storeId) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">Please log in to view your dashboard.</p>
          <Link href="/login" className="text-blue-600 hover:underline">Go to Login</Link>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">Loading analytics...</p>
        </div>
      </div>
    )
  }

  const trendUp = (trends?.change_percentage ?? 0) >= 0
  const criticalAnomalies = anomalies?.anomalies.filter(a => a.severity === 'high' || a.severity === 'critical') ?? []

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">📊 Business Intelligence</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : 'Loading...'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => loadAll(storeId)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
            <Link href="/" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              ← Back
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* 6.6.4 Real-time metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            title="This Week Revenue"
            value={`₹${(trends?.this_week_revenue ?? 0).toLocaleString('en-IN')}`}
            subtitle={`${trendUp ? '+' : ''}${(trends?.change_percentage ?? 0).toFixed(1)}% vs last week`}
            icon={trendUp ? TrendingUp : TrendingDown}
            color={trendUp ? 'bg-green-500' : 'bg-red-500'}
          />
          <MetricCard
            title="7-Day Forecast"
            value={`₹${(forecast?.revenue_forecast.next_7_days_total ?? 0).toLocaleString('en-IN')}`}
            subtitle={`${forecast?.revenue_forecast.confidence ?? '—'} confidence`}
            icon={BarChart2}
            color="bg-blue-500"
          />
          <MetricCard
            title="Churn Risk"
            value={`${forecast?.churn_forecast.predicted_churn_30d ?? 0} customers`}
            subtitle={`${forecast?.churn_forecast.high_risk_count ?? 0} high risk`}
            icon={Users}
            color="bg-orange-500"
          />
          <MetricCard
            title="Anomalies"
            value={`${criticalAnomalies.length}`}
            subtitle={criticalAnomalies.length > 0 ? 'Needs attention' : 'All clear'}
            icon={AlertTriangle}
            color={criticalAnomalies.length > 0 ? 'bg-red-500' : 'bg-green-500'}
          />
        </div>

        {/* Anomaly alerts */}
        {criticalAnomalies.length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <h2 className="font-semibold text-red-900 flex items-center gap-2 mb-3">
              <AlertTriangle size={18} /> Anomalies Detected
            </h2>
            <ul className="space-y-1">
              {criticalAnomalies.map((a, i) => (
                <li key={i} className="text-sm text-red-800">• {a.message}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 6.6.1 Trend charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingUp size={18} className="text-blue-600" /> Top Products This Week
            </h2>
            {trends?.top_products && trends.top_products.length > 0 ? (
              <SimpleBarChart
                data={trends.top_products.map(p => ({ label: p.name, value: p.revenue }))}
              />
            ) : (
              <p className="text-sm text-gray-400">No data available</p>
            )}
          </div>

          {/* 6.6.3 Forecast visualizations */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart2 size={18} className="text-blue-600" /> 7-Day Revenue Forecast
            </h2>
            {forecast?.revenue_forecast.daily_forecast && forecast.revenue_forecast.daily_forecast.length > 0 ? (
              <SimpleBarChart
                data={forecast.revenue_forecast.daily_forecast.map(d => ({
                  label: d.date.slice(5),
                  value: d.predicted_revenue,
                }))}
              />
            ) : (
              <p className="text-sm text-gray-400">No forecast data</p>
            )}
          </div>
        </div>

        {/* 6.6.2 Profitability breakdown */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
          <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <DollarSign size={18} className="text-green-600" /> Profitability Breakdown
          </h2>
          {profitability?.product_profitability && profitability.product_profitability.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100">
                    <th className="text-left py-2 text-gray-500 font-medium">Product</th>
                    <th className="text-right py-2 text-gray-500 font-medium">Revenue</th>
                    <th className="text-right py-2 text-gray-500 font-medium">Profit</th>
                    <th className="text-right py-2 text-gray-500 font-medium">Margin</th>
                  </tr>
                </thead>
                <tbody>
                  {profitability.product_profitability.slice(0, 8).map((p, i) => (
                    <tr key={i} className="border-b border-gray-50">
                      <td className="py-2 text-gray-900">{p.name}</td>
                      <td className="py-2 text-right text-gray-700">₹{p.revenue.toLocaleString('en-IN')}</td>
                      <td className="py-2 text-right text-gray-700">₹{p.profit.toLocaleString('en-IN')}</td>
                      <td className={`py-2 text-right font-medium ${p.margin_pct < 10 ? 'text-red-600' : 'text-green-600'}`}>
                        {p.margin_pct.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No profitability data available</p>
          )}

          {profitability?.recommendations && profitability.recommendations.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-sm font-medium text-gray-700 mb-2">Recommendations:</p>
              <ul className="space-y-1">
                {profitability.recommendations.map((r, i) => (
                  <li key={i} className="text-sm text-gray-600">• {r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Stockout predictions */}
        {forecast?.stockout_predictions && forecast.stockout_predictions.filter(s => s.risk !== 'low').length > 0 && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
            <h2 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Package size={18} className="text-orange-600" /> Stockout Predictions
            </h2>
            <div className="space-y-2">
              {forecast.stockout_predictions
                .filter(s => s.risk !== 'low')
                .slice(0, 6)
                .map((s, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-gray-50">
                    <span className="text-sm text-gray-900">{s.product_name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-500">{s.days_until_stockout.toFixed(0)} days left</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        s.risk === 'critical' ? 'bg-red-100 text-red-700' :
                        s.risk === 'high' ? 'bg-orange-100 text-orange-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}>
                        {s.risk}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Trend insights */}
        {trends?.insights && trends.insights.length > 0 && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
            <h2 className="font-semibold text-blue-900 mb-3">💡 AI Insights</h2>
            <ul className="space-y-1">
              {trends.insights.map((insight, i) => (
                <li key={i} className="text-sm text-blue-800">• {insight}</li>
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  )
}
