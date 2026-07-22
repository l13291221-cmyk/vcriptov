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

    const badge = document.getElementById("dataBadge");
    if (badge) {
      const ex = (d.market_exchange || "exchange").toUpperCase();
      if (d.data_source === "live") {
        badge.textContent = "● DATI LIVE " + ex;
        badge.className = "data-badge data-live";
      } else {
        badge.textContent = "○ dati offline (nessuna connessione a " + ex + ")";
        badge.className = "data-badge data-offline";
      }
    }
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

  async function refreshAccount() {
    const panel = document.getElementById("accountPanel");
    if (!panel) return;
    let d;
    try { d = await getJSON("/api/account"); } catch (e) { return; }
    const badge = document.getElementById("accountBadge");
    const body = document.getElementById("accountBody");
    if (!d.connected) {
      badge.textContent = "non collegato";
      badge.className = "data-badge data-offline";
      return;
    }
    badge.textContent = d.live_trading ? "● collegato · TRADING REALE ON" : "● collegato (sola lettura)";
    badge.className = "data-badge data-live";
    const bal = Object.entries(d.balances || {})
      .map(([a, v]) => `<div class="price-row"><span class="price-sym">${a}</span><span class="price-val"><div class="p">${(+v).toLocaleString("it-IT", { maximumFractionDigits: 8 })}</div></span></div>`)
      .join("") || '<div class="empty">Saldo vuoto</div>';
    const tr = (d.trades || []).slice(0, 15).map((t) => `<tr>
      <td>${(t.symbol || "").replace("/USDT", "")}</td>
      <td><span class="tag ${t.side === 'buy' ? 'tag-long' : 'tag-closed'}">${(t.side || "").toUpperCase()}</span></td>
      <td>${t.amount ?? "—"}</td>
      <td>${t.price ?? "—"}</td>
      <td>${t.cost ?? "—"}</td>
      <td class="hint">${t.time ? new Date(t.time).toLocaleString("it-IT") : "—"}</td>
    </tr>`).join("");
    body.innerHTML = `
      <div class="grid-2">
        <div><h3 style="font-size:14px;color:var(--muted);">Saldo</h3><div class="price-list">${bal}</div></div>
        <div><h3 style="font-size:14px;color:var(--muted);">Operazioni reali</h3>
          <div style="overflow-x:auto;"><table>
            <thead><tr><th>Crypto</th><th>Lato</th><th>Qtà</th><th>Prezzo</th><th>Costo</th><th>Quando</th></tr></thead>
            <tbody>${tr || '<tr><td colspan="6" class="empty">Nessuna operazione</td></tr>'}</tbody>
          </table></div>
        </div>
      </div>`;
  }

  async function refreshSignals() {
    const body = document.getElementById("signalsBody");
    if (!body) return;
    let rows;
    try { rows = await getJSON("/api/signals"); } catch (e) { return; }
    if (!rows.length) { body.innerHTML = '<tr><td colspan="6" class="empty">Nessun segnale ancora</td></tr>'; return; }
    body.innerHTML = rows.map((r) => `<tr>
      <td><strong>${r.symbol.replace("/USDT", "")}</strong></td>
      <td><span class="tag tag-long">${r.side.toUpperCase()}</span></td>
      <td>$${(+r.ref_price).toLocaleString("it-IT", { maximumFractionDigits: 4 })}</td>
      <td class="hint">${r.sl}% / ${r.tp}%</td>
      <td><span class="tag tag-${r.status}">${r.status}</span>${r.result ? ' <span class="hint">' + r.result + '</span>' : ''}</td>
      <td class="hint">${r.created_at ? new Date(r.created_at).toLocaleString("it-IT") : "—"}</td>
    </tr>`).join("");
  }

  async function refreshAll() {
    try {
      await Promise.all([
        refreshOverview(), refreshEquity(), refreshPrices(),
        refreshPositions(), refreshTrades(), refreshAccount(), refreshSignals(),
      ]);
    } catch (e) {
      console.warn("refresh error", e);
    }
  }

  refreshAll();
  setInterval(refreshAll, 5000); // la UI si aggiorna ogni 5s; il bot lavora ogni 30s
})();
