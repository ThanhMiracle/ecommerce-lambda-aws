import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import toast from "react-hot-toast";
import { orderApi, paymentApi } from "../api";

type Order = {
  id: number;
  status: string;
  total: number;
  items: { product_id: number; qty: number; unit_price: number }[];
};

type PayPayload = {
  shipping_address: string;
  phone_number: string;
};

const ADDRESS_KEY = "checkout_address";
const PHONE_KEY = "checkout_phone";

function normalizePhone(raw: string) {
  // keep digits + optional leading +
  const trimmed = raw.trim();
  if (trimmed.startsWith("+")) {
    return "+" + trimmed.slice(1).replace(/\D/g, "");
  }
  return trimmed.replace(/\D/g, "");
}

function isValidPhone(phone: string) {
  // simple rule: 9-15 digits (E.164-ish), allow leading +
  const p = normalizePhone(phone);
  const digits = p.startsWith("+") ? p.slice(1) : p;
  return digits.length >= 9 && digits.length <= 15;
}

export default function Payment() {
  const { orderId } = useParams<{ orderId: string }>();
  const nav = useNavigate();

  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);

  // NEW: address + phone form
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");

  const getTokenOrRedirect = (): string | null => {
    const token = localStorage.getItem("token");
    if (!token) {
      toast.error("Please login first");
      nav("/login");
      return null;
    }
    return token;
  };

  const handleAuthError = () => {
    toast.error("Session expired. Please login again.");
    localStorage.removeItem("token");
    nav("/login");
  };

  const loadOrder = async (id: string) => {
    const token = getTokenOrRedirect();
    if (!token) return null;

    try {
      const res = await orderApi.get<Order>(`/orders/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setOrder(res.data);
      return res.data;
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 401 || status === 403) {
        handleAuthError();
        return null;
      }
      toast.error(e?.response?.data?.detail || "Failed to load order");
      setOrder(null);
      return null;
    }
  };

  // Load order
  useEffect(() => {
    if (!orderId) {
      setLoading(false);
      setOrder(null);
      return;
    }

    (async () => {
      setLoading(true);
      await loadOrder(orderId);
      setLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  // Load saved address/phone
  useEffect(() => {
    const savedAddress = localStorage.getItem(ADDRESS_KEY) || "";
    const savedPhone = localStorage.getItem(PHONE_KEY) || "";
    setAddress(savedAddress);
    setPhone(savedPhone);
  }, []);

  // Persist as user types
  useEffect(() => {
    localStorage.setItem(ADDRESS_KEY, address);
  }, [address]);

  useEffect(() => {
    localStorage.setItem(PHONE_KEY, phone);
  }, [phone]);

  const isPayable = useMemo(() => order?.status === "CREATED", [order]);

  const validateForm = (): boolean => {
    if (!address.trim()) {
      toast.error("Please enter your shipping address");
      return false;
    }
    if (!phone.trim()) {
      toast.error("Please enter your phone number");
      return false;
    }
    if (!isValidPhone(phone)) {
      toast.error("Phone number is invalid (use 9–15 digits)");
      return false;
    }
    return true;
  };

  const handlePay = async () => {
    if (!orderId) return;

    const token = getTokenOrRedirect();
    if (!token) return;

    if (!validateForm()) return;

    const payload: PayPayload = {
      shipping_address: address.trim(),
      phone_number: normalizePhone(phone),
    };

    try {
      setPaying(true);

      const res = await paymentApi.post<{ ok: boolean; payment_id: number }>(
        `/payments/${orderId}`,
        payload,
        { headers: { Authorization: `Bearer ${token}` } }
      );

      toast.success("Payment successful 🎉");

      // optional refresh (don’t block redirect)
      await loadOrder(orderId);

      nav("/payments", { replace: true });
      return res.data;
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 401 || status === 403) {
        handleAuthError();
        return;
      }
      toast.error(e?.response?.data?.detail || "Payment failed");
    } finally {
      setPaying(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-xl p-6">
        <div className="candy-card p-6">Loading payment info…</div>
      </div>
    );
  }

  if (!orderId) {
    return (
      <div className="mx-auto max-w-xl p-6">
        <div className="candy-card p-6">
          <h2 className="text-2xl font-extrabold">Payment</h2>
          <p className="mt-2 text-sm text-slate-600">Missing order id.</p>
          <div className="mt-6">
            <Link to="/">
              <button className="candy-btn w-full">Back to shop</button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="mx-auto max-w-xl p-6">
        <div className="candy-card p-6">
          <h2 className="text-2xl font-extrabold">Payment</h2>
          <p className="mt-2 text-sm text-slate-600">Order not found.</p>
          <div className="mt-6">
            <Link to="/">
              <button className="candy-btn w-full">Back to shop</button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl p-6">
      <div className="candy-card p-6 space-y-4">
        <h2 className="text-2xl font-extrabold">Payment</h2>

        <div className="rounded-2xl bg-white/60 p-4 space-y-3">
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
            <div className="text-xl font-extrabold">
              {Number(order.total).toFixed(2)}
            </div>
          </div>
        </div>

        {/* NEW: Address + Phone */}
        <div className="rounded-2xl bg-white/60 p-4 space-y-3">
          <div>
            <label className="text-sm font-bold text-slate-700">
              Shipping address
            </label>
            <textarea
              className="candy-input mt-2 w-full"
              rows={3}
              placeholder="Street, Ward, District, City…"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              disabled={paying}
            />
          </div>

          <div>
            <label className="text-sm font-bold text-slate-700">
              Phone number
            </label>
            <input
              className="candy-input mt-2 w-full"
              placeholder="e.g. 0901234567 or +84901234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={paying}
            />
            <p className="mt-1 text-xs text-slate-500">
              Accepts 9–15 digits (can start with +).
            </p>
          </div>
        </div>

        {isPayable ? (
          <button
            className="candy-btn w-full"
            disabled={paying}
            onClick={handlePay}
          >
            {paying ? "Processing…" : "Pay Now"}
          </button>
        ) : (
          <div className="rounded-2xl bg-emerald-50 p-4 text-emerald-700 font-extrabold">
            Order not in CREATED status ✅
          </div>
        )}

        <div className="flex gap-2">
          <Link to="/">
            <button className="candy-btn-outline w-full">Back to shop</button>
          </Link>

          <button
            className="candy-btn-outline w-full"
            onClick={() => loadOrder(orderId)}
            disabled={paying}
          >
            Refresh
          </button>
        </div>

        <p className="text-xs text-slate-500">
          Tip: Payment history is available at <code>/payments</code>.
        </p>
      </div>
    </div>
  );
}