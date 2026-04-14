import { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import { Link } from "react-router-dom";

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
  Tooltip,
);

function Dashboard() {
  const [stats, setStats] = useState([]);

  useEffect(() => {
    fetch("http://127.0.0.1:5000/api/stats")
      .then((r) => r.json())
      .then((j) => setStats(Array.isArray(j) ? j : []))
      .catch(() => setStats([]));
  }, []);

  const labels = stats.map((d) => new Date(d.date).toLocaleDateString());

  const chartData = {
    labels,
    datasets: [
      {
        label: "IN",
        data: stats.map((d) => d.in),
        borderColor: "#22c55e",
        fill: false,
        tension: 0.3,
      },
      {
        label: "OUT",
        data: stats.map((d) => d.out),
        borderColor: "#ef4444",
        fill: false,
        tension: 0.3,
      },
    ],
  };

  return (
    <div style={wrapper}>
      <h1 style={{ textAlign: "center" }}>📊 Grafik</h1>

      <div style={{ textAlign: "center", marginBottom: "20px" }}>
        <Link to="/cctv">
          <button style={btn}>📷 Ke CCTV</button>
        </Link>
      </div>

      <div style={card}>
        {stats.length === 0 ? (
          <p style={{ textAlign: "center" }}>Tidak ada data</p>
        ) : (
          <Line data={chartData} />
        )}
      </div>
    </div>
  );
}

const wrapper = {
  minHeight: "100vh",
  background: "#020617",
  color: "white",
  padding: "30px",
};

const card = {
  padding: "20px",
  background: "#0f172a",
  borderRadius: "12px",
};

const btn = {
  padding: "10px 20px",
  background: "#22c55e",
  border: "none",
  borderRadius: "8px",
  color: "white",
  cursor: "pointer",
};

export default Dashboard;
