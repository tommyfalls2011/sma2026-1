import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(name, email, password)
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
        <h1 className="font-display text-3xl font-bold text-white" data-testid="register-title">Join SMA</h1>
        <p className="text-dark-400 mt-2">Free membership — no charge</p>
      </div>
      <form onSubmit={handleSubmit} className="bg-dark-900 border border-dark-800 rounded-sm p-6 space-y-4">
        {error && <div className="bg-red-500/10 border border-red-500/30 text-red-400 text-sm p-3 rounded" data-testid="register-error">{error}</div>}
        <div>
          <label className="block text-sm text-dark-400 mb-1">Name</label>
          <input type="text" value={name} onChange={e => setName(e.target.value)} required className="w-full bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="register-name" />
        </div>
        <div>
          <label className="block text-sm text-dark-400 mb-1">Email</label>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className="w-full bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="register-email" />
        </div>
        <div>
          <label className="block text-sm text-dark-400 mb-1">Password</label>
          <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} className="w-full bg-dark-800 border border-dark-700 text-white px-4 py-3 rounded-sm focus:outline-none focus:border-brand-500" data-testid="register-password" />
        </div>
        <button type="submit" disabled={loading} className="w-full font-display uppercase tracking-wider text-sm bg-brand-500 text-dark-950 px-8 py-4 rounded-sm hover:bg-brand-400 transition-colors font-semibold disabled:opacity-50" data-testid="register-submit">
          {loading ? 'Creating Account...' : 'Create Free Account'}
        </button>
        <p className="text-center text-sm text-dark-400">Already a member? <Link to="/login" className="text-brand-400 hover:text-brand-300">Sign In</Link></p>
      </form>
    </div>
  )
}
