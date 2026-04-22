import { useEffect, useState } from "react";
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
  Tooltip,
);

function Dashboard() {
  const [realtime, setRealtime] = useState([]);
  const [daily, setDaily] = useState([]);
  const [hover, setHover] = useState(false);

  // ================= REALTIME =================
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

  // ================= DAILY =================
  useEffect(() => {
    fetch("http://127.0.0.1:8000/stats")
      .then((r) => r.json())
      .then((j) => setDaily(j))
      .catch(() => setDaily([]));
  }, []);

  // ambil data terakhir buat card
  const latest = realtime[realtime.length - 1] || {};

  // ================= CHART =================
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

  const dailyData = {
    labels: daily.map((d) => new Date(d.date).toLocaleDateString()),
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
      {/* HEADER */}
      <div style={header}>
        <h1>📊 Dashboard CCTV</h1>

        <Link to="/cctv" style={{ textDecoration: "none" }}>
          <button
            style={{
              ...btn,
              transform: hover ? "scale(1.05)" : "scale(1)",
              boxShadow: hover
                ? "0 6px 20px rgba(34,197,94,0.6)"
                : "0 4px 12px rgba(34,197,94,0.3)",
              outline: "none",
            }}
            onMouseEnter={() => setHover(true)}
            onMouseLeave={() => setHover(false)}
          >
            📷 Live CCTV
          </button>
        </Link>
      </div>

      {/* STAT CARDS */}
      <div style={cardContainer}>
        <Stat title="IN" value={latest.in} color="#22c55e" icon="⬆️" />
        <Stat title="OUT" value={latest.out} color="#ef4444" icon="⬇️" />
        <Stat title="HELMET" value={latest.helmet} color="#3b82f6" icon="🪖" />
        <Stat
          title="NO HELMET"
          value={latest.no_helmet}
          color="#facc15"
          icon="⚠️"
        />
      </div>

      {/* REALTIME */}
      <div style={card}>
        <h2>Realtime Monitoring</h2>
        {realtime.length === 0 ? (
          <p>Menunggu data...</p>
        ) : (
          <Line data={realtimeData} />
        )}
      </div>

      {/* DAILY */}
      <div style={card}>
        <h2>Statistik Harian</h2>
        {daily.length === 0 ? <p>Belum ada data</p> : <Line data={dailyData} />}
      </div>
    </div>
  );
}

// COMPONENT CARD KECIL
function Stat({ title, value, color, icon }) {
  const [hover, setHover] = useState(false);

  const handleClick = () => {
    console.log("klik");
  };

  return (
    <button
      onClick={handleClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        ...statCard,

        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",

        border: "none",
        background: "transparent",
        cursor: "pointer",
        outline: "none",

        transform: hover ? "translateY(-5px)" : "translateY(0)",
        boxShadow: hover
          ? `0 10px 25px ${color}55`
          : "0 4px 12px rgba(0,0,0,0.3)",
      }}
    >
      {/* ICON */}
      <div
        style={{
          fontSize: "30px",
          color: color,
        }}
      >
        {icon}
      </div>

      {/* TITLE */}
      <h3 style={{ color, marginTop: "10px" }}>{title}</h3>

      {/* VALUE */}
      <h1
        style={{
          margin: "5px 0",
          color: "#fff",
          textShadow:
            "0 0 10px rgba(255,255,255,0.8), 0 0 20px rgba(255,255,255,0.6)",
          transition: "all 0.3s ease",
        }}
      >
        {value || 0}
      </h1>

      {/* LINE */}
      <div
        style={{
          height: "4px",
          width: "100%",
          background: color,
          borderRadius: "10px",
          marginTop: "10px",
          opacity: 0.7,
        }}
      />
    </button>
  );
}

Stat.propTypes = {
  title: PropTypes.string.isRequired,
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
};

const header = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "30px",
};

const cardContainer = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
  gap: "20px",
  marginBottom: "30px",
};

const statCard = {
  background: "linear-gradient(145deg, #0f172a, #020617)",
  padding: "20px",
  borderRadius: "16px",
  textAlign: "center",
  transition: "0.3s",
  cursor: "pointer",
  border: "1px solid rgba(255,255,255,0.05)",
};

const card = {
  background: "#0f172a",
  padding: "20px",
  borderRadius: "12px",
  marginBottom: "20px",
};

const btn = {
  padding: "10px 18px",
  background: "linear-gradient(135deg, #22c55e, #16a34a)",
  border: "none",
  borderRadius: "10px",
  color: "white",
  cursor: "pointer",
  fontWeight: "bold",
  display: "flex",
  alignItems: "center",
  gap: "8px",
  boxShadow: "0 4px 12px rgba(34,197,94,0.3)",
  transition: "all 0.3s ease",
};

export default Dashboard;
