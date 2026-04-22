import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PropTypes from "prop-types";

function CCTV() {
  const CAMERA_NAME = "Camera 01";
  const CAMERA_URL = encodeURIComponent(CAMERA_NAME);
  const [hoverBtn, setHoverBtn] = useState(false);

  const [data, setData] = useState({
    in: 0,
    out: 0,
    helmet: 0,
    no_helmet: 0,
  });

  const [linePosition, setLinePosition] = useState(50);
  const [direction, setDirection] = useState("NORMAL");

  // =============================
  // FETCH COUNTER (REALTIME)
  // =============================
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

  // =============================
  // FETCH CONFIG AWAL (SYNC)
  // =============================
  useEffect(() => {
    // line
    fetch(`http://127.0.0.1:8000/line/${CAMERA_URL}`)
      .then((r) => r.json())
      .then((j) => {
        setLinePosition((j.position || 0.5) * 100);
      })
      .catch(() => {});

    // direction
    fetch(`http://127.0.0.1:8000/direction/${CAMERA_URL}`)
      .then((r) => r.json())
      .then((j) => {
        setDirection(j.mode || "NORMAL");
      })
      .catch(() => {});
  }, []);

  // =============================
  // SEND LINE (DEBOUNCE)
  // =============================
  useEffect(() => {
    const timeout = setTimeout(() => {
      fetch(`http://127.0.0.1:8000/line/${CAMERA_URL}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          position: linePosition / 100,
        }),
      }).catch(() => {});
    }, 200);

    return () => clearTimeout(timeout);
  }, [linePosition]);

  // =============================
  // HANDLE DIRECTION (INSTANT)
  // =============================
  const toggleDirection = () => {
    const newDir = direction === "NORMAL" ? "REVERSE" : "NORMAL";

    setDirection(newDir);

    fetch(`http://127.0.0.1:8000/direction/${CAMERA_URL}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        mode: newDir,
      }),
    }).catch(() => {});
  };

  return (
    <div style={wrapper}>
      <div style={header}>
        {/* tombol kiri */}
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

        {/* judul tengah */}
        <h1 style={titleCenter}>CCTV Monitoring</h1>
      </div>

      {/* CCTV + CONTROL */}
      <div style={mainContent}>
        {/* CCTV */}
        <div style={videoContainer}>
          <img
            src={`http://127.0.0.1:8000/stream/${CAMERA_URL}`}
            alt="CCTV"
            style={video}
          />
        </div>

        {/* CONTROL */}
        <div style={controlBox}>
          <h4>Line Position</h4>

          <input
            type="range"
            min="0"
            max="100"
            value={linePosition}
            onChange={(e) => setLinePosition(Number(e.target.value))}
          />

          <p>{linePosition}%</p>

          <button style={directionBtn} onClick={toggleDirection}>
            {direction}
          </button>
        </div>
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

const videoContainer = {
  background: "#020617",
  padding: "10px",
  borderRadius: "12px",
  border: "1px solid #1e293b",
  width: "100%",
  maxWidth: "1200px",
};

const video = {
  width: "100%",
  maxWidth: "900  px",
  borderRadius: "8px",
};

const controlBox = {
  background: "#020617",
  padding: "20px",
  borderRadius: "12px",
  border: "1px solid #1e293b",
  minWidth: "250px",
};

const directionBtn = {
  marginTop: "10px",
  padding: "8px",
  background: "#3b82f6",
  border: "none",
  borderRadius: "6px",
  color: "white",
  cursor: "pointer",
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

const mainContent = {
  display: "flex",
  justifyContent: "center",
  alignItems: "flex-start",
  gap: "30px",
  flexWrap: "wrap",
};

export default CCTV;
