import React from "react";
import {
  LayoutDashboard,
  Activity,
  Bell,
  History,
  BarChart2,
  Info
} from "lucide-react";

const Sidebar = ({ currentPage, setCurrentPage }) => {

  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "marketoverview", label: "Market Overview", icon: BarChart2 }, // ✅ FIXED
    { id: "backtest", label: "Backtests", icon: Activity },
    { id: "alerts", label: "Alerts", icon: Bell },
    { id: "history", label: "History", icon: History },
    { id: "about", label: "About", icon: Info },
  ];

  return (
    <div style={{
      width: 230,
      height: "100vh",
      background: "linear-gradient(180deg, #0b0f19, #0f172a)",
      padding: "20px 12px",
      display: "flex",
      flexDirection: "column",
      justifyContent: "space-between",
    }}>

      {/* LOGO */}
      <div>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 30,
          padding: "0 10px"
        }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #6366f1, #22c55e)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}>
            <BarChart2 size={18} color="white" />
          </div>

          <h2 style={{ fontSize: "1.2rem", fontWeight: 700 }}>
            Stock<span style={{ color: "#22c55e" }}>AI</span>
          </h2>
        </div>

        {/* NAV */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {navItems.map(item => {
            const Icon = item.icon;
            const active =
              currentPage === item.id ||
              (item.id === "dashboard" && currentPage === "predictions");

            return (
              <div
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "10px 14px",
                  borderRadius: 10,
                  cursor: "pointer",
                  background: active ? "rgba(99,102,241,0.2)" : "transparent",
                  color: active ? "#fff" : "#9ca3af",
                }}
              >
                <Icon size={18} color={active ? "#6366f1" : "#9ca3af"} />
                <span style={{ fontWeight: active ? 600 : 400 }}>
                  {item.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* FOOTER */}
      <div style={{
        padding: "12px",
        borderRadius: 10,
        background: "rgba(34,197,94,0.1)",
        border: "1px solid rgba(34,197,94,0.3)",
        textAlign: "center"
      }}>
        <div style={{ fontSize: "0.8rem", color: "#22c55e", fontWeight: 600 }}>
          ● System Active
        </div>
        <div style={{ fontSize: "0.7rem", color: "#9ca3af", marginTop: 4 }}>
          AI Engine Running
        </div>
      </div>

    </div>
  );
};

export default Sidebar;