import { useEffect, useState, useMemo } from "react";
import { Line } from "react-chartjs-2";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

import {
  Chart as ChartJS,
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Legend,
  Tooltip,
} from "chart.js";

ChartJS.register(
  LineElement,
  CategoryScale,
  LinearScale,
  PointElement,
  Legend,
  Tooltip
);

function Dashboard() {
  const [realtime, setRealtime] = useState([]);
  const [daily, setDaily] = useState([]);
  const [hover, setHover] = useState(false);

  // ✅ TAMBAHAN (KUNCI)
  const [summary, setSummary] = useState({
    total_in: 0,
    total_out: 0,
    total_helmet: 0,
    total_no_helmet: 0,
  });

  useEffect(() => {
  const fetchAll = () => {
    fetch("http://127.0.0.1:8000/realtime")
      .then(r => r.json())
      .then(j => {
        console.log("🔥 REALTIME DARI BACKEND:", j);
        setRealtime(Array.isArray(j) ? j : []);
      })
      .catch(err => {
        console.log("❌ ERROR FETCH REALTIME:", err);
        setRealtime([]);
      });

    fetch("http://127.0.0.1:8000/stats")
      .then(r => r.json())
      .then(j => {
        console.log("🔥 DAILY DARI BACKEND:", j);
        setDaily(Array.isArray(j) ? j : []);
      })
      .catch(err => {
        console.log("❌ ERROR FETCH DAILY:", err);
        setDaily([]);
      });

    fetch("http://127.0.0.1:8000/summary")
      .then(r => r.json())
      .then(j => {
        console.log("🔥 SUMMARY DARI BACKEND:", j);
        setSummary(j);
      })
      .catch(err => {
        console.log("❌ ERROR FETCH SUMMARY:", err);
      });
  };

  fetchAll(); // initial load

  const interval = setInterval(fetchAll, 500); // 0.5 detik sync

  return () => clearInterval(interval);
}, []);

  const safeDaily = Array.isArray(daily) ? daily : [];


  // ================= CHART =================
  const realtimeData = useMemo(() => ({
  labels: realtime.map(d =>
    new Date(d.time).toLocaleTimeString()
  ),
 datasets: [
  {
    label: "IN",
    data: realtime.map(d => d.in),
    borderColor: "#22c55e",
    tension: 0.4,
  },
  {
    label: "OUT",
    data: realtime.map(d => d.out),
    borderColor: "#ef4444",
    tension: 0.4,
  },
  {
    label: "HELMET",
    data: realtime.map(d => d.helmet),
    borderColor: "#3b82f6",
    tension: 0.4,
  },
  {
    label: "NO HELMET",
    data: realtime.map(d => d.no_helmet),
    borderColor: "#facc15",
    tension: 0.4,
  },
]
}), [realtime]);

  const dailyData = {
  labels: safeDaily.map((d) =>
    new Date(d.date).toLocaleDateString()
  ),
  datasets: [
    {
      label: "IN",
      data: safeDaily.map((d) => d.in),
      borderColor: "#22c55e",
      backgroundColor: "#22c55e",
      tension: 0.4,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: false,
    },
    {
      label: "OUT",
      data: safeDaily.map((d) => d.out),
      borderColor: "#ef4444",
      backgroundColor: "#ef4444",
      tension: 0.4,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: false,
    },
    {
      label: "HELMET",
      data: safeDaily.map((d) => d.helmet),
      borderColor: "#3b82f6",
      backgroundColor: "#3b82f6",
      tension: 0.4,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: false,
    },
    {
      label: "NO HELMET",
      data: safeDaily.map((d) => d.no_helmet),
      borderColor: "#facc15",
      backgroundColor: "#facc15",
      tension: 0.4,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: false,
    },
  ],
};

  const options = {
  responsive: true,
  plugins: {
    legend: {
      labels: { color: "#fff" },
    },
  },
  scales: {
    x: {
      ticks: { color: "#94a3b8" },
      grid: { color: "#1e293b" },
    },
    y: {
      ticks: { color: "#94a3b8" },
      grid: { color: "#1e293b" },
    },
  },
};

  return (
    <div style={wrapper}>
      <div style={header}>
        <div style={headerInner}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1>Dashboard CCTV</h1>
          </div>

          <Link to="/cctv" style={{ marginLeft: "auto" }}>
            <button
              style={{
                ...btn,
                transform: hover ? "scale(1.05)" : "scale(1)",
              }}
              onMouseEnter={() => setHover(true)}
              onMouseLeave={() => setHover(false)}
            >
              📷 Live CCTV
            </button>
          </Link>
        </div>
      </div>

      {/* ✅ FIX UTAMA */}
      <div style={cardContainer}>
        <Stat title="IN" value={summary.total_in} color="#22c55e" icon="⬆️" />
        <Stat title="OUT" value={summary.total_out} color="#ef4444" icon="⬇️" />
        <Stat title="HELMET" value={summary.total_helmet} color="#3b82f6" icon="🪖" />
        <Stat title="NO HELMET" value={summary.total_no_helmet} color="#facc15" icon="⚠️" />
      </div>

      <div style={card}>
  <h2>Realtime Monitoring Today</h2>
  <Line
  key="realtime-chart"
  data={realtimeData}
  options={options}
/>
</div>

    <div style={card}>
  <h2>Statistik Harian</h2>
  <Line data={dailyData} options={options} />
</div>
    </div>
  );
}

// ================= STAT =================
function Stat({ title, value, color, icon }) {
  return (
    <div style={{ ...statCard, borderColor: color }}>
      <div style={{ fontSize: "28px" }}>{icon}</div>
      <h3 style={{ color }}>{title}</h3>
      <h1>{value || 0}</h1>
    </div>
  );
}

Stat.propTypes = {
  title: PropTypes.string,
  value: PropTypes.number,
  color: PropTypes.string,
  icon: PropTypes.node,
};

// ================= STYLE =================
const wrapper = {
  minHeight: "100vh",
  background: "#020617",
  color: "white",
  padding: "30px",
  paddingTop: "120px",
};

const header = {
  position: "fixed",
  top: 0,
  width: "100%",
  background: "#020617",
  borderBottom: "1px solid #1e293b",
};

const headerInner = {
  display: "flex",
  alignItems: "center",
  padding: "10px 30px",
};

const cardContainer = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
  gap: "20px",
  marginBottom: "30px",
};

const statCard = {
  background: "#0f172a",
  padding: "20px",
  borderRadius: "12px",
  textAlign: "center",
};

const card = {
  background: "#0f172a",
  padding: "20px",
  borderRadius: "12px",
  marginBottom: "20px",
};

const btn = {
  padding: "10px 18px",
  background: "#22c55e",
  border: "none",
  borderRadius: "8px",
  color: "white",
  cursor: "pointer",
};

export default Dashboard;