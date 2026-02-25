import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate } from "react-router-dom";
import { paymentApi } from "../api";

type Payment = {
  id: number;
  order_id: number;
  user_id: number;
  amount: number;
  status: string; // SUCCESS | FAILED | PENDING
};

export default function Payments() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [payments, setPayments] = useState<Payment[]>([]);

  const handleAuthError = () => {
    toast.error("Session expired. Please login again.");
    localStorage.removeItem("token");
    nav("/login");
  };

  const load = async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Please login first");
      nav("/login");
      return;
    }

    try {
      setLoading(true);
      const res = await paymentApi.get<Payment[]>("/payments", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setPayments(res.data || []);
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 401 || status === 403) {
        handleAuthError();
        return;
      }
      toast.error(e?.response?.data?.detail || "Failed to load payments");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto max-w-3xl p-6">
      <div className="candy-card p-6">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-2xl font-extrabold">Payment History</h2>
          <div className="flex gap-2">
            <Link to="/">
              <button className="candy-btn-outline">Back to shop</button>
            </Link>
            <button className="candy-btn-outline" onClick={load} disabled={loading}>
              {loading ? "Loading…" : "Refresh"}
            </button>
          </div>
        </div>

        {loading ? (
          <p className="mt-4 text-sm text-slate-600">Loading…</p>
        ) : payments.length === 0 ? (
          <div className="mt-4 rounded-2xl bg-white/60 p-4">
            <p className="text-sm text-slate-600">No payments yet.</p>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {payments.map((p) => (
              <div
                key={p.id}
                className="flex flex-col gap-2 rounded-2xl bg-white/60 p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <div className="font-extrabold">Payment #{p.id}</div>
                  <div className="text-sm text-slate-600">
                    Order: #{p.order_id} · Amount: {Number(p.amount).toFixed(2)}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="rounded-xl bg-slate-100 px-3 py-1 text-sm font-bold">
                    {p.status}
                  </div>
                  <Link to={`/orders/${p.order_id}`}>
                    <button className="candy-btn-outline">View order</button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        <p className="mt-4 text-xs text-slate-500">
          Tip: This page calls <code>GET /payments</code> from payment-service.
        </p>
      </div>
    </div>
  );
}