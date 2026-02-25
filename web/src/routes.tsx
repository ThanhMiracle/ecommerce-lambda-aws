import { Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Verify from "./pages/Verify";
import Cart from "./pages/Cart";
import AdminProducts from "./pages/AdminProducts";

import Payment from "./pages/Payment";     // single pay page
import Payments from "./pages/Payments";   // history page (plural)

import OrderDetails from "./pages/OrderDetails";

export default function AppRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/admin/products" element={<AdminProducts />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify" element={<Verify />} />

        <Route path="/orders/:orderId" element={<OrderDetails />} />

        {/* payment flow */}
        <Route path="/payment/:orderId" element={<Payment />} />
        <Route path="/payments" element={<Payments />} />

        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Layout>
  );
}