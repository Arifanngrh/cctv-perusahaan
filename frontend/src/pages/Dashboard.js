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
  Tooltip
);

function Dashboard() {
  const [realtime, setRealtime] = useState([]);
  const [daily, setDaily] = useState([]);

  // =========================
  // REALTIME
  // =========================
  useEffect(() => {
    const interval = setInterval(() => {
      fetch("http://127.0.0.1:8000/summary")
        .then((r) => r.json())
        .then((j) => {
          const now = new Date().toLocaleTimeString();

          setRealtime((prev) => {
            const newData = [
              ...prev,
              {
                time: now,
                in: j.total_in || 0,
                out: j.total_out || 0,
                helmet: j.total_helmet || 0,
                no_helmet: j.total_no_helmet || 0,
              },
            ];

            return newData.slice(-20);
          });
        })
        .catch(() => {});
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // =========================
  // DAILY (DATABASE)
  // =========================
  useEffect(() => {
    fetch("http://127.0.0.1:8000/stats")
      .then((r) => r.json())
      .then((j) => setDaily(j))
      .catch(() => setDaily([]));
  }, []);

  // =========================
  // CHART REALTIME
  // =========================
  const realtimeData = {
    labels: realtime.map((d) => d.time),
    datasets: [
      {
        label: "IN",
        data: realtime.map((d) => d.in),
        borderColor: "#22c55e",
        tension: 0.3,
      },
      {
        label: "OUT",
        data: realtime.map((d) => d.out),
        borderColor: "#ef4444",
        tension: 0.3,
      },
      {
        label: "HELMET",
        data: realtime.map((d) => d.helmet),
        borderColor: "#3b82f6",
        tension: 0.3,
      },
      {
        label: "NO HELMET",
        data: realtime.map((d) => d.no_helmet),
        borderColor: "#facc15",
        tension: 0.3,
      },
    ],
  };

  // =========================
  // CHART DAILY
  // =========================
  const dailyData = {
    labels: daily.map((d) =>
      new Date(d.date).toLocaleDateString()
    ),
    datasets: [
      {
        label: "IN",
        data: daily.map((d) => d.in),
        borderColor: "#22c55e",
        tension: 0.3,
      },
      {
        label: "OUT",
        data: daily.map((d) => d.out),
        borderColor: "#ef4444",
        tension: 0.3,
      },
    ],
  };

  return (
    <div style={wrapper}>
      <h1 style={{ textAlign: "center" }}>📊 Dashboard CCTV</h1>

      <div style={{ textAlign: "center", marginBottom: "20px" }}>
        <Link to="/cctv">
          <button style={btn}>📷 Ke CCTV</button>
        </Link>
      </div>

      {/* REALTIME */}
      <h2>Realtime</h2>
      <div style={card}>
        {realtime.length === 0 ? (
          <p style={{ textAlign: "center" }}>Menunggu data...</p>
        ) : (
          <Line data={realtimeData} />
        )}
      </div>

      {/* DAILY */}
      <h2 style={{ marginTop: "30px" }}>Per Hari</h2>
      <div style={card}>
        {daily.length === 0 ? (
          <p style={{ textAlign: "center" }}>Belum ada data</p>
        ) : (
          <Line data={dailyData} />
        )}
      </div>
    </div>
  );
}

// STYLE
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
  marginBottom: "20px",
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