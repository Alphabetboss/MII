/* Ingenious Irrigation · Astra UI (Sketch Pro)
   - One JS file shared across pages.
   - Safe to load even when some elements do not exist.
*/

const $ = (id) => document.getElementById(id);

async function httpJson(url, options = {}) {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const ct = resp.headers.get('content-type') || '';
  const body = ct.includes('application/json') ? await resp.json() : await resp.text();
  if (!resp.ok) throw new Error(typeof body === 'string' ? body : (body.error || JSON.stringify(body)));
  return body;
}

function showToast(message, isError = false) {
  const el = $('toast');
  if (!el) return;
  el.textContent = message;
  el.classList.add('show');
  el.classList.toggle('error', Boolean(isError));
  window.clearTimeout(showToast._t);
  showToast._t = window.setTimeout(() => el.classList.remove('show'), 3200);
}

function zoneIds(schedule) {
  return Object.keys(schedule?.zones || {}).sort((a, b) => Number(a) - Number(b));
}

function prettyFrequency(cfg) {
  const frequency = cfg?.frequency || 'daily';
  if (frequency === 'daily') return 'Daily';
  if (frequency === 'every_x_days') return `Every ${cfg?.every_x_days || 2} days`;
  if (frequency === 'days_of_week') {
    const days = (cfg?.days_of_week || []).join(', ');
    return days || 'Selected days';
  }
  return String(frequency).replaceAll('_', ' ');
}

function setConnection(ok) {
  const pill = $('connectionPill');
  if (!pill) return;
  pill.textContent = ok ? 'Connected' : 'Offline';
  pill.classList.toggle('soft', ok);
}

// ---------------- Clock (client-side) ----------------
function startClock() {
  const timeEl = $('clockTime');
  const dateEl = $('clockDate');
  if (!timeEl || !dateEl) return;

  const tick = () => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    timeEl.textContent = `${hh}:${mm}`;
    dateEl.textContent = now.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
  };
  tick();
  window.setInterval(tick, 15000);
}

// ---------------- Voice (laptop) ----------------
const voiceState = {
  micActive: false,
  convoActive: false,
  micSupported: false,
  recognition: null,
  wakeWord: 'Astra',
  astraName: 'Astra',
  preferBrowserTts: false,
  allowBrowserFallback: false,
  serverTtsAvailable: false,
  preferredVoiceHint: '',
};

function setupSpeechControls(onCommandText) {
  const micBtn = $('micToggleBtn');
  const convoBtn = $('convoToggleBtn');
  const label = $('micStatusLabel');
  if (!micBtn && !convoBtn) return;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    voiceState.micSupported = false;
    if (micBtn) micBtn.disabled = true;
    if (convoBtn) convoBtn.disabled = true;
    if (label) label.textContent = 'Voice input isn’t supported in this browser.';
    return;
  }

  voiceState.micSupported = true;
  const rec = new SpeechRecognition();
  rec.continuous = true;
  rec.interimResults = false;
  rec.lang = 'en-US';

  const wakeWordLower = () => String(voiceState.wakeWord || 'Astra').toLowerCase();

  const setUi = () => {
    if (micBtn) {
      micBtn.classList.toggle('active', voiceState.micActive);
      micBtn.textContent = voiceState.micActive ? 'Listening' : 'Mic';
    }
    if (convoBtn) {
      convoBtn.classList.toggle('active', voiceState.convoActive);
      convoBtn.textContent = voiceState.convoActive ? 'Talking' : 'Convo';
    }
    if (!label) return;
    if (voiceState.convoActive) {
      label.textContent = `Conversation mode: just talk — ${voiceState.astraName} will reply.`;
    } else if (voiceState.micActive) {
      label.textContent = `Listening… say “${voiceState.wakeWord} …”`;
    } else {
      label.textContent = `Say “${voiceState.wakeWord}” before a voice command.`;
    }
  };

  const safeStart = () => {
    try { rec.start(); } catch (_) {}
  };
  const safeStop = () => {
    try { rec.stop(); } catch (_) {}
  };

  rec.onresult = (event) => {
    const last = event.results[event.results.length - 1];
    const text = String(last[0]?.transcript || '').trim();
    if (!text) return;

    // Convo mode: treat every final utterance as a message.
    if (voiceState.convoActive) {
      onCommandText(text);
      return;
    }

    // Wake-word mode: require the wake word somewhere in the phrase.
    const lower = text.toLowerCase();
    const wake = wakeWordLower();
    const idx = lower.indexOf(wake);
    if (idx === -1) {
      if (label) label.textContent = `Say “${voiceState.wakeWord}” before a voice command.`;
      return;
    }
    const command = text.slice(idx + wake.length).replace(/^[:\s,.-]+/, '').trim();
    if (!command) {
      if (label) label.textContent = `Listening… say a command after “${voiceState.wakeWord}”.`;
      return;
    }
    onCommandText(`${voiceState.wakeWord}, ${command}`);
  };

  rec.onend = () => {
    // Chrome/Safari can end sessions on pauses. If a mode is active, restart.
    if (voiceState.micActive || voiceState.convoActive) safeStart();
  };

  rec.onerror = () => {
    // Don’t spam; just show a small prompt.
    if (label) label.textContent = 'Mic paused. Click Mic/Convo again.';
    voiceState.micActive = false;
    voiceState.convoActive = false;
    setUi();
  };

  voiceState.recognition = rec;

  micBtn?.addEventListener('click', () => {
    voiceState.micActive = !voiceState.micActive;
    if (voiceState.micActive) voiceState.convoActive = false;
    setUi();
    if (voiceState.micActive) safeStart();
    else safeStop();
  });

  convoBtn?.addEventListener('click', () => {
    voiceState.convoActive = !voiceState.convoActive;
    if (voiceState.convoActive) voiceState.micActive = false;
    setUi();
    if (voiceState.convoActive) safeStart();
    else safeStop();
  });

  setUi();
}

function speakBrowser(text) {
  const synth = window.speechSynthesis;
  if (!synth) return;
  const utter = new SpeechSynthesisUtterance(text);
  // pick a confident, friendly voice if available
  const voices = synth.getVoices?.() || [];
  const hint = String(voiceState.preferredVoiceHint || '').toLowerCase();
  const byHint = hint
    ? voices.find(v => String(v.name || '').toLowerCase().includes(hint) || String(v.voiceURI || '').toLowerCase().includes(hint))
    : null;
  const preferred = byHint
    || voices.find(v => /samantha|victoria|zira|ava|allison|serena|jenny|aria|hazel|susan/i.test(v.name))
    || voices.find(v => /female|woman/i.test(v.name))
    || voices.find(v => /en/i.test(v.lang || ''))
    || voices[0];
  if (preferred) utter.voice = preferred;
  // Slightly crisp, upbeat cadence
  utter.rate = 1.04;
  utter.pitch = 1.08;
  synth.cancel();
  synth.speak(utter);
}

function playServerAudio(audioUrl) {
  if (!audioUrl) return;
  const audio = new Audio(audioUrl + (audioUrl.includes('?') ? '&' : '?') + 't=' + Date.now());
  audio.play().catch(() => {});
}

async function speakOut(text, context = 'general') {
  const line = String(text || '').trim();
  if (!line) return;

  // Prefer Pi/server-side TTS when available (speaker attached to the device).
  if (voiceState.serverTtsAvailable) {
    try {
      const result = await httpJson('/api/astra/speak', { method: 'POST', body: JSON.stringify({ text: line, context }) });
      if (result.audio_url) playServerAudio(result.audio_url);
      return;
    } catch (err) {
      // On Pi we avoid browser fallback; surface an on-screen hint instead.
      const label = document.getElementById('micStatusLabel');
      if (label) label.textContent = 'Astra audio error — check speaker/voice service.';
      if (!voiceState.allowBrowserFallback) return;
    }
  }
  if (voiceState.preferBrowserTts) speakBrowser(line);
}

// ---------------- Dashboard rendering ----------------

const dash = {
  selectedZone: '1',
  schedule: { zones: {} },
  settings: null,
  system: null,
  telemetry: null,
};

function ensureSelectedZone() {
  const zones = zoneIds(dash.schedule);
  if (!zones.length) {
    dash.selectedZone = '1';
    return;
  }
  if (!zones.includes(dash.selectedZone)) dash.selectedZone = zones[0];
}

function currentZoneConfig() {
  return dash.schedule?.zones?.[dash.selectedZone] || {
    minutes: 10,
    enabled: true,
    start_time: '05:00',
    frequency: 'daily',
    every_x_days: 2,
    days_of_week: [],
  };
}

function gradeForTelemetry(telemetry) {
  // Simple & stable grading for the UI: keep it understandable.
  const soil = Number(telemetry?.soil_moisture_pct ?? 42);
  if (soil >= 35 && soil <= 62) return 'A';
  if ((soil >= 28 && soil < 35) || (soil > 62 && soil <= 70)) return 'B';
  if ((soil >= 22 && soil < 28) || (soil > 70 && soil <= 78)) return 'C';
  if ((soil >= 16 && soil < 22) || (soil > 78 && soil <= 86)) return 'D';
  return 'F';
}

function renderZoneSelectors() {
  const chipRow = $('autoZoneChips');
  const manualSelect = $('manualZoneSelect');
  const sprinklerDefaultZone = $('sprinklerDefaultZone');
  if (!chipRow && !manualSelect && !sprinklerDefaultZone) return;

  ensureSelectedZone();
  const zones = zoneIds(dash.schedule);

  if (chipRow) chipRow.innerHTML = '';
  if (manualSelect) manualSelect.innerHTML = '';
  if (sprinklerDefaultZone) sprinklerDefaultZone.innerHTML = '';

  zones.forEach((z) => {
    if (chipRow) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = `zone-chip${z === dash.selectedZone ? ' active' : ''}`;
      b.textContent = `Zone ${z}`;
      b.addEventListener('click', () => {
        dash.selectedZone = z;
        renderZoneSelectors();
        renderAutoCard();
        renderZoneHistory();
      });
      chipRow.appendChild(b);
    }

    const opt = document.createElement('option');
    opt.value = z;
    opt.textContent = `Zone ${z}`;
    if (manualSelect) manualSelect.appendChild(opt.cloneNode(true));

    if (sprinklerDefaultZone) {
      const o2 = opt.cloneNode(true);
      if (Number(dash.settings?.sprinkler?.default_zone || 1) === Number(z)) o2.selected = true;
      sprinklerDefaultZone.appendChild(o2);
    }
  });

  if (manualSelect) manualSelect.value = dash.selectedZone;
}

function renderAutoCard() {
  const cfg = currentZoneConfig();
  const tele = dash.telemetry?.telemetry || {};
  const health = dash.telemetry?.health || {};

  const gradeEl = $('healthGrade');
  const startEl = $('autoStartTime');
  const daysEl = $('autoDays');
  const minEl = $('autoMinutes');
  const sumEl = $('healthSummary');
  const noteEl = $('healthNote');
  const astraToggleEl = $('astraZoneControlToggle');

  const grade = gradeForTelemetry(tele);
  if (gradeEl) gradeEl.textContent = grade;
  if (startEl) startEl.textContent = cfg.start_time || '--:--';
  if (daysEl) daysEl.textContent = prettyFrequency(cfg);
  if (minEl) minEl.textContent = `${cfg.minutes ?? 10} min`;
  if (sumEl) sumEl.textContent = health.summary || (grade === 'A' ? 'Healthy range.' : 'Needs attention.');
  if (astraToggleEl) astraToggleEl.checked = Boolean(cfg.astra_control_enabled ?? true);
  if (noteEl) {
    const soil = tele.soil_moisture_pct != null ? `Soil moisture is ${Number(tele.soil_moisture_pct).toFixed(0)}%.` : 'Collecting new soil read…';
    noteEl.textContent = health.remedy || soil;
  }
}

function renderManualStatus() {
  const el = $('manualStatus');
  if (!el) return;
  const controller = dash.system?.controller || {};
  if (controller.watering) el.textContent = `Watering Zone ${controller.active_zone} now.`;
  else el.textContent = 'Nothing is watering right now.';
}

function appendMessage(who, text) {
  const history = $('messageHistory');
  const output = $('messageOutput');
  if (output) output.textContent = text;
  if (!history) return;
  const row = document.createElement('div');
  row.className = 'msg-row';
  row.innerHTML = `<span class="msg-who">${who}</span><span class="msg-text">${escapeHtml(text)}</span>`;
  history.prepend(row);
}

function escapeHtml(s) {
  return String(s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;');
}

async function sendChat(message) {
  const text = String(message || '').trim();
  if (!text) return;
  appendMessage('You', text);
  try {
    const res = await httpJson('/astra/chat', { method: 'POST', body: JSON.stringify({ message: text }) });
    const reply = res.reply || '…';
    appendMessage('Astra', reply);
    await speakOut(reply, 'chat_reply');
  } catch (err) {
    showToast(`Chat error: ${err.message}`, true);
  }
}

function renderZoneHistory() {
  const grid = $('zoneHistoryGrid');
  if (!grid) return;
  const zones = zoneIds(dash.schedule);
  const tele = dash.telemetry?.telemetry || {};
  const soil = Number(tele.soil_moisture_pct ?? 42);
  const tempC = Number(tele.temperature_c ?? 24);
  const pressure = Number(tele.pressure_psi ?? 46);

  grid.innerHTML = '';
  zones.forEach((z) => {
    const card = document.createElement('div');
    card.className = 'history-card chrome-panel raised';
    const grade = gradeForTelemetry({ ...tele, soil_moisture_pct: soil + (Number(z) - 1) * 1.5 });
    card.innerHTML = `
      <div class="history-head">
        <strong>Zone ${z}</strong>
        <span class="grade-pill">${grade}</span>
      </div>
      <div class="history-metrics">
        <div><span>Soil</span><strong>${Math.max(0, Math.min(100, soil + (Number(z) - 1) * 1.5)).toFixed(0)}%</strong></div>
        <div><span>Temp</span><strong>${tempC.toFixed(0)}°C</strong></div>
        <div><span>Pressure</span><strong>${pressure.toFixed(0)} PSI</strong></div>
      </div>
      <div class="spark" aria-hidden="true">${sparkline(soil + Number(z))}</div>
    `;
    grid.appendChild(card);
  });
}

function sparkline(seed) {
  // text sparkline with blocks (works without canvas)
  const vals = Array.from({ length: 18 }, (_, i) => {
    const wave = Math.sin((i + seed) / 2.8) * 8;
    const drift = (seed % 5) - 2;
    const v = 48 + wave + drift - i * 0.25;
    return Math.max(10, Math.min(90, v));
  });
  const blocks = '▁▂▃▄▅▆▇█';
  return vals.map(v => blocks[Math.floor((v / 100) * (blocks.length - 1))]).join('');
}

// ---------------- Settings pages ----------------

function populateSettingsForms(settings, schedule) {
  // Sprinkler
  const spr = settings?.sprinkler || {};
  if ($('sprinklerDefaultMinutes')) $('sprinklerDefaultMinutes').value = spr.default_minutes ?? 10;
  if ($('sprinklerStartTime')) $('sprinklerStartTime').value = spr.start_time ?? '05:30';
  if ($('sprinklerSoakGuard')) $('sprinklerSoakGuard').checked = Boolean(spr.soak_guard_enabled);
  if ($('sprinklerSeasonalBlend')) $('sprinklerSeasonalBlend').checked = Boolean(spr.seasonal_blend_enabled);
  if ($('sprinklerQuietHours')) $('sprinklerQuietHours').checked = Boolean(spr.quiet_hours_enabled);
  if ($('sprinklerQuietStart')) $('sprinklerQuietStart').value = spr.quiet_hours_start ?? '22:00';
  if ($('sprinklerQuietEnd')) $('sprinklerQuietEnd').value = spr.quiet_hours_end ?? '06:00';

  // AI
  const ai = settings?.ai || {};
  if ($('aiAstraEnabled')) $('aiAstraEnabled').checked = ai.astra_enabled !== false;
  if ($('aiWaterDetection')) $('aiWaterDetection').checked = ai.water_detection_enabled !== false;
  if ($('aiPeopleAvoidance')) $('aiPeopleAvoidance').checked = Boolean(ai.people_avoidance_enabled);
  if ($('aiAnimalDeterrent')) $('aiAnimalDeterrent').checked = Boolean(ai.animal_deterrent_enabled);
  if ($('aiAnimalStart')) $('aiAnimalStart').value = ai.animal_deterrent_start ?? '21:00';
  if ($('aiAnimalEnd')) $('aiAnimalEnd').value = ai.animal_deterrent_end ?? '05:00';
  if ($('aiAnimalDistance')) $('aiAnimalDistance').value = ai.animal_deterrent_distance_ft ?? 18;
  if ($('aiIntelligentOverride')) $('aiIntelligentOverride').checked = Boolean(ai.intelligent_override_enabled);
  if ($('aiOverrideLimit')) $('aiOverrideLimit').value = ai.intelligent_override_limit_pct ?? 12;

  // Fill zone dropdowns
  const zd = $('sprinklerDefaultZone');
  if (zd) {
    zd.innerHTML = '';
    zoneIds(schedule).forEach((z) => {
      const opt = document.createElement('option');
      opt.value = z;
      opt.textContent = `Zone ${z}`;
      if (Number(spr.default_zone || 1) === Number(z)) opt.selected = true;
      zd.appendChild(opt);
    });
  }
}

async function saveSprinklerSettings() {
  const payload = {
    default_zone: Number($('sprinklerDefaultZone')?.value || 1),
    default_minutes: Number($('sprinklerDefaultMinutes')?.value || 10),
    start_time: String($('sprinklerStartTime')?.value || '05:30'),
    soak_guard_enabled: Boolean($('sprinklerSoakGuard')?.checked),
    seasonal_blend_enabled: Boolean($('sprinklerSeasonalBlend')?.checked),
    quiet_hours_enabled: Boolean($('sprinklerQuietHours')?.checked),
    quiet_hours_start: String($('sprinklerQuietStart')?.value || '22:00'),
    quiet_hours_end: String($('sprinklerQuietEnd')?.value || '06:00'),
  };
  const res = await httpJson('/api/settings/sprinkler', { method: 'POST', body: JSON.stringify(payload) });
  showToast('Sprinkler settings saved.');
  return res;
}

async function saveAiSettings() {
  const payload = {
    astra_enabled: Boolean($('aiAstraEnabled')?.checked),
    water_detection_enabled: Boolean($('aiWaterDetection')?.checked),
    people_avoidance_enabled: Boolean($('aiPeopleAvoidance')?.checked),
    animal_deterrent_enabled: Boolean($('aiAnimalDeterrent')?.checked),
    animal_deterrent_start: String($('aiAnimalStart')?.value || '21:00'),
    animal_deterrent_end: String($('aiAnimalEnd')?.value || '05:00'),
    animal_deterrent_distance_ft: Number($('aiAnimalDistance')?.value || 18),
    intelligent_override_enabled: Boolean($('aiIntelligentOverride')?.checked),
    intelligent_override_limit_pct: Number($('aiOverrideLimit')?.value || 12),
  };
  const res = await httpJson('/api/settings/ai', { method: 'POST', body: JSON.stringify(payload) });
  showToast('AI settings saved.');
  return res;
}

async function saveAstraZoneControl(zone, enabled) {
  const cfg = currentZoneConfig();
  const payload = {
    minutes: Number(cfg.minutes ?? 10),
    enabled: Boolean(cfg.enabled ?? true),
    astra_control_enabled: Boolean(enabled),
    start_time: String(cfg.start_time || '05:00'),
    frequency: String(cfg.frequency || 'daily'),
    every_x_days: Number(cfg.every_x_days || 2),
    days_of_week: Array.isArray(cfg.days_of_week) ? cfg.days_of_week : [],
  };
  const res = await httpJson('/api/schedule/update', { method: 'POST', body: JSON.stringify({ zone: Number(zone), ...payload }) });
  dash.schedule.zones[String(zone)] = res.config;
  renderAutoCard();
  renderZoneHistory();
  showToast(`Astra ${enabled ? 'enabled' : 'disabled'} for Zone ${zone}. Manual watering stays available.`);
  return res;
}

// ---------------- Details page ----------------

function renderDetailsCharts(schedule) {
  const grid = $('detailZoneGrid');
  if (!grid) return;
  if (!window.Chart) {
    grid.innerHTML = '<p class="muted">Chart library not loaded.</p>';
    return;
  }
  grid.innerHTML = '';

  zoneIds(schedule).forEach((z) => {
    const wrap = document.createElement('div');
    wrap.className = 'detail-zone-card';
    wrap.innerHTML = `
      <div class="detail-zone-head"><strong>Zone ${z}</strong><span class="muted">Plant health score</span></div>
      <canvas id="chart_${z}" height="120"></canvas>
    `;
    grid.appendChild(wrap);
    const ctx = wrap.querySelector('canvas').getContext('2d');
    const points = Array.from({ length: 14 }, (_, i) => {
      const base = 72 - i * 0.9;
      const wave = Math.sin((i + Number(z)) / 2.2) * 4;
      return Math.max(10, Math.min(100, base + wave + (Number(z) - 1) * 1.5));
    }).reverse();
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: points.map((_, i) => `Day ${i + 1}`),
        datasets: [{
          data: points,
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { display: true, min: 0, max: 100, ticks: { maxTicksLimit: 4 } },
        },
      },
    });
  });
}

function renderList(containerId, items, formatter) {
  const el = $(containerId);
  if (!el) return;
  el.innerHTML = '';
  if (!items?.length) {
    el.innerHTML = '<p class="muted">No entries yet.</p>';
    return;
  }
  items.slice(0, 40).forEach((it) => {
    const row = document.createElement('div');
    row.className = 'detail-item';
    row.innerHTML = formatter(it);
    el.appendChild(row);
  });
}

// ---------------- Boot ----------------

async function boot() {
  startClock();

  // Always try to load these
  try {
    const [schedule, settings, status, profile] = await Promise.all([
      httpJson('/api/schedule'),
      httpJson('/api/settings').then(r => r.settings),
      httpJson('/api/system/status'),
      httpJson('/api/astra/profile').catch(() => null),
    ]);
    dash.schedule = schedule;
    dash.settings = settings;
    dash.system = status;

    // Voice config for wake-word + TTS routing
    const v = status?.voice || {};
    voiceState.wakeWord = (profile?.wake_phrase || v.wake_phrase || voiceState.wakeWord);
    voiceState.astraName = (profile?.name || voiceState.astraName);
    voiceState.serverTtsAvailable = Boolean(v.available);
    // Pi-first: if local/server voice is available, prefer it and avoid browser fallback.
    voiceState.allowBrowserFallback = !voiceState.serverTtsAvailable;
    voiceState.preferBrowserTts = voiceState.allowBrowserFallback;
voiceState.preferredVoiceHint = v.preferred_voice || '';

    setConnection(true);
  } catch (err) {
    setConnection(false);
    showToast(`Offline: ${err.message}`, true);
  }

  // Telemetry (optional)
  try {
    dash.telemetry = await httpJson('/api/telemetry');
  } catch (_) {
    dash.telemetry = null;
  }

  // Populate page elements if they exist
  renderZoneSelectors();
  renderAutoCard();
  renderManualStatus();
  renderZoneHistory();
  populateSettingsForms(dash.settings, dash.schedule);
  renderDetailsCharts(dash.schedule);

  // Update any voice copy in the UI.
  const input = $('chatInput');
  if (input) input.placeholder = `Type a question, or say: ‘${voiceState.wakeWord}, water Zone 1 for 10 minutes.’`;

  // Details lists
  try {
    const [decisions, incidents] = await Promise.all([
      httpJson('/api/decisions?limit=40'),
      httpJson('/api/incidents?limit=40'),
    ]);
    renderList('decisionList', decisions, (d) => {
      const ts = escapeHtml(d.ts || d.timestamp || '');
      const msg = escapeHtml(d.summary || d.message || JSON.stringify(d));
      return `<strong>${ts}</strong><span>${msg}</span>`;
    });
    renderList('incidentList', incidents, (d) => {
      const ts = escapeHtml(d.ts || d.timestamp || '');
      const msg = escapeHtml(d.summary || d.message || JSON.stringify(d));
      return `<strong>${ts}</strong><span>${msg}</span>`;
    });
  } catch (_) {
    // ignore
  }

  // Wire buttons
  $('refreshBtn')?.addEventListener('click', () => window.location.reload());
  $('analyzeBtn')?.addEventListener('click', async () => {
    try {
      dash.telemetry = await httpJson('/api/telemetry');
      renderAutoCard();
      renderZoneHistory();
      showToast('Updated yard read.');
    } catch (err) {
      showToast(`Could not update: ${err.message}`, true);
    }
  });

  $('astraZoneControlToggle')?.addEventListener('change', async (e) => {
    try {
      await saveAstraZoneControl(dash.selectedZone, Boolean(e.target.checked));
    } catch (err) {
      e.target.checked = !e.target.checked;
      showToast(`Could not update Astra control: ${err.message}`, true);
    }
  });

  $('manualZoneSelect')?.addEventListener('change', (e) => {
    dash.selectedZone = String(e.target.value);
    renderZoneSelectors();
    renderAutoCard();
  });

  $('startZoneBtn')?.addEventListener('click', async () => {
    const zone = Number($('manualZoneSelect')?.value || 1);
    const minutes = Number($('manualMinutesInput')?.value || 10);
    try {
      const res = await httpJson(`/api/zone/${zone}/run`, { method: 'POST', body: JSON.stringify({ minutes }) });
      showToast(res.ok ? `Started Zone ${zone}.` : 'Could not start zone.', !res.ok);
      dash.system = await httpJson('/api/system/status');
      renderManualStatus();
    } catch (err) {
      showToast(`Start failed: ${err.message}`, true);
    }
  });

  $('stopZoneBtn')?.addEventListener('click', async () => {
    const zone = Number($('manualZoneSelect')?.value || 1);
    try {
      const res = await httpJson(`/api/zone/${zone}/stop`, { method: 'POST', body: JSON.stringify({}) });
      showToast(res.ok ? `Stopped Zone ${zone}.` : 'Could not stop zone.', !res.ok);
      dash.system = await httpJson('/api/system/status');
      renderManualStatus();
    } catch (err) {
      showToast(`Stop failed: ${err.message}`, true);
    }
  });

  $('chatForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const input = $('chatInput');
    const msg = input?.value || '';
    if (input) input.value = '';
    sendChat(msg);
  });

  $('greetingBtn')?.addEventListener('click', () => {
    sendChat(`${voiceState.wakeWord}, status report`);
  });

  $('saveSprinklerSettingsBtn')?.addEventListener('click', async () => {
    try { await saveSprinklerSettings(); }
    catch (err) { showToast(`Save failed: ${err.message}`, true); }
  });

  $('saveAiSettingsBtn')?.addEventListener('click', async () => {
    try { await saveAiSettings(); }
    catch (err) { showToast(`Save failed: ${err.message}`, true); }
  });

  // Voice controls (wake-word + conversation mode)
  setupSpeechControls((text) => sendChat(text));
}

boot();
