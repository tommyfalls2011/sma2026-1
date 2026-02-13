import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCart } from '../context/CartContext'
import { useAuth } from '../context/AuthContext'

const API = import.meta.env.REACT_APP_BACKEND_URL || ''
const NC_TAX_RATE = 0.075
const SHIPPING_RATES = { standard: 15, priority: 25, express: 45 }

export default function Cart() {
  const { items, removeItem, updateQty, total, count, clearCart } = useCart()
  const { user, token } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [shippingMethod, setShippingMethod] = useState('standard')

  const tax = total * NC_TAX_RATE
  const shipping = count > 0 ? SHIPPING_RATES[shippingMethod] : 0
  const grandTotal = total + tax + shipping

  const handleCheckout = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API}/api/store/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          items: items.map(i => ({ id: i.id, qty: i.qty })),
          origin_url: window.location.origin,
          shipping: shippingMethod
        })
      })
      const data = await res.json()
      if (res.ok && data.url) {
        window.location.href = data.url
      } else {
        setError(data.detail || 'Failed to create checkout session')
        setLoading(false)
      }
    } catch {
      setError('Network error. Please try again.')
      setLoading(false)
    }
  }

  if (items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <h1 className="font-display text-3xl font-bold text-white" data-testid="cart-empty">Your Cart is Empty</h1>
        <p className="text-dark-400 mt-2">Browse our amplifiers and add some to your cart.</p>
        <Link to="/products" className="inline-block mt-6 font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold">Shop Amps</Link>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="font-display text-3xl font-bold text-white mb-8" data-testid="cart-title">Your Cart ({count})</h1>
      <div className="space-y-4">
        {items.map(item => (
          <div key={item.id} className="bg-dark-900 border border-dark-800 rounded-sm p-4 flex items-center gap-4" data-testid={`cart-item-${item.id}`}>
            <img src={item.image_url || 'https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=200'} alt={item.name} className="w-20 h-20 object-cover rounded-sm" />
            <div className="flex-1">
              <h3 className="font-display text-lg font-semibold text-white">{item.name}</h3>
              <p className="text-brand-400 font-display font-bold">${item.price}</p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => updateQty(item.id, item.qty - 1)} className="w-8 h-8 bg-dark-800 text-white rounded-sm hover:bg-dark-700 flex items-center justify-center">-</button>
              <span className="w-8 text-center text-white font-medium">{item.qty}</span>
              <button onClick={() => updateQty(item.id, item.qty + 1)} className="w-8 h-8 bg-dark-800 text-white rounded-sm hover:bg-dark-700 flex items-center justify-center">+</button>
            </div>
            <p className="font-display text-lg font-bold text-white w-24 text-right">${(item.price * item.qty).toFixed(2)}</p>
            <button onClick={() => removeItem(item.id)} className="text-dark-500 hover:text-red-400 transition-colors" data-testid={`remove-${item.id}`}>
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-8 bg-dark-900 border border-dark-800 rounded-sm p-6">
        <div className="space-y-3">
          <div className="flex justify-between text-sm text-dark-400"><span>Subtotal</span><span>${total.toFixed(2)}</span></div>
          <div className="flex justify-between text-sm text-dark-400"><span>NC Sales Tax (6.75%)</span><span>${tax.toFixed(2)}</span></div>
          <div className="flex justify-between text-sm text-dark-400"><span>Shipping (Standard)</span><span>${shipping.toFixed(2)}</span></div>
          <div className="border-t border-dark-700 pt-3 flex justify-between">
            <span className="font-display text-lg font-bold text-white">Total</span>
            <span className="font-display text-2xl font-bold text-brand-400" data-testid="cart-total">${grandTotal.toFixed(2)}</span>
          </div>
        </div>
        <div className="mt-6 space-y-3">
          {error && <p className="text-red-400 text-sm" data-testid="checkout-error">{error}</p>}
          <p className="text-xs text-dark-500">Payment Options: Stripe (Credit/Debit) or CashApp ($tfcp2011)</p>
          {user ? (
            <button onClick={handleCheckout} disabled={loading} className="w-full font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold disabled:opacity-50" data-testid="checkout-btn">
              {loading ? 'Redirecting to Stripe...' : 'Proceed to Checkout'}
            </button>
          ) : (
            <Link to="/login" className="block text-center w-full font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold">
              Sign In to Checkout
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}
