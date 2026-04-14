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

  // FETCH COUNTER
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
      <h1 style={{ textAlign: "center" }}>📷 CCTV</h1>

      <div style={{ textAlign: "center", marginBottom: "20px" }}>
        <Link to="/">
          <button style={btn}>⬅ Ke Grafik</button>
        </Link>
      </div>

      {/* CCTV */}
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          marginBottom: "30px",
        }}
      >
        <img
          src={`http://127.0.0.1:8000/stream/${CAMERA_URL}`}
          alt="CCTV"
          style={{
            width: "900px",
            borderRadius: "12px",
          }}
        />
      </div>

      {/* BOX DI BAWAH CCTV */}
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

// STYLE
const wrapper = {
  minHeight: "100vh",
  background: "#020617",
  color: "white",
  padding: "30px",
};

const boxContainer = {
  display: "flex",
  justifyContent: "center",
  gap: "20px",
  flexWrap: "wrap",
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
  cursor: "pointer",
};

export default CCTV;
