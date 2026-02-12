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
  const [showGallery, setShowGallery] = useState(false)
  const [activeImg, setActiveImg] = useState(0)

  useEffect(() => {
    fetch(`${API}/api/store/products/${id}`).then(r => r.json()).then(setProduct).catch(() => {})
  }, [id])

  if (!product) return <div className="max-w-7xl mx-auto px-4 py-20 text-center text-dark-400">Loading...</div>

  const allImages = [product.image_url, ...(product.gallery || [])].filter(Boolean)

  const handleAdd = () => {
    addItem({ id: product.id, name: product.name, price: product.price, image_url: product.image_url })
    setAdded(true)
    setTimeout(() => setAdded(false), 2000)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Link to="/products" className="text-sm text-dark-400 hover:text-brand-400 transition-colors mb-8 inline-block" data-testid="back-link">← Back to Shop</Link>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
        <div>
          <div className="aspect-square bg-dark-900 border border-dark-800 rounded-sm overflow-hidden relative cursor-pointer" onClick={() => { setActiveImg(0); setShowGallery(true) }}>
            <img src={product.image_url || 'https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=800'} alt={product.name} className="w-full h-full object-cover" />
            {allImages.length > 1 && (
              <button onClick={(e) => { e.stopPropagation(); setShowGallery(true) }} className="absolute bottom-3 right-3 bg-dark-950/80 backdrop-blur-sm text-brand-400 border border-brand-500/30 px-3 py-2 rounded-sm flex items-center gap-2 hover:bg-dark-950 transition-colors" data-testid="view-gallery-btn">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" /></svg>
                <span className="text-xs font-display font-semibold">+{allImages.length - 1} MORE</span>
              </button>
            )}
          </div>
          {allImages.length > 1 && (
            <div className="flex gap-2 mt-3">
              {allImages.map((img, i) => (
                <button key={i} onClick={() => { setActiveImg(i); setShowGallery(true) }} className={`w-16 h-16 rounded-sm overflow-hidden border-2 transition-colors ${i === 0 ? 'border-brand-500/50' : 'border-dark-700 hover:border-dark-500'}`}>
                  <img src={img} alt={`View ${i + 1}`} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="flex flex-col justify-center">
          <p className="text-brand-400 text-xs tracking-[0.3em] uppercase font-display">HF Amplifier</p>
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

      {/* Gallery Modal */}
      {showGallery && (
        <div className="fixed inset-0 z-50 bg-dark-950/95 backdrop-blur-md flex items-center justify-center" onClick={() => setShowGallery(false)}>
          <button onClick={() => setShowGallery(false)} className="absolute top-4 right-4 text-dark-400 hover:text-white z-10" data-testid="gallery-close">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
          <div className="max-w-3xl w-full mx-4" onClick={e => e.stopPropagation()}>
            <img src={allImages[activeImg]} alt={`Image ${activeImg + 1}`} className="w-full max-h-[70vh] object-contain rounded-sm" />
            <div className="flex justify-center gap-3 mt-4">
              {allImages.map((img, i) => (
                <button key={i} onClick={() => setActiveImg(i)} className={`w-16 h-16 rounded-sm overflow-hidden border-2 transition-colors ${i === activeImg ? 'border-brand-500' : 'border-dark-700 hover:border-dark-500'}`}>
                  <img src={img} alt={`Thumb ${i + 1}`} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          </div>
          {allImages.length > 1 && (
            <>
              <button onClick={(e) => { e.stopPropagation(); setActiveImg(i => i > 0 ? i - 1 : allImages.length - 1) }} className="absolute left-4 text-dark-400 hover:text-white">
                <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15.75 19.5L8.25 12l7.5-7.5" /></svg>
              </button>
              <button onClick={(e) => { e.stopPropagation(); setActiveImg(i => i < allImages.length - 1 ? i + 1 : 0) }} className="absolute right-4 text-dark-400 hover:text-white">
                <svg className="w-10 h-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}
