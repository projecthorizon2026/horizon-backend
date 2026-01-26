import { useState, useEffect } from 'react'
import {
  Search,
  TrendingUp,
  TrendingDown,
  Globe,
  Link,
  ExternalLink,
  RefreshCw,
  Plus,
  Edit2,
  Trash2,
  Eye,
  BarChart3,
  Target,
  AlertTriangle,
  CheckCircle,
  ArrowUp,
  ArrowDown,
  Minus,
  FileText,
  Settings,
  X,
  Copy,
  Zap,
  Award
} from 'lucide-react'
import { supabase } from '../lib/supabase'

const sampleKeywords = [
  { keyword: 'plus size bras india', volume: 12100, difficulty: 45, position: 3, change: 2, ctr: 8.5, impressions: 15600 },
  { keyword: 'dd+ bras online', volume: 8100, difficulty: 38, position: 5, change: -1, ctr: 5.2, impressions: 9800 },
  { keyword: 'full bust lingerie', volume: 6600, difficulty: 52, position: 8, change: 3, ctr: 3.1, impressions: 7200 },
  { keyword: 'plus size bra sizes', volume: 5400, difficulty: 35, position: 2, change: 0, ctr: 12.3, impressions: 6100 },
  { keyword: 'curvy lingerie india', volume: 4400, difficulty: 42, position: 6, change: 5, ctr: 4.8, impressions: 5200 },
  { keyword: 'best bras for large bust', volume: 9900, difficulty: 58, position: 12, change: -2, ctr: 1.8, impressions: 11200 },
  { keyword: 'supportive bras plus size', volume: 3300, difficulty: 41, position: 4, change: 1, ctr: 6.9, impressions: 4100 },
  { keyword: 'lingerie for curvy women', volume: 2900, difficulty: 48, position: 7, change: 0, ctr: 3.5, impressions: 3400 }
]

const seoIssues = [
  { type: 'warning', title: 'Missing meta descriptions', count: 3, pages: ['Product A', 'Category B', 'About Page'] },
  { type: 'error', title: 'Broken internal links', count: 2, pages: ['Blog post 1', 'FAQ Page'] },
  { type: 'warning', title: 'Images without alt text', count: 12, pages: ['Multiple product pages'] },
  { type: 'info', title: 'Pages with thin content', count: 4, pages: ['Size guide', 'Shipping info'] }
]

function AddKeywordModal({ onClose, onAdd }) {
  const [keyword, setKeyword] = useState('')
  const [targetUrl, setTargetUrl] = useState('')
  const [adding, setAdding] = useState(false)

  const handleAdd = async () => {
    if (!keyword.trim()) return
    setAdding(true)
    try {
      await onAdd({ keyword: keyword.trim(), targetUrl: targetUrl.trim() })
      onClose()
    } catch (err) {
      console.error('Error adding keyword:', err)
    } finally {
      setAdding(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Track New Keyword</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Keyword *</label>
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="e.g., plus size bras india"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Target URL (optional)</label>
            <input
              type="url"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="https://lumierecurves.shop/..."
            />
          </div>
        </div>

        <div className="px-6 py-4 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            Cancel
          </button>
          <button
            onClick={handleAdd}
            disabled={adding || !keyword.trim()}
            className="px-6 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50"
          >
            {adding ? 'Adding...' : 'Track Keyword'}
          </button>
        </div>
      </div>
    </div>
  )
}

function PageAnalysisModal({ onClose }) {
  const [url, setUrl] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [results, setResults] = useState(null)

  const handleAnalyze = async () => {
    if (!url.trim()) return
    setAnalyzing(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 2000))
      setResults({
        score: 78,
        title: { status: 'good', value: 'Premium Plus-Size Lingerie | Lumière Curves', length: 42 },
        description: { status: 'good', value: 'Shop India\'s finest DD+ bras and lingerie...', length: 145 },
        h1: { status: 'good', value: 'Plus-Size Lingerie for Every Curve' },
        wordCount: 850,
        images: { total: 12, withAlt: 10 },
        internalLinks: 8,
        externalLinks: 2,
        loadTime: '2.3s',
        mobile: 'Responsive',
        issues: [
          'Consider adding more internal links',
          'Some images could use more descriptive alt text'
        ]
      })
    } catch (err) {
      console.error('Error analyzing:', err)
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Page SEO Analysis</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto max-h-[70vh]">
          <div className="flex gap-3">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-rose-500"
              placeholder="https://lumierecurves.shop/..."
            />
            <button
              onClick={handleAnalyze}
              disabled={analyzing || !url.trim()}
              className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700 disabled:opacity-50 flex items-center gap-2"
            >
              {analyzing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Analyze
                </>
              )}
            </button>
          </div>

          {results && (
            <div className="space-y-6">
              {/* Score */}
              <div className="flex items-center gap-6 p-6 bg-gray-50 rounded-xl">
                <div className="relative w-24 h-24">
                  <svg className="w-full h-full -rotate-90">
                    <circle
                      cx="48" cy="48" r="40"
                      fill="none"
                      stroke="#e5e7eb"
                      strokeWidth="8"
                    />
                    <circle
                      cx="48" cy="48" r="40"
                      fill="none"
                      stroke={results.score >= 80 ? '#22c55e' : results.score >= 60 ? '#f59e0b' : '#ef4444'}
                      strokeWidth="8"
                      strokeDasharray={`${results.score * 2.51} 251`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold text-gray-900">{results.score}</span>
                  </div>
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 text-lg">SEO Score</h3>
                  <p className="text-gray-500 text-sm">
                    {results.score >= 80 ? 'Excellent! Your page is well optimized.' :
                     results.score >= 60 ? 'Good, but there\'s room for improvement.' :
                     'Needs work. Check the issues below.'}
                  </p>
                </div>
              </div>

              {/* Details */}
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">Title Tag</span>
                  </div>
                  <span className="text-sm text-gray-500">{results.title.length} characters</span>
                </div>
                <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">Meta Description</span>
                  </div>
                  <span className="text-sm text-gray-500">{results.description.length} characters</span>
                </div>
                <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">H1 Tag</span>
                  </div>
                  <span className="text-sm text-gray-500">Present</span>
                </div>
                <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">Word Count</span>
                  </div>
                  <span className="text-sm text-gray-500">{results.wordCount} words</span>
                </div>
                <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    {results.images.withAlt === results.images.total ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : (
                      <AlertTriangle className="w-5 h-5 text-yellow-500" />
                    )}
                    <span className="text-gray-700">Images with Alt</span>
                  </div>
                  <span className="text-sm text-gray-500">{results.images.withAlt}/{results.images.total}</span>
                </div>
                <div className="flex items-center justify-between p-3 border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <CheckCircle className="w-5 h-5 text-green-500" />
                    <span className="text-gray-700">Mobile Friendly</span>
                  </div>
                  <span className="text-sm text-gray-500">{results.mobile}</span>
                </div>
              </div>

              {/* Suggestions */}
              {results.issues.length > 0 && (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <h4 className="font-medium text-yellow-800 mb-2">Suggestions</h4>
                  <ul className="space-y-1 text-sm text-yellow-700">
                    {results.issues.map((issue, i) => (
                      <li key={i}>• {issue}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function SEO() {
  const [keywords, setKeywords] = useState(sampleKeywords)
  const [loading, setLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showAnalysisModal, setShowAnalysisModal] = useState(false)
  const [activeTab, setActiveTab] = useState('keywords')
  const [sortBy, setSortBy] = useState('volume')
  const [sortOrder, setSortOrder] = useState('desc')

  useEffect(() => {
    loadKeywords()
  }, [])

  const loadKeywords = async () => {
    setLoading(true)
    try {
      const { data } = await supabase
        .from('seo_keywords')
        .select('*')
        .order('search_volume', { ascending: false })
      if (data?.length > 0) {
        setKeywords(data.map(k => ({
          keyword: k.keyword,
          volume: k.search_volume,
          difficulty: k.difficulty,
          position: k.current_position,
          change: (k.previous_position || k.current_position) - k.current_position,
          ctr: k.ctr,
          impressions: k.impressions_last_30d
        })))
      }
    } catch (err) {
      console.error('Error loading keywords:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleAddKeyword = async (data) => {
    try {
      await supabase.from('seo_keywords').insert({
        keyword: data.keyword,
        target_url: data.targetUrl,
        search_volume: 0,
        difficulty: 0,
        current_position: 0,
        source: 'manual'
      })
      loadKeywords()
    } catch (err) {
      // Add to local state for demo
      setKeywords([...keywords, {
        keyword: data.keyword,
        volume: 0,
        difficulty: 0,
        position: 0,
        change: 0,
        ctr: 0,
        impressions: 0
      }])
    }
  }

  const handleDelete = async (keyword) => {
    if (!confirm(`Remove "${keyword}" from tracking?`)) return
    try {
      await supabase.from('seo_keywords').delete().eq('keyword', keyword)
      setKeywords(keywords.filter(k => k.keyword !== keyword))
    } catch (err) {
      setKeywords(keywords.filter(k => k.keyword !== keyword))
    }
  }

  const sortedKeywords = [...keywords].sort((a, b) => {
    const aVal = a[sortBy] || 0
    const bVal = b[sortBy] || 0
    return sortOrder === 'desc' ? bVal - aVal : aVal - bVal
  })

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }

  // Calculate totals
  const totalImpressions = keywords.reduce((sum, k) => sum + k.impressions, 0)
  const avgPosition = keywords.length > 0
    ? (keywords.reduce((sum, k) => sum + k.position, 0) / keywords.length).toFixed(1)
    : 0
  const keywordsInTop10 = keywords.filter(k => k.position > 0 && k.position <= 10).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SEO & Keywords</h1>
          <p className="text-gray-500 mt-1">Track rankings, analyze pages, and optimize for search</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setShowAnalysisModal(true)}
            className="flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
          >
            <FileText className="w-4 h-4" />
            Page Analysis
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center justify-center gap-2 px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700"
          >
            <Plus className="w-4 h-4" />
            Track Keyword
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{keywords.length}</p>
              <p className="text-xs text-gray-500">Tracked Keywords</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              <Award className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{keywordsInTop10}</p>
              <p className="text-xs text-gray-500">In Top 10</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <Target className="w-5 h-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{avgPosition}</p>
              <p className="text-xs text-gray-500">Avg Position</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-rose-100 rounded-lg flex items-center justify-center">
              <Eye className="w-5 h-5 text-rose-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{(totalImpressions / 1000).toFixed(1)}K</p>
              <p className="text-xs text-gray-500">Impressions (30d)</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-gray-200">
        {['keywords', 'issues', 'competitors'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors capitalize ${
              activeTab === tab
                ? 'border-rose-500 text-rose-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'keywords' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Keyword</th>
                  <th
                    className="text-right px-4 py-3 text-sm font-medium text-gray-500 cursor-pointer hover:text-gray-700"
                    onClick={() => handleSort('volume')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Volume
                      {sortBy === 'volume' && (sortOrder === 'desc' ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />)}
                    </div>
                  </th>
                  <th
                    className="text-right px-4 py-3 text-sm font-medium text-gray-500 cursor-pointer hover:text-gray-700"
                    onClick={() => handleSort('difficulty')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Difficulty
                      {sortBy === 'difficulty' && (sortOrder === 'desc' ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />)}
                    </div>
                  </th>
                  <th
                    className="text-right px-4 py-3 text-sm font-medium text-gray-500 cursor-pointer hover:text-gray-700"
                    onClick={() => handleSort('position')}
                  >
                    <div className="flex items-center justify-end gap-1">
                      Position
                      {sortBy === 'position' && (sortOrder === 'desc' ? <ArrowDown className="w-3 h-3" /> : <ArrowUp className="w-3 h-3" />)}
                    </div>
                  </th>
                  <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">Change</th>
                  <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">CTR</th>
                  <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">Impressions</th>
                  <th className="w-20"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sortedKeywords.map((kw, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Search className="w-4 h-4 text-gray-400" />
                        <span className="font-medium text-gray-900">{kw.keyword}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {kw.volume?.toLocaleString() || '-'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        kw.difficulty < 40 ? 'bg-green-100 text-green-700' :
                        kw.difficulty < 60 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        {kw.difficulty || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-semibold ${
                        kw.position <= 3 ? 'text-green-600' :
                        kw.position <= 10 ? 'text-blue-600' :
                        'text-gray-600'
                      }`}>
                        {kw.position || '-'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {kw.change !== 0 ? (
                        <span className={`flex items-center justify-end gap-1 ${
                          kw.change > 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {kw.change > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                          {Math.abs(kw.change)}
                        </span>
                      ) : (
                        <span className="flex items-center justify-end text-gray-400">
                          <Minus className="w-4 h-4" />
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {kw.ctr ? `${kw.ctr}%` : '-'}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">
                      {kw.impressions?.toLocaleString() || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(kw.keyword)}
                        className="p-1 text-gray-400 hover:text-red-600 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'issues' && (
        <div className="space-y-4">
          {seoIssues.map((issue, i) => (
            <div
              key={i}
              className={`bg-white rounded-xl border shadow-sm p-4 ${
                issue.type === 'error' ? 'border-red-200' :
                issue.type === 'warning' ? 'border-yellow-200' :
                'border-gray-200'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  issue.type === 'error' ? 'bg-red-100' :
                  issue.type === 'warning' ? 'bg-yellow-100' :
                  'bg-blue-100'
                }`}>
                  <AlertTriangle className={`w-5 h-5 ${
                    issue.type === 'error' ? 'text-red-600' :
                    issue.type === 'warning' ? 'text-yellow-600' :
                    'text-blue-600'
                  }`} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium text-gray-900">{issue.title}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      issue.type === 'error' ? 'bg-red-100 text-red-700' :
                      issue.type === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-blue-100 text-blue-700'
                    }`}>
                      {issue.count} {issue.count === 1 ? 'page' : 'pages'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    Affected: {issue.pages.join(', ')}
                  </p>
                </div>
                <button className="px-3 py-1.5 text-sm text-rose-600 hover:bg-rose-50 rounded-lg">
                  Fix Now
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'competitors' && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
          <Globe className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">Competitor Analysis</h3>
          <p className="text-gray-500 mb-4">Track and compare your rankings against competitors</p>
          <button className="px-4 py-2 bg-rose-600 text-white rounded-lg hover:bg-rose-700">
            Add Competitor
          </button>
        </div>
      )}

      {/* Quick Tips */}
      <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-xl p-6 text-white">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
            <Zap className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-lg">SEO Quick Tips</h3>
            <ul className="text-white/80 text-sm mt-2 space-y-1">
              <li>• Focus on long-tail keywords like "plus size bra for wedding" for higher conversions</li>
              <li>• Add unique product descriptions to avoid duplicate content</li>
              <li>• Use schema markup for products to get rich snippets in search results</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showAddModal && (
        <AddKeywordModal
          onClose={() => setShowAddModal(false)}
          onAdd={handleAddKeyword}
        />
      )}

      {showAnalysisModal && (
        <PageAnalysisModal onClose={() => setShowAnalysisModal(false)} />
      )}
    </div>
  )
}
