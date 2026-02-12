import { Link } from 'react-router-dom'

export default function ProductCard({ product }) {
  return (
    <Link to={`/product/${product.id}`} className="group" data-testid={`product-card-${product.id}`}>
      <div className="bg-dark-900 border border-dark-800 rounded-sm overflow-hidden hover:border-brand-500/40 transition-all duration-300 group-hover:-translate-y-1">
        <div className="aspect-square bg-dark-800 overflow-hidden">
          <img
            src={product.image_url || 'https://images.unsplash.com/photo-1672689933227-2ce1249c46a9?w=600'}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
          />
        </div>
        <div className="p-5">
          <h3 className="font-display text-lg font-semibold text-white group-hover:text-brand-400 transition-colors">{product.name}</h3>
          <p className="text-sm text-dark-400 mt-1 line-clamp-2">{product.short_desc}</p>
          <div className="mt-3 flex items-center justify-between">
            <span className="font-display text-2xl font-bold text-brand-400">${product.price}</span>
            {product.in_stock ? (
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">In Stock</span>
            ) : (
              <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">Sold Out</span>
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}
