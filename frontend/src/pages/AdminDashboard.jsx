import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'

const API = import.meta.env.REACT_APP_BACKEND_URL || ''

export default function AdminDashboard() {
  const { user, token } = useAuth()
  const navigate = useNavigate()
  const [products, setProducts] = useState([])
  const [members, setMembers] = useState([])
  const [orders, setOrders] = useState([])
  const [tab, setTab] = useState('products')
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ name: '', price: '', short_desc: '', description: '', image_url: '', gallery: [], in_stock: true, specs: '' })
  const [galleryInput, setGalleryInput] = useState('')
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    if (!user?.is_admin) { navigate('/'); return }
    loadData()
  }, [user])

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const loadData = () => {
    fetch(`${API}/api/store/products`).then(r => r.json()).then(setProducts)
    fetch(`${API}/api/store/admin/members`, { headers }).then(r => r.json()).then(setMembers).catch(() => {})
    fetch(`${API}/api/store/admin/orders`, { headers }).then(r => r.json()).then(setOrders).catch(() => {})
  }

  const uploadImage = async (target) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/jpeg,image/png,image/webp,image/gif'
    input.onchange = async (e) => {
      const file = e.target.files[0]
      if (!file) return
      if (file.size > 10 * 1024 * 1024) { alert('File too large. Max 10 MB.'); return }
      setUploading(true)
      const fd = new FormData()
      fd.append('file', file)
      try {
        const res = await fetch(`${API}/api/store/admin/upload`, { method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: fd })
        const data = await res.json()
        if (res.ok && data.url) {
          if (target === 'main') {
            setForm(f => ({ ...f, image_url: data.url }))
          } else {
            setForm(f => ({ ...f, gallery: [...f.gallery, data.url] }))
          }
        } else {
          alert(data.detail || 'Upload failed')
        }
      } catch { alert('Upload failed') }
      setUploading(false)
    }
    input.click()
  }

  const saveProduct = async () => {
    const body = { ...form, price: parseFloat(form.price), specs: form.specs.split('\n').filter(Boolean), gallery: form.gallery }
    const url = editing ? `${API}/api/store/admin/products/${editing}` : `${API}/api/store/admin/products`
    const method = editing ? 'PUT' : 'POST'
    await fetch(url, { method, headers, body: JSON.stringify(body) })
    setEditing(null)
    setForm({ name: '', price: '', short_desc: '', description: '', image_url: '', gallery: [], in_stock: true, specs: '' })
    setGalleryInput('')
    loadData()
  }

  const deleteProduct = async (id) => {
    if (!confirm('Delete this product?')) return
    await fetch(`${API}/api/store/admin/products/${id}`, { method: 'DELETE', headers })
    loadData()
  }

  const editProduct = (p) => {
    setEditing(p.id)
    setForm({ name: p.name, price: p.price.toString(), short_desc: p.short_desc || '', description: p.description || '', image_url: p.image_url || '', gallery: p.gallery || [], in_stock: p.in_stock, specs: (p.specs || []).join('\n') })
    setGalleryInput('')
    setTab('products')
  }

  if (!user?.is_admin) return null

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="font-display text-3xl font-bold text-white mb-8" data-testid="admin-title">Admin Dashboard</h1>

      <div className="flex gap-4 mb-8">
        {['products', 'orders', 'members'].map(t => (
          <button key={t} onClick={() => setTab(t)} className={`font-display uppercase tracking-wider text-sm px-6 py-2 rounded-sm transition-colors ${tab === t ? 'bg-brand-500 text-dark-950' : 'bg-dark-800 text-dark-400 hover:text-white'}`} data-testid={`tab-${t}`}>
            {t} ({t === 'products' ? products.length : t === 'orders' ? orders.length : members.length})
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
              <div className="sm:col-span-2 flex gap-2">
                <input placeholder="Main Image URL" value={form.image_url} onChange={e => setForm(f => ({ ...f, image_url: e.target.value }))} className="flex-1 bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="product-form-image" />
                <button type="button" onClick={() => uploadImage('main')} disabled={uploading} className="bg-dark-700 text-dark-300 border border-dark-600 px-4 py-3 rounded-sm text-sm hover:bg-dark-600 hover:text-white transition-colors font-display whitespace-nowrap disabled:opacity-50" data-testid="upload-main-image-btn">
                  {uploading ? 'Uploading...' : 'Upload'}
                </button>
              </div>
              {form.image_url && (
                <div className="sm:col-span-2">
                  <img src={form.image_url} alt="Main preview" className="w-24 h-24 object-cover rounded-sm border border-dark-700" />
                </div>
              )}
              {/* Gallery Images */}
              <div className="sm:col-span-2 space-y-3">
                <label className="text-sm text-dark-400 font-display">Additional Gallery Images</label>
                <div className="flex gap-2">
                  <input placeholder="Paste image URL and click Add" value={galleryInput} onChange={e => setGalleryInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && galleryInput.trim()) { e.preventDefault(); setForm(f => ({ ...f, gallery: [...f.gallery, galleryInput.trim()] })); setGalleryInput('') }}} className="flex-1 bg-dark-800 border border-dark-700 text-white px-4 py-2 rounded-sm focus:outline-none focus:border-brand-500 text-sm" data-testid="gallery-url-input" />
                  <button type="button" onClick={() => { if (galleryInput.trim()) { setForm(f => ({ ...f, gallery: [...f.gallery, galleryInput.trim()] })); setGalleryInput('') }}} className="bg-brand-500/20 text-brand-400 border border-brand-500/30 px-4 py-2 rounded-sm text-sm hover:bg-brand-500/30 transition-colors font-display" data-testid="gallery-add-btn">Add</button>
                  <button type="button" onClick={() => uploadImage('gallery')} disabled={uploading} className="bg-dark-700 text-dark-300 border border-dark-600 px-4 py-2 rounded-sm text-sm hover:bg-dark-600 hover:text-white transition-colors font-display whitespace-nowrap disabled:opacity-50" data-testid="upload-gallery-image-btn">
                    {uploading ? 'Uploading...' : 'Upload'}
                  </button>
                </div>
                {form.gallery.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {form.gallery.map((url, i) => (
                      <div key={i} className="relative group">
                        <img src={url} alt={`Gallery ${i + 1}`} className="w-20 h-20 object-cover rounded-sm border border-dark-700" />
                        <button type="button" onClick={() => setForm(f => ({ ...f, gallery: f.gallery.filter((_, idx) => idx !== i) }))} className="absolute -top-1.5 -right-1.5 bg-red-500 text-white w-5 h-5 rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" data-testid={`gallery-remove-${i}`}>x</button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <textarea placeholder="Full Description" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={3} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500 sm:col-span-2" data-testid="product-form-desc" />
              <textarea placeholder="Specs (one per line)" value={form.specs} onChange={e => setForm(f => ({ ...f, specs: e.target.value }))} rows={3} className="bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500 sm:col-span-2" data-testid="product-form-specs" />
              <label className="flex items-center gap-2 text-dark-400">
                <input type="checkbox" checked={form.in_stock} onChange={e => setForm(f => ({ ...f, in_stock: e.target.checked }))} className="accent-brand-500" />
                In Stock
              </label>
            </div>
            <div className="mt-4 flex gap-3">
              <button onClick={saveProduct} className="font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-6 py-3 rounded-sm hover:bg-brand-400 transition-colors font-semibold" data-testid="product-form-save">{editing ? 'Update' : 'Add Product'}</button>
              {editing && <button onClick={() => { setEditing(null); setGalleryInput(''); setForm({ name: '', price: '', short_desc: '', description: '', image_url: '', gallery: [], in_stock: true, specs: '' }) }} className="text-sm text-dark-400 hover:text-white px-4">Cancel</button>}
            </div>
          </div>

          {/* Product List */}
          <div className="space-y-3">
            {products.map(p => (
              <div key={p.id} className="bg-dark-900 border border-dark-800 rounded-sm p-4 flex items-center gap-4">
                <img src={p.image_url || 'https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=100'} alt={p.name} className="w-16 h-16 object-cover rounded-sm" />
                <div className="flex-1">
                  <h3 className="font-display font-semibold text-white">{p.name}</h3>
                  <p className="text-sm text-dark-400">${p.price} - {p.in_stock ? 'In Stock' : 'Sold Out'}{p.gallery?.length > 0 && ` - ${p.gallery.length + 1} photos`}</p>
                </div>
                <button onClick={() => editProduct(p)} className="text-sm text-brand-400 hover:text-brand-300">Edit</button>
                <button onClick={() => deleteProduct(p.id)} className="text-sm text-red-400 hover:text-red-300">Delete</button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'orders' && (
        <div className="space-y-4" data-testid="orders-tab">
          {orders.length === 0 ? (
            <div className="bg-dark-900 border border-dark-800 rounded-sm p-8 text-center">
              <p className="text-dark-400">No orders yet</p>
            </div>
          ) : orders.map(o => (
            <div key={o.id} className="bg-dark-900 border border-dark-800 rounded-sm p-5" data-testid={`order-${o.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-4 mb-3">
                <div>
                  <p className="text-xs text-dark-500 font-mono">{o.id}</p>
                  <p className="text-sm text-white mt-1">{o.email}</p>
                  <p className="text-xs text-dark-500 mt-1">{new Date(o.created_at).toLocaleString()}</p>
                </div>
                <div className="text-right">
                  <p className="font-display text-xl font-bold text-brand-400">${o.total?.toFixed(2)}</p>
                  <div className="flex items-center gap-2 mt-1 justify-end">
                    <span className={`text-xs px-2 py-0.5 rounded-sm font-display ${o.payment_status === 'paid' ? 'bg-green-500/10 text-green-400' : o.payment_status === 'pending' ? 'bg-yellow-500/10 text-yellow-400' : 'bg-dark-700 text-dark-400'}`} data-testid={`order-payment-${o.id}`}>
                      {o.payment_status}
                    </span>
                    <select
                      value={o.status || 'initiated'}
                      onChange={async (e) => {
                        await fetch(`${API}/api/store/admin/orders/${o.id}/status`, { method: 'PUT', headers, body: JSON.stringify({ status: e.target.value }) })
                        loadData()
                      }}
                      className="bg-dark-800 border border-dark-700 text-white text-xs px-2 py-1 rounded-sm focus:outline-none"
                      data-testid={`order-status-${o.id}`}
                    >
                      {['initiated', 'processing', 'shipped', 'delivered', 'cancelled'].map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
              <div className="border-t border-dark-800 pt-3 space-y-1">
                {(o.items || []).map((item, i) => (
                  <div key={i} className="flex justify-between text-sm">
                    <span className="text-dark-300">{item.name} x{item.qty}</span>
                    <span className="text-dark-400">${(item.price * item.qty).toFixed(2)}</span>
                  </div>
                ))}
                <div className="flex justify-between text-xs text-dark-500 pt-1">
                  <span>Tax: ${o.tax?.toFixed(2)} | Shipping: ${o.shipping?.toFixed(2)} ({o.shipping_method || 'standard'})</span>
                </div>
              </div>
            </div>
          ))}
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
