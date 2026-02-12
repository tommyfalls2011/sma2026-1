import { useState, useEffect } from 'react'
import ProductCard from '../components/ProductCard'

const API = import.meta.env.REACT_APP_BACKEND_URL || ''

export default function Products() {
  const [products, setProducts] = useState([])

  useEffect(() => {
    fetch(`${API}/api/store/products`).then(r => r.json()).then(setProducts).catch(() => {})
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-10">
        <p className="text-brand-400 text-xs tracking-[0.3em] uppercase font-display">Shop</p>
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-white mt-1" data-testid="products-title">All Amplifiers</h1>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="products-grid">
        {products.map(p => <ProductCard key={p.id} product={p} />)}
        {products.length === 0 && (
          <div className="col-span-3 text-center py-20 text-dark-400">
            <p className="font-display text-xl">No products available</p>
          </div>
        )}
      </div>
    </div>
  )
}
