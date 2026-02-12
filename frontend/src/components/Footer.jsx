import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="bg-dark-950 border-t border-dark-800 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <span className="font-display text-lg font-bold text-white">SWING MASTER AMPS</span>
            <p className="mt-2 text-sm text-dark-400 leading-relaxed">Hand-built CB amplifiers from North Carolina. Quality you can trust on the airwaves.</p>
          </div>
          <div>
            <h4 className="font-display text-sm font-semibold text-white uppercase tracking-wider mb-3">Quick Links</h4>
            <div className="flex flex-col gap-2">
              <Link to="/products" className="text-sm text-dark-400 hover:text-brand-400 transition-colors">Shop Amps</Link>
              <Link to="/register" className="text-sm text-dark-400 hover:text-brand-400 transition-colors">Become a Member</Link>
              <Link to="/privacy" className="text-sm text-dark-400 hover:text-brand-400 transition-colors">Privacy Policy</Link>
            </div>
          </div>
          <div>
            <h4 className="font-display text-sm font-semibold text-white uppercase tracking-wider mb-3">Contact</h4>
            <p className="text-sm text-dark-400">fallstommy@gmail.com</p>
            <p className="text-sm text-dark-400 mt-1">CashApp: $tfcp2011</p>
            <p className="text-sm text-dark-400 mt-1">North Carolina, USA</p>
            <p className="text-sm text-dark-400 mt-1">US Shipping Only</p>
          </div>
        </div>
        <div className="mt-8 pt-6 border-t border-dark-800 text-center">
          <p className="text-xs text-dark-500">&copy; {new Date().getFullYear()} Swing Master Amps. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}
