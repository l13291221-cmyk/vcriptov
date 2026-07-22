// Dashboard live: interroga le API JSON del backend e aggiorna KPI, grafico e tabelle.
(function () {
  const eur = (n) => (n >= 0 ? "" : "-") + "$" + Math.abs(n).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const cls = (n) => (n > 0 ? "pos" : n < 0 ? "neg" : "");
  const sign = (n) => (n > 0 ? "+" : "") + n.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  // ----- Grafico equity -----
  const ctx = document.getElementById("equityChart").getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 240);
  grad.addColorStop(0, "rgba(79,140,255,.35)");
  grad.addColorStop(1, "rgba(79,140,255,0)");

  const equityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [{
        label: "Equity (USDT)",
        data: [],
        borderColor: "#4f8cff",
        backgroundColor: grad,
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8a97b1", maxTicksLimit: 8 }, grid: { display: false } },
        y: { ticks: { color: "#8a97b1" }, grid: { color: "rgba(37,48,73,.5)" } },
      },
    },
  });

  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + " -> " + r.status);
    return r.json();
  }

  async function refreshOverview() {
    const d = await getJSON("/api/overview");
    document.getElementById("kpi-equity").textContent = eur(d.equity);
    document.getElementById("kpi-equity-sub").textContent = "Capitale iniziale: " + eur(d.starting_equity);

    const pnlEl = document.getElementById("kpi-pnl");
    pnlEl.textContent = sign(d.total_pnl);
    pnlEl.className = "value " + cls(d.total_pnl);
    const pctEl = document.getElementById("kpi-pnl-pct");
    pctEl.textContent = sign(d.total_pnl_pct) + "%  (realizzato " + sign(d.realized_pnl) + ")";
    pctEl.className = "sub " + cls(d.total_pnl);

    document.getElementById("kpi-cash").textContent = eur(d.cash);
    document.getElementById("kpi-invested").textContent = eur(d.positions_value);
    document.getElementById("kpi-open").textContent = d.open_positions;
    document.getElementById("kpi-winrate").textContent = d.win_rate + "% (" + d.closed_trades + " chiuse)";
  }

  async function refreshEquity() {
    const d = await getJSON("/api/equity");
    equityChart.data.labels = d.labels;
    equityChart.data.datasets[0].data = d.values;
    equityChart.update("none");
  }

  async function refreshPrices() {
    const rows = await getJSON("/api/prices");
    const el = document.getElementById("priceList");
    if (!rows.length) { el.innerHTML = '<div class="empty">Nessun simbolo</div>'; return; }
    el.innerHTML = rows.map((r) => {
      const c = cls(r.change);
      return `<div class="price-row">
        <span class="price-sym">${r.symbol.replace("/USDT", "")}<span class="hint">/USDT</span></span>
        <span class="price-val">
          <div class="p">$${r.price.toLocaleString("it-IT", { maximumFractionDigits: 4 })}</div>
          <div class="c ${c}">${sign(r.change)}%</div>
        </span>
      </div>`;
    }).join("");
  }

  async function refreshPositions() {
    const rows = await getJSON("/api/positions");
    const body = document.getElementById("positionsBody");
    if (!rows.length) { body.innerHTML = '<tr><td colspan="6" class="empty">Nessuna posizione aperta</td></tr>'; return; }
    body.innerHTML = rows.map((t) => `<tr>
      <td><strong>${t.symbol.replace("/USDT", "")}</strong></td>
      <td><span class="tag tag-long">LONG</span></td>
      <td>${t.qty}</td>
      <td>$${t.entry_price.toLocaleString("it-IT", { maximumFractionDigits: 4 })}</td>
      <td>$${(t.current_price || 0).toLocaleString("it-IT", { maximumFractionDigits: 4 })}</td>
      <td class="${cls(t.pnl)}">${sign(t.pnl)}</td>
    </tr>`).join("");
  }

  async function refreshTrades() {
    const rows = await getJSON("/api/trades");
    const body = document.getElementById("tradesBody");
    if (!rows.length) { body.innerHTML = '<tr><td colspan="7" class="empty">Nessuna operazione chiusa</td></tr>'; return; }
    body.innerHTML = rows.map((t) => `<tr>
      <td><strong>${t.symbol.replace("/USDT", "")}</strong></td>
      <td><span class="tag tag-long">LONG</span></td>
      <td>${t.qty}</td>
      <td>$${t.entry_price.toLocaleString("it-IT", { maximumFractionDigits: 4 })}</td>
      <td>$${(t.exit_price || 0).toLocaleString("it-IT", { maximumFractionDigits: 4 })}</td>
      <td class="${cls(t.pnl)}">${sign(t.pnl)}</td>
      <td class="hint">${t.closed_at ? new Date(t.closed_at).toLocaleTimeString("it-IT") : "—"}</td>
    </tr>`).join("");
  }

  async function refreshAll() {
    try {
      await Promise.all([
        refreshOverview(), refreshEquity(), refreshPrices(),
        refreshPositions(), refreshTrades(),
      ]);
    } catch (e) {
      console.warn("refresh error", e);
    }
  }

  refreshAll();
  setInterval(refreshAll, 5000); // la UI si aggiorna ogni 5s; il bot lavora ogni 30s
})();
