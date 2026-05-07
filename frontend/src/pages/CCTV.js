import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

// =============================
// COMPONENT: CAMERA CARD
// =============================
function CameraCard({ cam }) {
  const CAM_URL = encodeURIComponent(cam.name);

  const [line, setLine] = useState(50);
  const [direction, setDirection] = useState("NORMAL");

  // ambil config awal
  useEffect(() => {
    fetch(`http://127.0.0.1:8000/line/${CAM_URL}`)
      .then((r) => r.json())
      .then((j) => setLine((j.position || 0.5) * 100))
      .catch(() => {});

    fetch(`http://127.0.0.1:8000/direction/${CAM_URL}`)
      .then((r) => r.json())
      .then((j) => setDirection(j.mode || "NORMAL"))
      .catch(() => {});
  }, [CAM_URL]);

  return (
    <div style={videoContainer}>
      <h4 style={{ marginBottom: "10px" }}>{cam.name}</h4>

      <img
  src={`http://127.0.0.1:8000/stream/${encodeURIComponent(cam.name)}`}
  alt={cam.name}
  style={video}
/>

      {/* CONTROL */}
      <div style={controlBox}>
        <p style={{ marginBottom: "5px" }}>Line Position</p>

        <input
          type="range"
          min="0"
          max="100"
          value={line}
          onChange={(e) => {
            const val = Number(e.target.value);
            setLine(val);

            fetch(`http://127.0.0.1:8000/line/${CAM_URL}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                position: val / 100,
              }),
            }).catch(() => {});
          }}
        />

        <p>{line}%</p>

        <button
          style={directionBtn}
          onClick={() => {
            const newDir = direction === "NORMAL" ? "REVERSE" : "NORMAL";

            setDirection(newDir);

            fetch(`http://127.0.0.1:8000/direction/${CAM_URL}`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ mode: newDir }),
            }).catch(() => {});
          }}
        >
          {direction}
        </button>
      </div>
    </div>
  );
}

CameraCard.propTypes = {
  cam: PropTypes.object.isRequired,
};

// =============================
// MAIN PAGE
// =============================
function CCTV() {
  const [hoverBtn, setHoverBtn] = useState(false);
  const [cameras, setCameras] = useState([]);

  const [data, setData] = useState({
    in: 0,
    out: 0,
    helmet: 0,
    no_helmet: 0,
  });

  // ambil list kamera
  useEffect(() => {
    fetch("http://127.0.0.1:8000/cameras")
      .then((res) => res.json())
      .then((data) => setCameras(data))
      .catch(() => {});
  }, []);

  // summary global
  useEffect(() => {
    const t = setInterval(() => {
      fetch("http://127.0.0.1:8000/summary")
        .then((r) => r.json())
        .then((j) => {
          setData({
            in: j.total_in || 0,
            out: j.total_out || 0,
            helmet: j.total_helmet || 0,
            no_helmet: j.total_no_helmet || 0,
          });
        })
        .catch(() => {});
    }, 2000);

    return () => clearInterval(t);
  }, []);

  return (
    <div style={wrapper}>
      {/* HEADER */}
      <div style={header}>
        <Link to="/">
          <button
            style={{
              ...btn,
              transform: hoverBtn ? "translateY(-2px)" : "translateY(0)",
              boxShadow: hoverBtn ? "0 8px 20px rgba(59,130,246,0.4)" : "none",
              transition: "0.2s",
            }}
            onMouseEnter={() => setHoverBtn(true)}
            onMouseLeave={() => setHoverBtn(false)}
          >
            ⬅ Dashboard
          </button>
        </Link>

        <h1 style={titleCenter}>CCTV Monitoring</h1>
      </div>

      {/* MULTI CAMERA */}
      <div style={grid}>
        {cameras.map((cam) => (
          <CameraCard key={cam.name} cam={cam} />
        ))}
      </div>

      {/* DATA */}
      <div style={boxContainer}>
        <Stat title="IN" value={data.in} />
        <Stat title="OUT" value={data.out} />
        <Stat title="HELMET" value={data.helmet} />
        <Stat title="NO HELMET" value={data.no_helmet} />
      </div>
    </div>
  );
}

// =============================
function Stat({ title, value }) {
  const getColor = () => {
    if (title === "IN") return "#22c55e";
    if (title === "OUT") return "#3b82f6";
    if (title === "HELMET") return "#eab308";
    if (title === "NO HELMET") return "#ef4444";
    return "white";
  };

  return (
    <div style={statBox}>
      <p style={statTitle}>{title}</p>
      <h2 style={{ ...statValue, color: getColor() }}>{value}</h2>
    </div>
  );
}

Stat.propTypes = {
  title: PropTypes.string.isRequired,
  value: PropTypes.number.isRequired,
};

// =============================
// STYLE
// =============================
const wrapper = {
  minHeight: "100vh",
  background: "radial-gradient(circle at top, #0f172a, #020617)",
  color: "white",
  padding: "30px",
};

const header = {
  position: "relative",
  display: "flex",
  alignItems: "center",
  marginBottom: "20px",
};

const titleCenter = {
  position: "absolute",
  left: "50%",
  transform: "translateX(-50%)",
  margin: 0,
  fontSize: "22px",
  fontWeight: "bold",
};

const grid = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
  gap: "20px",
};

const videoContainer = {
  background: "#020617",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #1e293b",
  
};

const video = {
  width: "100%",
  maxWidth: "800px",
  aspectRatio: "16/9",
  objectFit: "cover",
  borderRadius: "8px",
  margin: "0 auto", // 🔥 tambahan penting
  display: "block",
};

const controlBox = {
  marginTop: "10px",
  background: "#020617",
  padding: "15px",
  borderRadius: "10px",
  border: "1px solid #1e293b",
};

const directionBtn = {
  marginTop: "10px",
  padding: "8px",
  background: "#3b82f6",
  border: "none",
  borderRadius: "6px",
  color: "white",
  cursor: "pointer",
  width: "100%",
};

const boxContainer = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "20px",
  marginTop: "40px",
};

const statBox = {
  background: "#020617",
  padding: "25px",
  borderRadius: "12px",
  border: "1px solid #1e293b",
  textAlign: "center",
};

const statTitle = {
  fontSize: "12px",
  color: "#94a3b8",
  marginBottom: "5px",
};

const statValue = {
  fontSize: "32px",
  fontWeight: "bold",
  marginTop: "10px",
};

const btn = {
  padding: "10px 20px",
  background: "#3b82f6",
  border: "none",
  borderRadius: "8px",
  color: "white",
  cursor: "pointer",
};

export default CCTV;
