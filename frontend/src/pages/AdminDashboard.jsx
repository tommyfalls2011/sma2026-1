import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

const API = import.meta.env.REACT_APP_BACKEND_URL || ''

export default function AdminDashboard() {
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const [products, setProducts] = useState([])
  const [members, setMembers] = useState([])
  const [tab, setTab] = useState('products')
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ name: '', price: '', short_desc: '', description: '', image_url: '', gallery: [], in_stock: true, specs: '' })
  const [galleryInput, setGalleryInput] = useState('')

  useEffect(() => {
    if (!user?.is_admin) { navigate('/'); return }
    loadData()
  }, [user])

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const loadData = () => {
    fetch(`${API}/api/store/products`).then(r => r.json()).then(setProducts)
    fetch(`${API}/api/store/admin/members`, { headers }).then(r => r.json()).then(setMembers).catch(() => {})
  }

  const saveProduct = async () => {
    const body = { ...form, price: parseFloat(form.price), specs: form.specs.split('\n').filter(Boolean) }
    const url = editing ? `${API}/api/store/admin/products/${editing}` : `${API}/api/store/admin/products`
    const method = editing ? 'PUT' : 'POST'
    await fetch(url, { method, headers, body: JSON.stringify(body) })
    setEditing(null)
    setForm({ name: '', price: '', short_desc: '', description: '', image_url: '', in_stock: true, specs: '' })
    loadData()
  }

  const deleteProduct = async (id) => {
    if (!confirm('Delete this product?')) return
    await fetch(`${API}/api/store/admin/products/${id}`, { method: 'DELETE', headers })
    loadData()
  }

  const editProduct = (p) => {
    setEditing(p.id)
    setForm({ name: p.name, price: p.price.toString(), short_desc: p.short_desc || '', description: p.description || '', image_url: p.image_url || '', in_stock: p.in_stock, specs: (p.specs || []).join('\n') })
    setTab('products')
  }

  if (!user?.is_admin) return null

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="font-display text-3xl font-bold text-white mb-8" data-testid="admin-title">Admin Dashboard</h1>

      <div className="flex gap-4 mb-8">
        {['products', 'members'].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`font-display uppercase tracking-wider text-sm px-6 py-2 rounded-sm transition-colors ${tab === t ? 'bg-brand-500 text-dark-950' : 'bg-dark-800 text-dark-400 hover:text-white'}`} data-testid={`tab-${t}`}>
            {t} ({t === 'products' ? products.length : members.length})
          </button>
        ))}
      </div>

      {tab === 'products' && (
        <div className="space-y-6">
          {/* Product Form */}
          <div className="bg-dark-900 border border-dark-800 rounded-sm p-6">
            <h2 className="font-display text-lg font-semibold text-white mb-4">{editing ? 'Edit Product' : 'Add Product'}</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <input placeholder="Product Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="product-form-name" />
              <input placeholder="Price" type="number" value={form.price} onChange={e => setForm(f => ({ ...f, price: e.target.value }))} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="product-form-price" />
              <input placeholder="Short Description" value={form.short_desc} onChange={e => setForm(f => ({ ...f, short_desc: e.target.value }))} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500 sm:col-span-2" data-testid="product-form-short-desc" />
              <input placeholder="Image URL" value={form.image_url} onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500 sm:col-span-2" data-testid="product-form-image" />
              <textarea placeholder="Full Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500 sm:col-span-2" data-testid="product-form-desc" />
              <textarea placeholder="Specs (one per line)" value={form.specs} onChange={e => setForm(f => ({ ...f, specs: e.target.value }))} rows={3} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500 sm:col-span-2" data-testid="product-form-specs" />
              <label className="flex items-center gap-2 text-dark-400">
                <input type="checkbox" checked={form.in_stock} onChange={e => setForm(f => ({ ...f, in_stock: e.target.checked }))} className="accent-brand-500" />
                In Stock
              </label>
            </div>
            <div className="mt-4 flex gap-3">
              <button onClick={saveProduct} className="font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-6 py-3 rounded-sm hover:bg-brand-400 transition-colors font-semibold" data-testid="product-form-save">{editing ? 'Update' : 'Add Product'}</button>
              {editing && <button onClick={() => { setEditing(null); setForm({ name: '', price: '', short_desc: '', description: '', image_url: '', in_stock: true, specs: '' }) }} className="text-sm text-dark-400 hover:text-white px-4">Cancel</button>}
            </div>
          </div>

          {/* Product List */}
          <div className="space-y-3">
            {products.map(p => (
              <div key={p.id} className="bg-dark-900 border border-dark-800 rounded-sm p-4 flex items-center gap-4">
                <img src={p.image_url || 'https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=100'} alt={p.name} className="w-16 h-16 object-cover rounded-sm" />
                <div className="flex-1">
                  <h3 className="font-display font-semibold text-white">{p.name}</h3>
                  <p className="text-sm text-dark-400">${p.price} - {p.in_stock ? 'In Stock' : 'Sold Out'}</p>
                </div>
                <button onClick={() => editProduct(p)} className="text-sm text-brand-400 hover:text-brand-300">Edit</button>
                <button onClick={() => deleteProduct(p.id)} className="text-sm text-red-400 hover:text-red-300">Delete</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'members' && (
        <div className="bg-dark-900 border border-dark-800 rounded-sm overflow-hidden">
          <table className="w-full">
            <thead><tr className="border-b border-dark-700">
              <th className="text-left p-4 text-xs text-dark-400 uppercase font-display">Name</th>
              <th className="text-left p-4 text-xs text-dark-400 uppercase font-display">Email</th>
              <th className="text-left p-4 text-xs text-dark-400 uppercase font-display">Joined</th>
            </tr></thead>
            <tbody>
              {members.map(m => (
                <tr key={m.id} className="border-b border-dark-800">
                  <td className="p-4 text-sm text-white">{m.name}</td>
                  <td className="p-4 text-sm text-dark-400">{m.email}</td>
                  <td className="p-4 text-sm text-dark-500">{new Date(m.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
