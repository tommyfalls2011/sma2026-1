import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useCart } from '../context/CartContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const { count } = useCart()

  return (
    <nav className="sticky top-0 z-50 bg-dark-950/95 backdrop-blur-md border-b border-dark-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-3" data-testid="nav-logo">
            <div className="w-10 h-10 bg-brand-500 rounded-sm flex items-center justify-center">
              <span className="font-display font-bold text-dark-950 text-lg">S</span>
            </div>
            <div>
              <span className="font-display text-xl font-bold text-white tracking-wide">SWING MASTER</span>
              <span className="block text-[10px] text-brand-400 tracking-[0.3em] uppercase -mt-1">Amplifiers</span>
            </div>
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <Link to="/" className="text-sm font-medium text-dark-300 hover:text-brand-400 transition-colors" data-testid="nav-home">Home</Link>
            <Link to="/products" className="text-sm font-medium text-dark-300 hover:text-brand-400 transition-colors" data-testid="nav-products">Shop</Link>
          </div>

          <div className="flex items-center gap-4">
            <Link to="/cart" className="relative text-dark-300 hover:text-brand-400 transition-colors" data-testid="nav-cart">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" /></svg>
              {count > 0 && <span className="absolute -top-2 -right-2 bg-brand-500 text-dark-950 text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">{count}</span>}
            </Link>
            {user ? (
              <div className="flex items-center gap-3">
                <span className="text-sm text-dark-400 hidden sm:block">{user.name}</span>
                {user.is_admin && <Link to="/admin" className="text-xs bg-brand-500/20 text-brand-400 px-2 py-1 rounded" data-testid="nav-admin">Admin</Link>}
                <button onClick={logout} className="text-sm text-dark-400 hover:text-red-400 transition-colors" data-testid="nav-logout">Logout</button>
              </div>
            ) : (
              <Link to="/login" className="text-sm font-medium bg-brand-500 text-dark-950 px-4 py-2 rounded-sm hover:bg-brand-400 transition-colors" data-testid="nav-login">Sign In</Link>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
