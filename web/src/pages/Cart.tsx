// web/src/pages/Cart.tsx
import { useEffect, useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate } from "react-router-dom";
import { productApi, orderApi } from "../api";

type CartItem = { product_id: number; qty: number };

type Product = {
  id: number;
  name: string;
  description?: string | null;
  price: number;
  image_url?: string | null;
  published?: boolean;
};

function readCart(): CartItem[] {
  try {
    const raw = localStorage.getItem("cart");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((x: any) => ({
        product_id: Number(x?.product_id),
        qty: Number(x?.qty),
      }))
      .filter((x) => Number.isFinite(x.product_id) && Number.isFinite(x.qty) && x.qty > 0);
  } catch {
    return [];
  }
}

function writeCart(items: CartItem[]) {
  localStorage.setItem("cart", JSON.stringify(items));
}

export default function Cart() {
  const nav = useNavigate();
  const [items, setItems] = useState<CartItem[]>([]);
  const [productsById, setProductsById] = useState<Record<number, Product>>({});
  const [loading, setLoading] = useState(true);
  const [checkingOut, setCheckingOut] = useState(false);

  // Load cart from localStorage on mount + keep it in sync across tabs/windows
  useEffect(() => {
    setItems(readCart());
    const onStorage = (e: StorageEvent) => {
      if (e.key === "cart") setItems(readCart());
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  // Fetch product catalog (published) and map by id for display/total
  useEffect(() => {
    const run = async () => {
      try {
        setLoading(true);
        const res = await productApi.get<Product[]>("/products");
        const map: Record<number, Product> = {};
        for (const p of res.data) map[p.id] = p;
        setProductsById(map);
      } catch (e: any) {
        toast.error(e?.response?.data?.detail || "Failed to load products");
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  const enriched = useMemo(() => {
    return items.map((it) => {
      const p = productsById[it.product_id];
      const unit = p?.price ?? 0;
      return {
        ...it,
        product: p,
        unit_price: unit,
        line_total: unit * it.qty,
      };
    });
  }, [items, productsById]);

  const total = useMemo(() => enriched.reduce((s, x) => s + x.line_total, 0), [enriched]);

  const setQty = (product_id: number, qty: number) => {
    const q = Math.max(1, Math.floor(qty || 1));
    const next = items.map((x) => (x.product_id === product_id ? { ...x, qty: q } : x));
    setItems(next);
    writeCart(next);
  };

  const removeItem = (product_id: number) => {
    const next = items.filter((x) => x.product_id !== product_id);
    setItems(next);
    writeCart(next);
    toast.success("Removed from cart");
  };

  const clearCart = () => {
    setItems([]);
    localStorage.removeItem("cart");
    toast.success("Cart cleared");
  };

  const checkout = async () => {
    if (!items.length) return toast.error("Cart is empty");

    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Please login first");
      nav("/login");
      return;
    }

    // Validate products exist/published
    const missing = enriched.filter((x) => !x.product);
    if (missing.length) {
      toast.error("Some items are unavailable (refresh products and try again)");
      return;
    }

    try {
      setCheckingOut(true);
      const payload = {
        items: items.map((i) => ({ product_id: i.product_id, qty: i.qty })),
      };
      const res = await orderApi.post("/orders", payload);

      localStorage.removeItem("cart");
      setItems([]);

      toast.success(`Order created #${res.data?.id}`);
      // If you have an order details page, you can route there:
      nav(`/orders/${res.data?.id}`);
      // nav("/");
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Checkout failed");
    } finally {
      setCheckingOut(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <div className="candy-card p-6">
          <h2 className="text-2xl font-extrabold">Your Cart</h2>
          <p className="mt-3 text-sm text-slate-600">Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="candy-card p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-2xl font-extrabold">Your Cart</h2>
          <div className="flex gap-2">
            <Link to="/">
              <button className="candy-btn-outline">Continue shopping</button>
            </Link>
            <button className="candy-btn-outline" onClick={clearCart} disabled={!items.length}>
              Clear
            </button>
          </div>
        </div>

        {!items.length ? (
          <div className="mt-4 rounded-2xl bg-white/60 p-4">
            <p className="text-sm text-slate-600">Cart is empty.</p>
          </div>
        ) : (
          <>
            <div className="mt-5 space-y-3">
              {enriched.map((x) => (
                <div
                  key={x.product_id}
                  className="flex flex-col gap-3 rounded-2xl bg-white/60 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-center gap-3">
                    {x.product?.image_url ? (
                      <img
                        src={x.product.image_url}
                        alt={x.product.name}
                        className="h-14 w-14 rounded-xl object-cover"
                        onError={(e) => {
                          (e.currentTarget as HTMLImageElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="h-14 w-14 rounded-xl bg-slate-200" />
                    )}

                    <div>
                      <div className="font-extrabold">{x.product?.name ?? `Product #${x.product_id}`}</div>
                      <div className="text-sm text-slate-600">
                        Unit: {x.unit_price.toFixed(2)} · Line: {x.line_total.toFixed(2)}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 sm:justify-end">
                    <button
                      className="candy-btn-outline"
                      onClick={() => setQty(x.product_id, x.qty - 1)}
                      disabled={x.qty <= 1}
                    >
                      −
                    </button>
                    <input
                      className="candy-input w-20 text-center"
                      type="number"
                      min={1}
                      value={x.qty}
                      onChange={(e) => setQty(x.product_id, Number(e.target.value))}
                    />
                    <button className="candy-btn-outline" onClick={() => setQty(x.product_id, x.qty + 1)}>
                      +
                    </button>

                    <button className="candy-btn-outline" onClick={() => removeItem(x.product_id)}>
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 flex flex-col items-stretch justify-between gap-3 rounded-2xl bg-white/60 p-4 sm:flex-row sm:items-center">
              <div className="text-lg font-extrabold">Total: {total.toFixed(2)}</div>
              <button className="candy-btn" onClick={checkout} disabled={checkingOut}>
                {checkingOut ? "Processing…" : "Checkout"}
              </button>
            </div>

            <p className="mt-3 text-xs text-slate-500">
              Note: Cart is stored in localStorage under <code>cart</code>. Checkout creates an order via order-service.
            </p>
          </>
        )}
      </div>
    </div>
  );
}