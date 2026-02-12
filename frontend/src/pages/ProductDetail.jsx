import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { useAuth } from '../context/AuthContext'

const API = import.meta.env.REACT_APP_BACKEND_URL || ''

export default function ProductDetail() {
  const { id } = useParams()
  const { addItem } = useCart()
  const { user } = useAuth()
  const [product, setProduct] = useState(null)
  const [added, setAdded] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/store/products/${id}`).then(r => r.json()).then(setProduct).catch(() => {})
  }, [id])

  if (!product) return <div className="max-w-7xl mx-auto px-4 py-20 text-center text-dark-400">Loading...</div>

  const handleAdd = () => {
    addItem({ id: product.id, name: product.name, price: product.price, image_url: product.image_url })
    setAdded(true)
    setTimeout(() => setAdded(false), 2000)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Link to="/products" className="text-sm text-dark-400 hover:text-brand-400 transition-colors mb-8 inline-block" data-testid="back-link">← Back to Shop</Link>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div className="aspect-square bg-dark-900 border border-dark-800 rounded-sm overflow-hidden">
          <img src={product.image_url || 'https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=800'} alt={product.name} className="w-full h-full object-cover" />
        </div>
        <div className="flex flex-col justify-center">
          <p className="text-brand-400 text-xs tracking-[0.3em] uppercase font-display">CB Amplifier</p>
          <h1 className="font-display text-3xl sm:text-4xl font-bold text-white mt-2" data-testid="product-name">{product.name}</h1>
          <p className="font-display text-4xl font-bold text-brand-400 mt-4" data-testid="product-price">${product.price}</p>
          <p className="text-dark-300 mt-6 leading-relaxed">{product.description}</p>
          {product.specs && (
            <div className="mt-6 space-y-2">
              {product.specs.map((s, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-dark-400">
                  <span className="w-1.5 h-1.5 bg-brand-500 rounded-full" />
                  {s}
                </div>
              ))}
            </div>
          )}
          <div className="mt-8 flex gap-4">
            {user ? (
              <button
                onClick={handleAdd}
                disabled={!product.in_stock}
                className={`font-display uppercase tracking-wider text-sm px-8 py-4 rounded-sm font-semibold transition-all ${
                  !product.in_stock ? 'bg-dark-700 text-dark-500 cursor-not-allowed'
                  : added ? 'bg-green-500 text-white' 
                  : 'bg-brand-500 text-dark-950 hover:bg-brand-400'
                }`}
                data-testid="add-to-cart-btn"
              >
                {!product.in_stock ? 'Sold Out' : added ? 'Added!' : 'Add to Cart'}
              </button>
            ) : (
              <Link to="/login" className="font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold" data-testid="login-to-buy-btn">
                Sign In to Buy
              </Link>
            )}
          </div>
          <div className="mt-6 flex gap-6 text-xs text-dark-500">
            <span>US Shipping Only</span>
            <span>NC Sales Tax Applied</span>
          </div>
        </div>
      </div>
    </div>
  )
}
