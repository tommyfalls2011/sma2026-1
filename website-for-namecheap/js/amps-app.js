// SMA Amp Configurator — Standalone App Logic
// API_BASE for backend calls (inquiry, checkout, admin)
const AMP_API = '';

let selectedConfig = AMP_CONFIGS[1]; // default 2-pill
let selectedTransistor = '2SC2879';
let voltageMode = '13.8';
let isAdmin = false;
let showSpecs = false;
let showInquiry = false;
let showPayment = false;

function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function tierClass(tier) {
  if (tier === 'premium') return 'tier-premium';
  if (tier === 'economy') return 'tier-economy';
  return 'tier-standard';
}
function tierLabel(tier) {
  if (tier === 'premium') return 'Premium';
  if (tier === 'economy') return 'Economy';
  return 'Standard';
}

// ──── Render Config Cards ────
function renderConfigs() {
  const el = document.getElementById('config-grid');
  el.innerHTML = AMP_CONFIGS.map(c => {
    const active = selectedConfig && selectedConfig.id === c.id;
    return `<div class="card${active ? ' active' : ''}" data-config="${c.id}" onclick="selectConfig('${c.id}')">
      <div class="card-top"><span class="card-name">${esc(c.name)}</span><span class="pill-badge">${c.pills} pill${c.pills > 1 ? 's' : ''}</span></div>
      <p class="card-desc">${esc(c.description)}</p>
      <div class="card-bottom"><span class="card-price">$${c.basePrice}</span><span class="card-type">${esc(c.type)}</span></div>
    </div>`;
  }).join('');
}

function selectConfig(id) {
  selectedConfig = AMP_CONFIGS.find(c => c.id === id);
  renderConfigs();
  renderSpecs();
  renderPowerRef();
}

// ──── Render Transistor Cards ────
function renderTransistors() {
  const el = document.getElementById('transistor-grid');
  el.innerHTML = Object.entries(TRANSISTORS).map(([id, t]) => {
    const active = selectedTransistor === id;
    const s = t.specs;
    return `<div class="card${active ? ' active' : ''}" onclick="selectTransistor('${id}')">
      <div class="card-top"><span class="t-name">${esc(t.name)}</span><span class="tier-badge ${tierClass(t.tier)}">${tierLabel(t.tier)}</span></div>
      <div><span class="t-watts">${t.wattsPerPill}</span><span class="t-unit">W/pill</span></div>
      <div style="margin-top:4px"><span class="t-cost">$${t.costPerPill}</span><span class="t-cost-unit">/pill</span>${t.costPerPillUsed ? `<span class="t-used">($${t.costPerPillUsed} used)</span>` : ''}</div>
      ${s ? `<div class="t-mini-specs"><span>${s.maxVce}V max</span><span>${s.powerDissipation}W Pd</span><span>${s.maxIc}A Ic</span></div>` : ''}
    </div>`;
  }).join('');
}

function selectTransistor(id) {
  selectedTransistor = id;
  renderTransistors();
  renderSpecs();
  renderSpecSheets();
  renderPowerRef();
  renderWindingRatios();
  renderTuning();
}

// ──── Render Voltage ────
function renderVoltage() {
  const el = document.getElementById('voltage-grid');
  const t = TRANSISTORS[selectedTransistor];
  el.innerHTML = VOLTAGE_MODES.map(v => {
    const active = voltageMode === v.id;
    const vp = t && t.voltagePerformance && t.voltagePerformance[v.id];
    const rs = vp ? RISK_STYLES[vp.risk] : null;
    return `<div class="v-card" onclick="selectVoltage('${v.id}')" style="background:${active ? v.color + '10' : 'var(--card)'};border-color:${active ? v.color : 'var(--border)'}">
      <div class="v-top">
        <span class="v-label" style="color:${active ? v.color : '#fff'}">${v.label}</span>
        ${rs ? `<span style="font-size:10px;padding:2px 8px;border-radius:2px;background:${rs.bg};color:${rs.color}">${rs.label}</span>` : ''}
      </div>
      <span class="v-sub">${v.sublabel}</span>
    </div>`;
  }).join('');
}

function selectVoltage(id) {
  voltageMode = id;
  renderVoltage();
  renderSpecs();
  renderPowerRef();
  renderWindingRatios();
  renderTuning();
}

// ──── Render Live Specs ────
function renderSpecs() {
  const el = document.getElementById('specs-section');
  const t = TRANSISTORS[selectedTransistor];
  if (!selectedConfig || !t) { el.innerHTML = ''; return; }

  const vp = t.voltagePerformance && t.voltagePerformance[voltageMode];
  const destroyed = vp && vp.carrierW === null;
  const power = destroyed ? 0 : calcPower(selectedConfig, t, voltageMode);
  const pep = destroyed ? 0 : calcPEP(selectedConfig, t, voltageMode);
  const price = calcPrice(selectedConfig, t);
  const amps = destroyed ? 0 : calcCurrentDraw(power, voltageMode);
  const heat = destroyed ? 0 : calcHeatDissipation(power);
  const risk = vp ? vp.risk : 'low';
  const inputRatio = vp ? vp.inputRatio : '-';
  const outputRatio = vp ? vp.outputRatio : '-';

  const stepNum = isAdmin ? 4 : 3;
  let html = `<div class="step-header"><span class="step-num">${stepNum}</span><div><p class="step-label">Your Build</p><h2 class="step-title">${esc(selectedConfig.name)} with ${esc(selectedTransistor)} @ ${voltageMode}V</h2></div></div>`;

  // Destroy warning
  if (isAdmin && destroyed) {
    html += `<div class="warning" style="background:rgba(239,68,68,0.12);border-color:#ef4444">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      <div><p class="warning-title" style="color:#ef4444">WILL DESTROY TRANSISTORS</p><p class="warning-text">${voltageMode}V exceeds the absolute maximum Vce (${t.specs.maxVce}V) for ${selectedTransistor}.</p></div>
    </div>`;
    el.innerHTML = html;
    return;
  }

  // Risk warning
  if (isAdmin && (risk === 'high' || risk === 'medium-high')) {
    const rs = RISK_STYLES[risk];
    html += `<div class="warning" style="background:${rs.bg};border-color:${rs.color}">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${rs.color}" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
      <div><p class="warning-title" style="color:${rs.color}">${rs.label}</p><p class="warning-text">${t.hvNotes || ''}</p></div>
    </div>`;
  }

  // Spec cards
  html += `<div class="grid-specs${isAdmin ? ' admin' : ''}">`;
  html += specCard('Zap', isAdmin ? 'Carrier Output' : 'RF Output', power, 'watts', 'var(--brand)');
  if (isAdmin) html += specCard('Activity', 'PEP Output', pep, 'watts', 'var(--brandLight)');
  html += specCard('DollarSign', 'Estimated Price', '$' + price, '', 'var(--green)');
  html += specCard('Gauge', 'Current Draw', amps, 'amps @ ' + voltageMode + 'V', 'var(--brand)');
  html += specCard('Thermometer', 'Heat Dissipation', heat, 'watts', 'var(--red)');
  html += '</div>';

  // Admin: ratios
  if (isAdmin) {
    html += `<div class="ratio-grid"><div class="ratio-card"><div class="ratio-label">Input Transformer Ratio</div><div class="ratio-value">${esc(inputRatio)}</div></div><div class="ratio-card"><div class="ratio-label">Output Transformer Ratio</div><div class="ratio-value">${esc(outputRatio)}</div></div></div>`;
  }

  // Admin: cost breakdown
  if (isAdmin) {
    html += `<div class="cost-box">
      <div class="cost-header"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg> Cost Breakdown <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="var(--textDim)" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
      <div class="cost-row"><span class="label">Base (labor/parts/chassis)</span><span class="value">$${selectedConfig.basePrice}</span></div>
      <div class="cost-row"><span class="label">${selectedConfig.pills}x ${selectedTransistor} @ $${t.costPerPill}/pill</span><span class="value">$${(selectedConfig.pills * t.costPerPill).toFixed(2)}</span></div>
      ${t.costPerPillUsed ? `<div class="cost-row dim"><span class="label">(used option: ${selectedConfig.pills}x @ $${t.costPerPillUsed}/pill)</span><span class="value">$${(selectedConfig.pills * t.costPerPillUsed).toFixed(2)}</span></div>` : ''}
      <div class="cost-row"><span class="label">Shipping (${t.source})</span><span class="value">$${t.shippingFlat}</span></div>
      <div class="cost-row total"><span class="label">Total</span><span class="value">$${price}</span></div>
    </div>`;
  }

  // Summary bar
  html += `<div class="summary-bar" style="margin-top:16px">
    <div class="summary-row">
      <span><strong>${selectedConfig.pills}</strong> pill${selectedConfig.pills > 1 ? 's' : ''}</span><span class="summary-sep">|</span>
      <span><strong>${esc(selectedConfig.type)}</strong> config</span><span class="summary-sep">|</span>
      <span><strong>${esc(selectedTransistor)}</strong> transistors</span><span class="summary-sep">|</span>
      <span><strong>${voltageMode}V</strong> DC</span><span class="summary-sep">|</span>
      <span>~${Math.round(power / selectedConfig.pills)}W per pill</span>
    </div>
    <div class="summary-buttons">
      <button class="btn btn-brand" onclick="openPayment()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg> Pay 50% Deposit ($${Math.round(price / 2)})</button>
      <button class="btn btn-green" onclick="openPayment()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg> Buy Now $${price}</button>
      <button class="btn btn-outline" onclick="openInquiry()"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Get a Quote</button>
      <a href="#" class="track-link">Track an Order &rarr;</a>
    </div>
  </div>`;

  el.innerHTML = html;
}

function specCard(icon, label, value, unit, color) {
  const svgMap = {
    Zap: '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>',
    Activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    DollarSign: '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    Gauge: '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9"/>',
    Thermometer: '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>',
  };
  return `<div class="spec-card">
    <div class="spec-card-label"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${svgMap[icon] || ''}</svg><span>${esc(label)}</span></div>
    <div><span class="spec-card-value" style="color:${color}">${value}</span><span class="spec-card-unit">${unit}</span></div>
  </div>`;
}

// ──── Spec Sheets ────
function renderSpecSheets() {
  const el = document.getElementById('spec-sheets');
  el.innerHTML = Object.entries(TRANSISTORS).map(([id, t]) => {
    const s = t.specs;
    if (!s) return '';
    const rows = [
      ['Type', s.type], ['Manufacturer', s.manufacturer], ['Package', s.package], ['Frequency Range', s.freqRange],
      ['Max Vce (Collector-Emitter)', s.maxVce + ' V'], ['Max Vcb (Collector-Base)', s.maxVcb + ' V'], ['Max Veb (Emitter-Base)', s.maxVeb + ' V'],
      ['Max Collector Current (Ic)', s.maxIc + ' A'], ['Power Dissipation (Pd)', s.powerDissipation + ' W'],
      ['DC Current Gain (hFE)', s.hfeMax ? s.hfeMin + '–' + s.hfeMax + ' (' + s.hfeCondition + ')' : s.hfeMin + ' min (' + s.hfeCondition + ')'],
      ['Transition Frequency (fT)', s.fT + ' MHz'], ['Output Power', s.outputPower + ' W (' + s.outputCondition + ')'],
      ['Power Gain', s.powerGain + ' dB'], ['Efficiency', s.efficiency + '%'],
    ];
    if (s.cob) rows.push(['Output Capacitance (Cob)', s.cob + ' pF (' + s.cobCondition + ')']);
    if (s.thermalResistance) rows.push(['Thermal Resistance (Rjc)', s.thermalResistance + ' °C/W']);
    rows.push(['Max Junction Temp (Tj)', s.tjMax + ' °C']);
    return `<div class="spec-sheet"><div class="spec-sheet-header"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2" ry="2"/><rect x="9" y="9" width="6" height="6"/></svg><span class="name">${esc(t.name)}</span><span class="sub">— Full Specifications</span></div>
      ${rows.map(r => `<div class="spec-sheet-row"><span class="k">${r[0]}</span><span class="v">${r[1]}</span></div>`).join('')}
      ${s.notes ? `<div class="spec-sheet-notes">${esc(s.notes)}</div>` : ''}
    </div>`;
  }).join('');
}

function toggleSpecs() {
  showSpecs = !showSpecs;
  document.getElementById('spec-sheets').classList.toggle('hidden', !showSpecs);
  document.getElementById('specs-toggle-text').textContent = showSpecs ? 'Hide Full Specs' : 'Show Full Specs';
}

// ──── Power Reference Table ────
function renderPowerRef() {
  const tIds = Object.keys(TRANSISTORS);
  let html = `<div class="step-header"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg><h2 class="step-title">RF Power Quick Reference <span style="font-size:14px;font-weight:400;color:var(--textMuted)">@ ${voltageMode}V</span></h2></div>`;
  html += '<div class="table-wrap"><table class="data-table"><thead><tr><th style="text-align:left">Config</th>';
  tIds.forEach(id => { html += `<th style="font-family:monospace">${id}</th>`; });
  html += '</tr></thead><tbody>';
  AMP_CONFIGS.forEach(config => {
    html += '<tr>';
    html += `<td style="font-weight:500;color:#fff;white-space:nowrap">${esc(config.name)}</td>`;
    tIds.forEach(id => {
      const t = TRANSISTORS[id];
      const vp = t.voltagePerformance && t.voltagePerformance[voltageMode];
      const destroyed = vp && vp.carrierW === null;
      const pw = destroyed ? null : calcPower(config, t, voltageMode);
      const isSel = selectedConfig && selectedConfig.id === config.id && selectedTransistor === id;
      html += `<td style="color:${destroyed ? 'var(--red)' : isSel ? 'var(--brand)' : 'var(--textMuted)'};font-weight:${isSel ? 700 : 400}">${destroyed ? 'N/A' : pw + 'W'}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  document.getElementById('power-ref-section').innerHTML = html;
}

// ──── Winding Ratios (admin) ────
function renderWindingRatios() {
  if (!isAdmin) return;
  const el = document.getElementById('winding-section');
  const tIds = Object.keys(TRANSISTORS);
  let html = `<div class="step-header"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg><h2 class="step-title">Winding Ratios & PEP (2-Pill Pair)</h2><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--textDim)" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>`;
  html += '<div class="table-wrap"><table class="data-table"><thead><tr><th style="text-align:left">Transistor</th><th>Voltage</th><th>Input Ratio</th><th>Output Ratio</th><th>Max PEP (Pair)</th><th>Risk</th></tr></thead><tbody>';
  tIds.forEach(id => {
    const t = TRANSISTORS[id];
    const vp = t.voltagePerformance && t.voltagePerformance[voltageMode];
    if (!vp) return;
    const rs = RISK_STYLES[vp.risk] || RISK_STYLES.low;
    const isSel = selectedTransistor === id;
    html += `<tr><td style="color:${isSel ? 'var(--brand)' : '#fff'};font-weight:${isSel ? 700 : 400}">${t.name}</td><td style="color:var(--textMuted)">${voltageMode}V</td><td style="color:#fff">${vp.inputRatio}</td><td style="color:#fff">${vp.outputRatio}</td><td style="color:${vp.pepW ? 'var(--brand)' : 'var(--red)'}">${vp.pepW ? vp.pepW[0] + '-' + vp.pepW[1] + 'W' : 'N/A'}</td><td><span style="font-size:10px;padding:2px 8px;border-radius:2px;background:${rs.bg};color:${rs.color}">${rs.label}</span></td></tr>`;
  });
  html += '</tbody></table></div>';
  if (voltageMode !== '13.8') {
    html += `<div class="warning-note"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#eab308" stroke-width="2" style="flex-shrink:0;margin-top:2px"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg><p><strong>Output Transformer Note:</strong> At ${voltageMode}V, using a 1:2 output ratio (standard for 12V amps) will result in extremely high collector current and likely transistor failure. Moving to the 1:3 ratio (1:9 impedance) is mandatory to keep the load line safe.</p></div>`;
  }
  el.innerHTML = html;
}

// ──── Tuning Values (admin) ────
function renderTuning() {
  if (!isAdmin) return;
  const el = document.getElementById('tuning-section');
  const tIds = Object.keys(TRANSISTORS);
  let html = `<div class="step-header"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg><h2 class="step-title">Tuning Values (High-Voltage Style)</h2><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="var(--textDim)" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>`;
  html += '<div class="table-wrap"><table class="data-table"><thead><tr><th style="text-align:left">Transistor</th><th>Input Tune (Base-to-Base)</th><th>Output Tune (Coll-to-Coll)</th><th style="text-align:left">Notes</th></tr></thead><tbody>';
  tIds.forEach(id => {
    const t = TRANSISTORS[id];
    if (!t.hvTuning) return;
    const isSel = selectedTransistor === id;
    html += `<tr><td style="color:${isSel ? 'var(--brand)' : '#fff'};font-weight:${isSel ? 700 : 400}">${t.name}</td><td style="color:var(--brandLight)">${t.hvTuning.inputTune}</td><td style="color:var(--brandLight)">${t.hvTuning.outputTune}</td><td style="text-align:left;font-family:inherit;font-size:12px;color:var(--textMuted);max-width:300px;line-height:1.5">${esc(t.hvTuning.notes)}</td></tr>`;
  });
  html += '</tbody></table></div>';
  html += `<div class="tuning-notes">
    <p><strong>Rule of Thumb for 18V:</strong> Input: Start small and add until SWR is flat. Output: Start with 820pF (2SC2879) and add 100pF at a time. If power goes up and current stays steady, keep going. If power stops rising but heat/amps increase, back off.</p>
    <p><strong>Broadband vs Peaked:</strong> For specific frequency (27-28MHz), use large output cap to "dip" the circuit. For broadband, use smaller values.</p>
    <p><strong>Impedance Note:</strong> At 18V+, the 1:3 output ratio creates higher reflected impedance. Keep output capacitance lower to avoid over-coupling. These transistors become extremely "hot" at 18V — use heavy shunt on input to swamp gain.</p>
  </div>`;
  el.innerHTML = html;
}

// ──── Inquiry Form ────
function openInquiry() {
  showInquiry = true;
  showPayment = false;
  document.getElementById('payment-section').classList.add('hidden');
  const el = document.getElementById('inquiry-section');
  el.classList.remove('hidden');
  const t = TRANSISTORS[selectedTransistor];
  const power = calcPower(selectedConfig, t, voltageMode);
  const price = calcPrice(selectedConfig, t);
  el.innerHTML = `<div class="form-wrap">
    <div style="margin-bottom:24px"><p class="step-label">Get a Quote</p><h3 class="step-title" style="font-size:1.25rem">${esc(selectedConfig.name)} &middot; ${esc(selectedTransistor)} &middot; ${power}W &middot; $${price}</h3></div>
    <form id="inquiry-form" onsubmit="submitInquiry(event)">
      <div class="form-grid">
        <div class="form-field"><label>Name *</label><input id="inq-name" required placeholder="Your name"></div>
        <div class="form-field"><label>Email *</label><input id="inq-email" type="email" required placeholder="you@email.com"></div>
        <div class="form-field full"><label>Phone (optional)</label><input id="inq-phone" placeholder="(555) 123-4567"></div>
        <div class="form-field full"><label>Message</label><textarea id="inq-message" rows="4" placeholder="Any special requests, questions, or details about your build..."></textarea></div>
      </div>
      <div class="form-actions" style="margin-top:16px">
        <button type="submit" class="btn btn-brand"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg> Submit Inquiry</button>
        <button type="button" class="btn btn-outline" onclick="closeInquiry()">Cancel</button>
      </div>
    </form>
  </div>`;
  el.scrollIntoView({ behavior: 'smooth' });
}

function closeInquiry() {
  showInquiry = false;
  document.getElementById('inquiry-section').classList.add('hidden');
}

async function submitInquiry(e) {
  e.preventDefault();
  const t = TRANSISTORS[selectedTransistor];
  const power = calcPower(selectedConfig, t, voltageMode);
  const price = calcPrice(selectedConfig, t);
  try {
    const res = await fetch(AMP_API + '/api/amps/inquiry', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: document.getElementById('inq-name').value, email: document.getElementById('inq-email').value, phone: document.getElementById('inq-phone').value, config_id: selectedConfig.id, config_name: selectedConfig.name, transistor: selectedTransistor, estimated_power: power, estimated_price: price, message: document.getElementById('inq-message').value }),
    });
    if (res.ok) {
      document.getElementById('inquiry-section').innerHTML = `<div class="form-wrap"><div class="success-box"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg><h3>Inquiry Submitted!</h3><p>We'll get back to you shortly about your ${esc(selectedConfig.name)} build with ${esc(selectedTransistor)} transistors.</p><button class="btn btn-outline" style="margin-top:24px" onclick="closeInquiry()">Close</button></div></div>`;
    }
  } catch (err) { console.error(err); }
}

// ──── Payment Form ────
function openPayment() {
  showPayment = true;
  showInquiry = false;
  document.getElementById('inquiry-section').classList.add('hidden');
  const el = document.getElementById('payment-section');
  el.classList.remove('hidden');
  const t = TRANSISTORS[selectedTransistor];
  const power = calcPower(selectedConfig, t, voltageMode);
  const price = calcPrice(selectedConfig, t);
  el.innerHTML = `<div class="form-wrap">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:24px">
      <div><p class="step-label">Checkout</p><h3 class="step-title" style="font-size:1.25rem">${esc(selectedConfig.name)} &middot; ${esc(selectedTransistor)} &middot; ${power}W</h3></div>
      <button onclick="closePayment()" style="background:none;border:none;color:var(--textMuted);cursor:pointer;padding:4px"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
    </div>
    <div class="form-grid">
      <div class="form-field"><label>Name *</label><input id="pay-name" required placeholder="Your name"></div>
      <div class="form-field"><label>Email *</label><input id="pay-email" type="email" required placeholder="you@email.com"></div>
    </div>
    <div style="border-radius:2px;border:1px solid var(--border);padding:16px;background:var(--bg);margin-top:16px">
      <div class="cost-row"><span class="label">Full price</span><span class="value" style="color:var(--green)">$${price}</span></div>
      <div class="cost-row"><span class="label">50% deposit to start build</span><span class="value" style="color:var(--brand)">$${Math.round(price / 2)}</span></div>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:16px">
      <button class="btn btn-brand" style="flex:1" onclick="handleCheckout('deposit')"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg> Pay 50% ($${Math.round(price / 2)})</button>
      <button class="btn btn-green" style="flex:1" onclick="handleCheckout('full')"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg> Pay Full $${price}</button>
    </div>
    <p style="font-size:12px;text-align:center;color:var(--textDim);margin-top:12px">Secure payment via Stripe. You'll be redirected to complete checkout.</p>
  </div>`;
  el.scrollIntoView({ behavior: 'smooth' });
}

function closePayment() {
  showPayment = false;
  document.getElementById('payment-section').classList.add('hidden');
}

async function handleCheckout(paymentType) {
  const name = document.getElementById('pay-name').value;
  const email = document.getElementById('pay-email').value;
  if (!name || !email) return;
  try {
    const res = await fetch(AMP_API + '/api/amps/checkout', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config_id: selectedConfig.id, transistor: selectedTransistor, payment_type: paymentType, origin_url: window.location.origin, customer_name: name, customer_email: email }),
    });
    if (res.ok) { const data = await res.json(); if (data.url) window.location.href = data.url; }
  } catch (err) { console.error(err); }
}

// ──── Admin ────
function toggleAdminLogin() {
  if (isAdmin) { handleAdminLogout(); return; }
  document.getElementById('admin-modal').classList.remove('hidden');
  document.getElementById('admin-email').focus();
}

function closeAdminModal() {
  document.getElementById('admin-modal').classList.add('hidden');
  document.getElementById('admin-error').classList.add('hidden');
}

async function handleAdminLogin(e) {
  e.preventDefault();
  const email = document.getElementById('admin-email').value;
  const password = document.getElementById('admin-password').value;
  try {
    const res = await fetch(AMP_API + '/api/amps/admin/verify', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem('sma_admin_token', data.token);
      isAdmin = true;
      closeAdminModal();
      updateAdminUI();
    } else {
      const err = document.getElementById('admin-error');
      err.textContent = 'Invalid email or password';
      err.classList.remove('hidden');
    }
  } catch { document.getElementById('admin-error').textContent = 'Connection error'; document.getElementById('admin-error').classList.remove('hidden'); }
}

function handleAdminLogout() {
  localStorage.removeItem('sma_admin_token');
  isAdmin = false;
  voltageMode = '13.8';
  showSpecs = false;
  updateAdminUI();
}

function updateAdminUI() {
  const btn = document.getElementById('admin-toggle');
  if (isAdmin) {
    btn.className = 'admin-btn';
    btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg> Admin';
  } else {
    btn.className = 'admin-btn login';
    btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>';
  }
  document.getElementById('voltage-section').classList.toggle('hidden', !isAdmin);
  document.getElementById('specs-toggle').classList.toggle('hidden', !isAdmin);
  document.getElementById('winding-section').classList.toggle('hidden', !isAdmin);
  document.getElementById('tuning-section').classList.toggle('hidden', !isAdmin);
  if (!isAdmin) { document.getElementById('spec-sheets').classList.add('hidden'); showSpecs = false; }
  renderVoltage();
  renderSpecs();
  renderPowerRef();
  renderWindingRatios();
  renderTuning();
}

// ──── Init ────
async function init() {
  // Try loading data from CMS API, fallback to static amps-data.js
  try {
    const res = await fetch('/api/cms/content/configurator');
    if (res.ok) {
      const cfg = await res.json();
      if (cfg.amp_configs && cfg.amp_configs.length) AMP_CONFIGS.length = 0, cfg.amp_configs.forEach(c => AMP_CONFIGS.push(c));
      if (cfg.transistors && Object.keys(cfg.transistors).length) { Object.keys(TRANSISTORS).forEach(k => delete TRANSISTORS[k]); Object.assign(TRANSISTORS, cfg.transistors); }
      if (cfg.voltage_modes && cfg.voltage_modes.length) VOLTAGE_MODES.length = 0, cfg.voltage_modes.forEach(v => VOLTAGE_MODES.push(v));
      if (cfg.gallery_images && cfg.gallery_images.length) GALLERY_IMAGES.length = 0, cfg.gallery_images.forEach(g => GALLERY_IMAGES.push(g));
      if (cfg.gallery_filters && cfg.gallery_filters.length) GALLERY_FILTERS.length = 0, cfg.gallery_filters.forEach(f => GALLERY_FILTERS.push(f));
      console.log('Loaded configurator data from CMS API');
    }
  } catch(e) { console.log('Using static amps-data.js fallback'); }

  // Reset selections to valid values
  selectedConfig = AMP_CONFIGS[1] || AMP_CONFIGS[0];
  selectedTransistor = Object.keys(TRANSISTORS)[0] || '2SC2879';

  // Check existing admin token
  const token = localStorage.getItem('sma_admin_token');
  if (token) {
    fetch(AMP_API + '/api/amps/admin/check?token=' + token)
      .then(r => r.json())
      .then(d => { if (d.valid) { isAdmin = true; updateAdminUI(); } else { localStorage.removeItem('sma_admin_token'); } })
      .catch(() => {});
  }
  renderConfigs();
  renderTransistors();
  renderVoltage();
  renderSpecs();
  renderSpecSheets();
  renderPowerRef();
  renderGallery();
}

// ──── Gallery ────
let galleryFilter = 'all';

function renderGallery() {
  const el = document.getElementById('gallery-section');
  const filtered = galleryFilter === 'all' ? GALLERY_IMAGES : GALLERY_IMAGES.filter(i => i.configType === galleryFilter);

  let html = `<div class="step-header"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--brand)" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg><h2 class="step-title">Build Gallery</h2></div>`;
  html += '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:24px">';
  GALLERY_FILTERS.forEach(f => {
    const active = galleryFilter === f.id;
    html += `<button onclick="setGalleryFilter('${f.id}')" style="padding:8px 16px;font-size:12px;border-radius:2px;letter-spacing:.1em;text-transform:uppercase;cursor:pointer;transition:all .2s;background:${active ? 'var(--brandMuted)' : 'transparent'};color:${active ? 'var(--brand)' : 'var(--textMuted)'};border:1px solid ${active ? 'var(--brand)' : 'var(--border)'}">${f.label}</button>`;
  });
  html += '</div>';
  html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px">';
  filtered.forEach(img => {
    html += `<div style="border-radius:2px;border:1px solid var(--border);overflow:hidden">
      <div style="aspect-ratio:4/3;overflow:hidden;background:var(--card)"><img src="${esc(img.src)}" alt="${esc(img.alt)}" style="width:100%;height:100%;object-fit:cover;transition:transform .5s" onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'" loading="lazy"></div>
      <div style="padding:16px;background:var(--card)"><h4 style="font-size:14px;font-weight:600;color:#fff">${esc(img.label)}</h4><p style="font-size:12px;margin-top:4px;color:var(--textMuted)">${esc(img.description)}</p></div>
    </div>`;
  });
  html += '</div>';
  html += '<p style="font-size:12px;text-align:center;margin-top:16px;color:var(--textDim)">Placeholder images — real build photos coming soon</p>';
  el.innerHTML = html;
}

function setGalleryFilter(id) {
  galleryFilter = id;
  renderGallery();
}

init();
