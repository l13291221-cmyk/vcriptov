// Dashboard live. Regola chiave: se il conto Kraken NON è collegato, non
// mostriamo numeri inventati — lasciamo vuoto ("—") e invitiamo a collegarlo.
// I prezzi di mercato in alto sono invece dati reali e restano sempre visibili.
(function () {
  const eur = (n) => (n >= 0 ? "" : "-") + "$" + Math.abs(n).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const cls = (n) => (n > 0 ? "pos" : n < 0 ? "neg" : "");
  const sign = (n) => (n > 0 ? "+" : "") + n.toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const STABLES = new Set(["USDT", "USD", "USDC", "EUR", "DAI", "ZUSD", "ZEUR", "BUSD", "TUSD"]);

  // ----- Grafico equity (altezza fissa dal CSS) -----
  const ctx = document.getElementById("equityChart").getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 240);
  grad.addColorStop(0, "rgba(79,140,255,.35)");
  grad.addColorStop(1, "rgba(79,140,255,0)");
  const equityChart = new Chart(ctx, {
    type: "line",
    data: { labels: [], datasets: [{ label: "Saldo (USDT)", data: [], borderColor: "#4f8cff", backgroundColor: grad, borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0 }] },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8a97b1", maxTicksLimit: 8 }, grid: { display: false } },
        y: { ticks: { color: "#8a97b1" }, grid: { color: "rgba(37,48,73,.5)" } },
      },
    },
  });
  const equitySeries = [];  // andamento reale accumulato nella sessione

  async function getJSON(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(url + " -> " + r.status);
    return r.json();
  }

  function priceMap(prices) {
    const m = {};
    (prices || []).forEach((r) => { m[r.symbol.replace("/USDT", "")] = r.price; });
    return m;
  }

  function computeEquity(balances, pmap) {
    let total = 0;
    for (const [asset, amount] of Object.entries(balances || {})) {
      const a = +amount;
      if (!a) continue;
      if (STABLES.has(asset)) total += a;
      else if (pmap[asset]) total += a * pmap[asset];
    }
    return total;
  }

  // ---- KPI ----
  function setKpi(id, text, klass) {
    const el = document.getElementById(id);
    if (el) { el.textContent = text; if (klass !== undefined) el.className = klass; }
  }

  function blankKPIs() {
    setKpi("kpi-equity", "—", "value");
    setKpi("kpi-equity-sub", "Collega Kraken", "sub");
    setKpi("kpi-pnl", "—", "value");
    setKpi("kpi-pnl-pct", "Collega Kraken", "sub");
    setKpi("kpi-cash", "—", "value");
    setKpi("kpi-invested", "—");
    setKpi("kpi-open", "—", "value");
    setKpi("kpi-winrate", "—");
  }

  function realKPIs(account, pmap) {
    const balances = account.balances || {};
    const equity = computeEquity(balances, pmap);
    const cash = Object.entries(balances).filter(([a]) => STABLES.has(a)).reduce((s, [, v]) => s + (+v), 0);
    const assets = Object.entries(balances).filter(([, v]) => +v > 0).length;
    setKpi("kpi-equity", eur(equity), "value");
    setKpi("kpi-equity-sub", "Saldo reale del tuo Kraken", "sub");
    setKpi("kpi-pnl", "—", "value");
    setKpi("kpi-pnl-pct", "Profitto/perdita: storico in arrivo", "sub");
    setKpi("kpi-cash", eur(cash), "value");
    setKpi("kpi-invested", eur(Math.max(0, equity - cash)));
    setKpi("kpi-open", assets, "value");
    setKpi("kpi-winrate", "asset nel conto");
    return equity;
  }

  // ---- Grafico ----
  function showChart(show) {
    document.querySelector(".chart-box").style.display = show ? "block" : "none";
    document.getElementById("equityPlaceholder").style.display = show ? "none" : "block";
  }

  function pushEquity(equity) {
    equitySeries.push({ t: new Date().toLocaleTimeString("it-IT"), v: equity });
    if (equitySeries.length > 120) equitySeries.shift();
    equityChart.data.labels = equitySeries.map((p) => p.t);
    equityChart.data.datasets[0].data = equitySeries.map((p) => p.v);
    equityChart.update("none");
  }

  // ---- Tabelle ----
  function emptyTable(id, cols, text) {
    const b = document.getElementById(id);
    if (b) b.innerHTML = `<tr><td colspan="${cols}" class="empty">${text}</td></tr>`;
  }

  function realTradesTable(account) {
    const body = document.getElementById("tradesBody");
    const rows = account.trades || [];
    if (!rows.length) { emptyTable("tradesBody", 7, "Nessuna operazione sul tuo conto"); return; }
    body.innerHTML = rows.slice(0, 30).map((t) => `<tr>
      <td><strong>${(t.symbol || "").replace("/USDT", "")}</strong></td>
      <td><span class="tag ${t.side === "buy" ? "tag-long" : "tag-closed"}">${(t.side || "").toUpperCase()}</span></td>
      <td>${t.amount ?? "—"}</td>
      <td>${t.price ?? "—"}</td>
      <td>${t.cost ?? "—"}</td>
      <td>${t.fee ?? "—"}</td>
      <td class="hint">${t.time ? new Date(t.time).toLocaleString("it-IT") : "—"}</td>
    </tr>`).join("");
  }

  // ---- Prezzi di mercato (sempre reali) ----
  function renderPrices(rows) {
    const el = document.getElementById("priceList");
    if (!el) return;
    if (!rows || !rows.length) { el.innerHTML = '<div class="empty">Caricamento…</div>'; return; }
    el.innerHTML = rows.map((r) => {
      const hasCh = r.change !== null && r.change !== undefined;
      const c = hasCh ? cls(r.change) : "";
      const chTxt = hasCh ? sign(r.change) + "% <span class='hint'>24h</span>" : "—";
      return `<div class="price-row">
        <span class="price-sym">${r.symbol.replace("/USDT", "")}<span class="hint">/USDT</span></span>
        <span class="price-val">
          <div class="p">$${r.price.toLocaleString("it-IT", { maximumFractionDigits: 4 })}</div>
          <div class="c ${c}">${chTxt}</div>
        </span>
      </div>`;
    }).join("");
  }

  function renderDataBadge(overview) {
    const badge = document.getElementById("dataBadge");
    if (!badge || !overview) return;
    const ex = (overview.market_exchange || "exchange").toUpperCase();
    if (overview.data_source === "live") {
      badge.textContent = "● DATI LIVE " + ex; badge.className = "data-badge data-live";
    } else {
      badge.textContent = "○ dati offline"; badge.className = "data-badge data-offline";
    }
  }

  // ---- Pannello Conto Kraken reale ----
  function renderAccountPanel(account) {
    const panel = document.getElementById("accountPanel");
    if (!panel) return;
    const badge = document.getElementById("accountBadge");
    const body = document.getElementById("accountBody");
    if (!account.connected) {
      badge.textContent = "non collegato"; badge.className = "data-badge data-offline";
      body.innerHTML = '<div class="empty">Collega Kraken e attiva il trading reale nelle Impostazioni per vedere qui saldo e operazioni vere.</div>';
      return;
    }
    badge.textContent = account.live_trading ? "● collegato · TRADING REALE ON" : "● collegato (sola lettura)";
    badge.className = "data-badge data-live";
    const bal = Object.entries(account.balances || {}).filter(([, v]) => +v > 0)
      .map(([a, v]) => `<div class="price-row"><span class="price-sym">${a}</span><span class="price-val"><div class="p">${(+v).toLocaleString("it-IT", { maximumFractionDigits: 8 })}</div></span></div>`)
      .join("") || '<div class="empty">Saldo vuoto</div>';
    body.innerHTML = `<div><h3 style="font-size:14px;color:var(--muted);">Saldo</h3><div class="price-list">${bal}</div></div>`;
  }

  async function renderSignals() {
    const body = document.getElementById("signalsBody");
    if (!body) return;
    let rows;
    try { rows = await getJSON("/api/signals"); } catch (e) { return; }
    if (!rows.length) { emptyTable("signalsBody", 6, "Nessun segnale ancora"); return; }
    body.innerHTML = rows.map((r) => `<tr>
      <td><strong>${r.symbol.replace("/USDT", "")}</strong></td>
      <td><span class="tag tag-long">${r.side.toUpperCase()}</span></td>
      <td>$${(+r.ref_price).toLocaleString("it-IT", { maximumFractionDigits: 4 })}</td>
      <td class="hint">${r.sl}% / ${r.tp}%</td>
      <td><span class="tag tag-${r.status}">${r.status}</span>${r.result ? ' <span class="hint">' + r.result + "</span>" : ""}</td>
      <td class="hint">${r.created_at ? new Date(r.created_at).toLocaleString("it-IT") : "—"}</td>
    </tr>`).join("");
  }

  let lastPrices = [];
  let lastAccount = null;

  function applyAccount(account) {
    renderAccountPanel(account);
    const connected = account && account.connected;
    document.getElementById("connectHint").style.display = connected ? "none" : "block";
    const liveLbl = document.getElementById("equity-live");
    if (connected) {
      const equity = realKPIs(account, priceMap(lastPrices));
      showChart(true);
      pushEquity(equity);
      realTradesTable(account);
      emptyTable("positionsBody", 6, "Per lo spot il saldo è nel pannello “Conto Kraken reale”.");
      if (liveLbl) liveLbl.textContent = "conto reale";
    } else {
      blankKPIs();
      showChart(false);
      emptyTable("positionsBody", 6, "Collega il tuo Kraken per vedere le tue posizioni reali.");
      emptyTable("tradesBody", 7, "Collega il tuo Kraken per vedere le tue operazioni reali.");
      if (liveLbl) liveLbl.textContent = "";
    }
  }

  function refreshAll() {
    // Prezzi, badge e segnali: veloci → mostrati SUBITO, senza aspettare Kraken.
    getJSON("/api/prices").then((p) => {
      lastPrices = p; renderPrices(p);
      if (lastAccount) applyAccount(lastAccount);  // ricalcola KPI con prezzi freschi
    }).catch(() => {});
    getJSON("/api/overview").then(renderDataBadge).catch(() => {});
    renderSignals();
    // Conto Kraken: può essere più lento → aggiornato appena pronto, a parte.
    getJSON("/api/account").then((acc) => { lastAccount = acc; applyAccount(acc); })
      .catch(() => {});
  }

  // Stato iniziale immediato: niente numeri finti finché il conto non risponde.
  blankKPIs();
  showChart(false);
  refreshAll();
  setInterval(refreshAll, 5000);
})();
