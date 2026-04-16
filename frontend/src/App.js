import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import CCTV from "./pages/CCTV";

function App() {
  return (
    <BrowserRouter>
      <div style={{ background: "#607aee", minHeight: "100vh" }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cctv" element={<CCTV />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;