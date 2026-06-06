import { Heart } from 'lucide-react';

type FavoriteProduct = {
  id: string;
  slug?: string | null;
  name: string;
  imageUrl?: string | null;
  price?: number;
  discountPrice?: number | null;
  favoritedAt?: string | null;
};

type FavoriteProductsTabProps = {
  favorites: FavoriteProduct[];
  onOpenProduct: (product: FavoriteProduct) => void;
  onRemoveFavorite: (productId: string) => void;
};

function formatFavoriteTime(value?: string | null) {
  if (!value) return 'Chưa có thời gian';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Chưa có thời gian';
  return date.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function FavoriteProductsTab({ favorites, onOpenProduct, onRemoveFavorite }: FavoriteProductsTabProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
      <div className="flex items-center gap-3 mb-5">
        <Heart className="w-6 h-6 text-[#d70018]" />
        <h3 className="font-bold text-gray-800">Sản phẩm yêu thích</h3>
      </div>
      {favorites.length === 0 ? (
        <p className="text-sm text-gray-500">Bạn chưa có sản phẩm yêu thích nào.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {favorites.map((product) => (
            <div
              key={product.id}
              className="border border-gray-100 rounded-lg p-4 flex flex-col cursor-pointer hover:shadow-md transition-shadow relative"
              onClick={() => onOpenProduct(product)}
            >
              <div className="aspect-square mb-3 relative flex items-center justify-center p-2">
                <img src={product.imageUrl || ''} alt={product.name} className="w-full h-full object-contain" />
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onRemoveFavorite(product.id);
                  }}
                  className="absolute top-2 right-2 p-1.5 bg-white/80 backdrop-blur-sm shadow-sm rounded-full text-[#d70018] hover:scale-110 transition-transform"
                >
                  <Heart className="w-5 h-5 fill-[#d70018]" />
                </button>
              </div>
              <h4 className="text-sm font-semibold text-gray-800 line-clamp-2 mt-auto">{product.name}</h4>
              <p className="text-[#d70018] font-bold mt-2">{(product.discountPrice || product.price || 0).toLocaleString('vi-VN')} đ</p>
              <p className="mt-1 text-xs font-medium text-slate-500">Đã yêu thích lúc {formatFavoriteTime(product.favoritedAt)}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
