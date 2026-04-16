import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function CCTV() {
  const CAMERA_NAME = "Camera 01";
  const CAMERA_URL = encodeURIComponent(CAMERA_NAME);

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
      <h1 style={{ textAlign: "center" }}>📷 CCTV</h1>

      <div style={{ textAlign: "center", marginBottom: "20px" }}>
        <Link to="/">
          <button style={btn}>⬅ Ke Grafik</button>
        </Link>
      </div>

      {/* CCTV */}
      <div style={{ display: "flex", justifyContent: "center" }}>
        <img
          src={`http://127.0.0.1:8000/stream/${CAMERA_URL}`}
          alt="CCTV"
          style={{ width: "900px", borderRadius: "12px" }}
        />
      </div>

      {/* CONTROL BOX */}
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

      {/* DATA BOX */}
      <div style={boxContainer}>
        <div style={box}>
          IN<h1>{data.in}</h1>
        </div>
        <div style={box}>
          OUT<h1>{data.out}</h1>
        </div>
        <div style={box}>
          HELMET<h1>{data.helmet}</h1>
        </div>
        <div style={box}>
          NO HELMET<h1>{data.no_helmet}</h1>
        </div>
      </div>
    </div>
  );
}

// =============================
const wrapper = {
  minHeight: "100vh",
  background: "#020617",
  color: "white",
  padding: "30px",
};

const controlBox = {
  position: "fixed",
  bottom: "20px",
  right: "20px",
  background: "#0f172a",
  padding: "15px",
  borderRadius: "12px",
};

const directionBtn = {
  padding: "8px",
  background: "#22c55e",
  border: "none",
  borderRadius: "8px",
  color: "white",
  cursor: "pointer",
};

const boxContainer = {
  display: "flex",
  justifyContent: "center",
  gap: "20px",
  marginTop: "30px",
};

const box = {
  padding: "20px",
  width: "150px",
  textAlign: "center",
  background: "#0f172a",
  borderRadius: "12px",
};

const btn = {
  padding: "10px 20px",
  background: "#3b82f6",
  border: "none",
  borderRadius: "8px",
  color: "white",
};

export default CCTV;