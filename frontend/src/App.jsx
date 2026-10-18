import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";

// Route-level chunks keep the first screen light, while every original route remains available.
const Home = lazy(() => import("./pages/Home.jsx"));
const Verify = lazy(() => import("./pages/Verify.jsx"));
const Plot = lazy(() => import("./pages/Plot.jsx"));
const Register = lazy(() => import("./pages/Register.jsx"));
const Flagged = lazy(() => import("./pages/Flagged.jsx"));
const Admin = lazy(() => import("./pages/Admin.jsx"));

function PageLoading() {
  return <div className="page-loading" role="status"><span className="spinner"><span className="dot" /></span><span>Loading JomiProman…</span></div>;
}

export default function App() {
  return (
    <Suspense fallback={<PageLoading />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="verify" element={<Verify />} />
          <Route path="plot" element={<Plot />} />
          <Route path="register" element={<Register />} />
          <Route path="flagged" element={<Flagged />} />
          <Route path="admin" element={<Admin />} />
          <Route path="*" element={<Home />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
