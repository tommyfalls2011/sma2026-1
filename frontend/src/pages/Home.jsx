import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import ProductCard from '../components/ProductCard'

const API = import.meta.env.REACT_APP_BACKEND_URL || ''

export default function Home() {
  const [products, setProducts] = useState([])

  useEffect(() => {
    fetch(`${API}/api/store/products`).then(r => r.json()).then(setProducts).catch(() => {})
  }, [])

  return (
    <div>
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-brand-500/5 to-transparent" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 sm:py-32 relative">
          <div className="text-center mx-auto">
            <p className="font-display text-brand-400 tracking-[0.4em] uppercase text-sm mb-4" data-testid="hero-subtitle">Hand-Built in North Carolina</p>
            <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl font-bold text-white leading-[0.95]" data-testid="hero-title">
              SWING<br/>MASTER<br/><span className="text-brand-400">AMPS</span>
            </h1>
            <p className="mt-6 text-lg text-dark-300 max-w-xl mx-auto leading-relaxed">
              Premium HF amplifiers built with quality components. From 1-pill to 16-pill configurations, we build amps that push the power you need.
            </p>
            <div className="mt-8 flex justify-center gap-4">
              <Link to="/products" className="font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold" data-testid="hero-shop-btn">
                Shop Amps
              </Link>
              <Link to="/register" className="font-display uppercase tracking-wider text-sm border border-dark-600 text-dark-200 px-8 py-4 rounded-sm hover:border-brand-500 hover:text-brand-400 transition-colors font-semibold" data-testid="hero-join-btn">
                Join Free
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="flex items-center justify-between mb-10">
          <div>
            <p className="text-brand-400 text-xs tracking-[0.3em] uppercase font-display">Our Lineup</p>
            <h2 className="font-display text-2xl sm:text-3xl font-bold text-white mt-1">CB Amplifiers</h2>
          </div>
          <Link to="/products" className="text-sm text-brand-400 hover:text-brand-300 transition-colors">View All →</Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="product-grid">
          {products.map(p => <ProductCard key={p.id} product={p} />)}
          {products.length === 0 && (
            <div className="col-span-3 text-center py-20 text-dark-400">
              <p className="font-display text-xl">Loading inventory...</p>
            </div>
          )}
        </div>
      </section>

      {/* Why SMA */}
      <section className="border-t border-dark-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            <div className="text-center">
              <div className="w-12 h-12 bg-brand-500/10 rounded-sm flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>
              </div>
              <h3 className="font-display text-lg font-semibold text-white">Quality Built</h3>
              <p className="mt-2 text-sm text-dark-400">Every amp hand-assembled and tested before shipping</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-brand-500/10 rounded-sm flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.129-.504 1.09-1.124a17.902 17.902 0 00-3.213-9.193 2.056 2.056 0 00-1.58-.86H14.25M16.5 18.75h-2.25m0-11.177v-.958c0-.568-.422-1.048-.987-1.106a48.554 48.554 0 00-10.026 0 1.106 1.106 0 00-.987 1.106v7.635m12-6.677v6.677m0 4.5v-4.5m0 0h-12" /></svg>
              </div>
              <h3 className="font-display text-lg font-semibold text-white">US Shipping</h3>
              <p className="mt-2 text-sm text-dark-400">Fast shipping across the United States</p>
            </div>
            <div className="text-center">
              <div className="w-12 h-12 bg-brand-500/10 rounded-sm flex items-center justify-center mx-auto mb-4">
                <svg className="w-6 h-6 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" /></svg>
              </div>
              <h3 className="font-display text-lg font-semibold text-white">Direct Support</h3>
              <p className="mt-2 text-sm text-dark-400">Questions? Reach out directly — we're always here</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
