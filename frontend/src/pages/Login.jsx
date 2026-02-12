import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-md mx-auto px-4 py-20">
      <div className="text-center mb-8">
        <h1 className="font-display text-3xl font-bold text-white" data-testid="login-title">Sign In</h1>
        <p className="text-dark-400 mt-2">Welcome back to SMA</p>
      </div>
      <form onSubmit={handleSubmit} className="bg-dark-900 border border-dark-800 rounded-sm p-6 space-y-4">
        {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm p-3 rounded" data-testid="login-error">{error}</div>}
        <div>
          <label className="block text-sm text-dark-400 mb-1">Email</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="login-email" />
        </div>
        <div>
          <label className="block text-sm text-dark-400 mb-1">Password</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className="w-full bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="login-password" />
        </div>
        <button type="submit" disabled={loading} className="w-full font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold disabled:opacity-50" data-testid="login-submit">
          {loading ? 'Signing In...' : 'Sign In'}
        </button>
        <p className="text-center text-sm text-dark-400">Don't have an account? <Link to="/register" className="text-brand-400 hover:text-brand-300">Join Free</Link></p>
      </form>
    </div>
  )
}
