import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { orderApi } from "../api";

type OrderItem = {
  product_id: number;
  qty: number;
  unit_price: number;
};

type Order = {
  id: number;
  status: string;
  total: number;
  items: OrderItem[];
};

export default function OrderDetails() {
  const { orderId } = useParams();
  const nav = useNavigate();

  const [loading, setLoading] = useState(true);
  const [order, setOrder] = useState<Order | null>(null);

  const load = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Please login first");
      nav("/login");
      return;
    }

    if (!orderId) {
      setOrder(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const res = await orderApi.get<Order>(`/orders/${orderId}`);
      setOrder(res.data);
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || "Failed to load order");
      setOrder(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="candy-card p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-2xl font-extrabold">Order Details</h2>
          <div className="flex gap-2">
            <Link to="/"><button className="candy-btn-outline">Back to shop</button></Link>
            <button className="candy-btn-outline" onClick={load}>Refresh</button>
          </div>
        </div>

        {loading ? (
          <p className="mt-4 text-sm text-slate-600">Loading…</p>
        ) : !order ? (
          <div className="mt-4 rounded-2xl bg-white/60 p-4">
            <p className="text-sm text-slate-600">Order not found.</p>
          </div>
        ) : (
          <>
            <div className="mt-4 rounded-2xl bg-white/60 p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-sm text-slate-500">Order ID</div>
                <div className="font-bold">#{order.id}</div>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm text-slate-500">Status</div>
                <div className="font-bold">{order.status}</div>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-sm text-slate-500">Total</div>
                <div className="text-xl font-extrabold">{Number(order.total).toFixed(2)}</div>
              </div>
            </div>

            <div className="mt-4 space-y-3">
              {order.items.map((it, idx) => (
                <div
                  key={`${it.product_id}-${idx}`}
                  className="rounded-2xl bg-white/60 p-4 flex items-center justify-between"
                >
                  <div>
                    <div className="font-extrabold">Product #{it.product_id}</div>
                    <div className="text-sm text-slate-600">
                      Qty: {it.qty} · Unit: {Number(it.unit_price).toFixed(2)}
                    </div>
                  </div>
                  <div className="font-extrabold">
                    {(Number(it.unit_price) * Number(it.qty)).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>

            {order.status === "CREATED" && (
              <div className="mt-5">
                <Link to={`/payment/${order.id}`}>
                  <button className="candy-btn w-full">Go to Payment</button>
                </Link>
              </div>
            )}
          </>
        )}

        <p className="mt-4 text-xs text-slate-500">
          This page calls <code>GET /orders/{`{order_id}`}</code> from order-service.
        </p>
      </div>
    </div>
  );
}