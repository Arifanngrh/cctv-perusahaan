import { useEffect, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale);

function App() {

  const CAMERA_NAME = "Camera 01";
  const CAMERA_URL = encodeURIComponent(CAMERA_NAME);

  const [data, setData] = useState({
    in: 0,
    out: 0,
    helmet: 0,
    no_helmet: 0
  });

  const [linePosition, setLinePosition] = useState(0.5);
  const [direction, setDirection] = useState("NORMAL");
  const [notif, setNotif] = useState("");

  // ======================
  // FETCH COUNTER
  // ======================
  useEffect(() => {

    const t = setInterval(() => {

      fetch("http://127.0.0.1:8000/summary")
        .then(r => r.json())
        .then(j => {

          setData({
            in: j.total_in || 0,
            out: j.total_out || 0,
            helmet: j.total_helmet || 0,
            no_helmet: j.total_no_helmet || 0
          });

        })
        .catch(()=>{});

    }, 1000);

    return () => clearInterval(t);

  }, []);

  // ======================
  // LOAD SETTINGS
  // ======================
  useEffect(() => {

    fetch(`http://127.0.0.1:8000/line/${CAMERA_URL}`)
      .then(r => r.json())
      .then(j => setLinePosition(j.position || 0.5))
      .catch(()=>{});

    fetch(`http://127.0.0.1:8000/direction/${CAMERA_URL}`)
      .then(r => r.json())
      .then(j => setDirection(j.mode || "NORMAL"))
      .catch(()=>{});

  }, []);

  // ======================
  // NOTIFICATION
  // ======================
  const showNotif = (mode) => {

    let text = "";

    if (mode === "NORMAL") {
      text = "✔ NORMAL\nIN : B → A\nOUT : A → B";
    }

    if (mode === "REVERSE") {
      text = "✔ REVERSE\nIN : A → B\nOUT : B → A";
    }

    setNotif(text);

    setTimeout(() => setNotif(""), 3000);
  };

  // ======================
  // UPDATE LINE
  // ======================
  const updateLine = (value) => {

    setLinePosition(value);

    fetch(`http://127.0.0.1:8000/line/${CAMERA_URL}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ position: value })
    }).catch(()=>{});
  };

  // ======================
  // TOGGLE DIRECTION
  // ======================
  const toggleDirection = () => {

    const newMode = direction === "NORMAL" ? "REVERSE" : "NORMAL";

    setDirection(newMode);

    fetch(`http://127.0.0.1:8000/direction/${CAMERA_URL}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: newMode })
    }).catch(()=>{});

    showNotif(newMode);
  };

  // ======================
  // CHART DATA
  // ======================
  const chartData = {
    labels: ["IN", "OUT", "HELMET", "NO HELMET"],
    datasets: [
      {
        label: "Statistik",
        data: [
          data.in,
          data.out,
          data.helmet,
          data.no_helmet
        ]
      }
    ]
  };

  // ======================
  // HELMET PERCENTAGE
  // ======================
  const totalHelm = data.helmet + data.no_helmet;
  const persenHelm = totalHelm > 0
    ? ((data.helmet / totalHelm) * 100).toFixed(1)
    : 0;

  return (
    <div style={{ background: "#020617", minHeight: "100vh", color: "white", padding: "30px" }}>

      <h1 style={{ textAlign: "center" }}>🔥 CCTV AI Dashboard</h1>

      {/* NOTIF */}
      {notif && (
        <div style={{
          position: "fixed",
          top: "20px",
          right: "20px",
          background: "#22c55e",
          padding: "15px 25px",
          borderRadius: "10px",
          whiteSpace: "pre-line",
          fontWeight: "bold"
        }}>
          {notif}
        </div>
      )}

      {/* STREAM */}
      <div style={{ display: "flex", justifyContent: "center", margin: "20px" }}>
        <img
          src={`http://127.0.0.1:8000/stream/${CAMERA_URL}`}
          alt="CCTV"
          style={{
            width: "900px",
            border: "3px solid #0ea5e9",
            borderRadius: "12px"
          }}
        />
      </div>

      {/* CONTROL */}
      <div style={{ textAlign: "center" }}>

        <h3>Line Position</h3>

        <input
          type="range"
          min="0.1"
          max="0.9"
          step="0.01"
          value={linePosition}
          onChange={(e) => updateLine(parseFloat(e.target.value))}
          style={{ width: "60%" }}
        />

        <p>{(linePosition * 100).toFixed(0)}%</p>

        <button
          onClick={toggleDirection}
          style={{
            padding: "10px 20px",
            background: direction === "NORMAL" ? "#22c55e" : "#ef4444",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            color: "white"
          }}
        >
          Direction: {direction}
        </button>

      </div>

      {/* COUNTER */}
      <div style={{ display: "flex", justifyContent: "center", gap: "20px", marginTop: "30px", flexWrap: "wrap" }}>
        <div style={box}>IN<h1>{data.in}</h1></div>
        <div style={box}>OUT<h1>{data.out}</h1></div>
        <div style={box}>HELMET<h1>{data.helmet}</h1></div>
        <div style={box}>NO HELMET<h1>{data.no_helmet}</h1></div>
        <div style={box}>✔ {persenHelm}% SAFE</div>
      </div>

      {/* CHART */}
      <div style={{ width: "70%", margin: "40px auto" }}>
        <Bar data={chartData} />
      </div>

    </div>
  );
}

const box = {
  border: "2px solid #0ea5e9",
  padding: "20px",
  width: "150px",
  textAlign: "center",
  borderRadius: "10px"
};

export default App;