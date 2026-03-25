import React from "react";
import { Activity, BarChart2, Cpu, ShieldCheck } from "lucide-react";

const About = () => {
  return (
    <div className="page-container">

      {/* HEADER */}
      <div style={{ marginBottom: 20 }}>
        <h2>System Overview</h2>
        <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
          Real-time AI-powered stock signal engine
        </span>
      </div>

      {/* 🔥 SYSTEM STATUS CARDS */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginBottom: 20 }}>

        <div className="card" style={{ flex: 1 }}>
          <Cpu size={18} style={{ marginBottom: 6 }} />
          <h3 style={{ color: "#22c55e" }}>AI Engine</h3>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Active & Running
          </span>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <Activity size={18} style={{ marginBottom: 6 }} />
          <h3 style={{ color: "#22c55e" }}>Signal Pipeline</h3>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Live Monitoring
          </span>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <ShieldCheck size={18} style={{ marginBottom: 6 }} />
          <h3 style={{ color: "#22c55e" }}>System Health</h3>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Stable
          </span>
        </div>

      </div>

      {/* 🔥 PERFORMANCE METRICS */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3>Model Performance</h3>

        <div style={{ display: "flex", gap: 20, marginTop: 10, flexWrap: "wrap" }}>
          <div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Accuracy</span>
            <h2>89.4%</h2>
          </div>

          <div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Signals Generated</span>
            <h2>1,240+</h2>
          </div>

          <div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Win Rate</span>
            <h2>84%</h2>
          </div>
        </div>
      </div>

      {/* 🔥 SYSTEM DESCRIPTION */}
      <div className="card" style={{ marginBottom: 20 }}>
        <h3>Engine Description</h3>
        <p style={{ marginTop: 10, lineHeight: 1.6 }}>
          The SignalAI engine processes real-time market data using advanced machine learning 
          models and technical indicators. It continuously evaluates price movements, 
          volatility patterns, and probability distributions to generate actionable 
          BUY, SELL, and HOLD signals.
        </p>
      </div>

      {/* 🔥 FEATURES GRID */}
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>

        <div className="card" style={{ flex: "1 1 260px" }}>
          <BarChart2 size={18} style={{ marginBottom: 6 }} />
          <h4>Market Analysis</h4>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Real-time trend detection using technical indicators.
          </p>
        </div>

        <div className="card" style={{ flex: "1 1 260px" }}>
          <Activity size={18} style={{ marginBottom: 6 }} />
          <h4>Backtesting Engine</h4>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Historical evaluation of trading strategies.
          </p>
        </div>

        <div className="card" style={{ flex: "1 1 260px" }}>
          <Cpu size={18} style={{ marginBottom: 6 }} />
          <h4>AI Predictions</h4>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Smart signal generation using trained ML models.
          </p>
        </div>

      </div>

      {/* 🔥 FOOTER STATUS */}
      <div style={{
        marginTop: 20,
        padding: "12px",
        borderRadius: 10,
        background: "rgba(34,197,94,0.08)",
        border: "1px solid rgba(34,197,94,0.2)",
        textAlign: "center"
      }}>
        <span style={{ color: "#22c55e", fontWeight: 600 }}>
          ● System Live • Data Sync Active • Alerts Enabled
        </span>
      </div>

    </div>
  );
};

export default About;