<div className="grid-container">
  {filteredSignals?.map(stock => (
    <div
      key={stock.ticker}
      className="card"
      onClick={() => handleCardClick(stock)}
      style={{
        cursor: "pointer",
        transition: "all 0.2s ease",
        borderRadius: "14px"
      }}
      onMouseEnter={(e)=> {
        e.currentTarget.style.transform="translateY(-4px)";
        e.currentTarget.style.boxShadow="0 8px 20px rgba(0,0,0,0.2)";
      }}
      onMouseLeave={(e)=> {
        e.currentTarget.style.transform="translateY(0)";
        e.currentTarget.style.boxShadow="none";
      }}
    >

      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3>{stock.ticker}</h3>

        <span style={{
          color: getSignalColor(stock.signal),
          fontWeight: "bold",
          fontSize: "0.9rem"
        }}>
          {stock.signal}
        </span>
      </div>

      {/* PRICE */}
      <h2 style={{ margin: "12px 0", fontSize: "1.6rem" }}>
        ₹{stock.price?.toFixed(2)}
      </h2>

      {/* METRICS */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        marginBottom: 8
      }}>
        <div>
          <small style={{ color: "var(--text-muted)" }}>Conf</small>
          <div>{stock.confidence_pct}%</div>
        </div>

        <div>
          <small style={{ color: "var(--text-muted)" }}>Acc</small>
          <div>{(stock.accuracy * 100).toFixed(1)}%</div>
        </div>
      </div>

      {/* PROGRESS BAR */}
      <div style={{
        display: "flex",
        height: 6,
        borderRadius: 6,
        overflow: "hidden"
      }}>
        <div style={{
          width: `${(stock.probabilities?.BUY || 0) * 100}%`,
          background: "var(--signal-buy)"
        }} />
        <div style={{
          width: `${(stock.probabilities?.HOLD || 0) * 100}%`,
          background: "var(--signal-hold)"
        }} />
        <div style={{
          width: `${(stock.probabilities?.SELL || 0) * 100}%`,
          background: "var(--signal-sell)"
        }} />
      </div>

    </div>
  ))}
</div>