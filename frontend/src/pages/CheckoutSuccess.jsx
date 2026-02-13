import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useCart } from '../context/CartContext'

const API = import.meta.env.REACT_APP_BACKEND_URL || ''

export default function CheckoutSuccess() {
  const [searchParams] = useSearchParams()
  const sessionId = searchParams.get('session_id')
  const [status, setStatus] = useState('checking')
  const [orderInfo, setOrderInfo] = useState(null)
  const { clearCart } = useCart()

  useEffect(() => {
    if (!sessionId) { setStatus('error'); return }
    let attempts = 0
    const poll = async () => {
      if (attempts >= 8) { setStatus('timeout'); return }
      attempts++
      try {
        const res = await fetch(`${API}/api/store/checkout/status/${sessionId}`)
        const data = await res.json()
        setOrderInfo(data)
        if (data.payment_status === 'paid') {
          setStatus('success')
          clearCart()
          return
        } else if (data.status === 'expired') {
          setStatus('expired')
          return
        }
        setStatus('processing')
        setTimeout(poll, 2000)
      } catch {
        setStatus('error')
      }
    }
    poll()
  }, [sessionId])

  return (
    <div className="max-w-2xl mx-auto px-4 py-20 text-center">
      {status === 'checking' && (
        <div data-testid="checkout-checking">
          <div className="w-12 h-12 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
          <h1 className="font-display text-3xl font-bold text-white">Checking Payment...</h1>
          <p className="text-dark-400 mt-2">Please wait while we verify your payment.</p>
        </div>
      )}
      {status === 'processing' && (
        <div data-testid="checkout-processing">
          <div className="w-12 h-12 border-2 border-brand-500 border-t-transparent rounded-full animate-spin mx-auto mb-6" />
          <h1 className="font-display text-3xl font-bold text-white">Processing Payment...</h1>
          <p className="text-dark-400 mt-2">Your payment is being processed. This may take a moment.</p>
        </div>
      )}
      {status === 'success' && (
        <div data-testid="checkout-success">
          <div className="w-16 h-16 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
          </div>
          <h1 className="font-display text-3xl font-bold text-white">Payment Successful!</h1>
          <p className="text-dark-400 mt-2">Thank you for your order. You'll receive a confirmation email shortly.</p>
          {orderInfo && (
            <div className="mt-6 bg-dark-900 border border-dark-800 rounded-sm p-6 text-left">
              <p className="text-sm text-dark-400">Order ID: <span className="text-white font-mono" data-testid="order-id">{orderInfo.order_id}</span></p>
              <p className="text-sm text-dark-400 mt-1">Amount: <span className="text-brand-400 font-bold">${(orderInfo.amount_total / 100).toFixed(2)}</span></p>
            </div>
          )}
          <Link to="/products" className="inline-block mt-8 font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold">Continue Shopping</Link>
        </div>
      )}
      {(status === 'error' || status === 'timeout' || status === 'expired') && (
        <div data-testid="checkout-error">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
          </div>
          <h1 className="font-display text-3xl font-bold text-white">
            {status === 'expired' ? 'Session Expired' : status === 'timeout' ? 'Status Check Timed Out' : 'Something Went Wrong'}
          </h1>
          <p className="text-dark-400 mt-2">
            {status === 'expired' ? 'Your payment session expired. Please try again.' : 'If you were charged, please contact us. Your payment may still be processing.'}
          </p>
          <Link to="/cart" className="inline-block mt-8 font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold">Back to Cart</Link>
        </div>
      )}
    </div>
  )
}
