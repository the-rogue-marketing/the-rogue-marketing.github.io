/**
 * AI API Pricing Calculator — Rogue Marketing
 * Comprehensive multimodal token & cost estimator for all major AI providers.
 * Supports text, image, audio, and video input estimation.
 */

const MODELS = {
  google: {
    name: "Google Gemini",
    color: "#4285f4",
    icon: "🔷",
    models: [
      { id:"gemini-3.5-flash", name:"Gemini 3.5 Flash", input:1.50, output:9.00, cachedInput:0.375, context:1000000, img:true, aud:true, vid:true, batch:true, tier:"flagship" },
      { id:"gemini-3.1-pro", name:"Gemini 3.1 Pro", input:2.00, output:12.00, cachedInput:0.50, inputLong:4.00, outputLong:24.00, longThreshold:200000, context:1000000, img:true, aud:true, vid:true, batch:true, tier:"flagship" },
      { id:"gemini-3-flash", name:"Gemini 3 Flash", input:0.50, output:3.00, cachedInput:0.125, context:1000000, img:true, aud:true, vid:true, batch:true, tier:"balanced" },
      { id:"gemini-3.1-flash-lite", name:"Gemini 3.1 Flash-Lite", input:0.25, output:1.50, cachedInput:0.0625, context:1000000, img:true, aud:true, vid:true, batch:true, tier:"budget" },
      { id:"gemini-2.5-pro", name:"Gemini 2.5 Pro", input:1.25, output:10.00, cachedInput:0.3125, inputLong:2.50, outputLong:20.00, longThreshold:200000, context:1000000, img:true, aud:true, vid:true, batch:true, tier:"legacy" },
      { id:"gemini-2.5-flash", name:"Gemini 2.5 Flash", input:0.30, output:2.50, cachedInput:0.075, context:1000000, img:true, aud:true, vid:true, batch:true, tier:"legacy" },
      { id:"gemini-2.5-flash-lite", name:"Gemini 2.5 Flash-Lite", input:0.10, output:0.40, cachedInput:0.025, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"budget" }
    ],
    imageTokens: 258,
    audioTokensPerSec: 32,
    videoTokensPerSec: 263
  },
  openai: {
    name: "OpenAI",
    color: "#10a37f",
    icon: "🟢",
    models: [
      { id:"gpt-5.5-pro", name:"GPT-5.5 Pro", input:5.00, output:30.00, cachedInput:1.25, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"flagship" },
      { id:"gpt-5.5-instant", name:"GPT-5.5 Instant", input:2.50, output:15.00, cachedInput:0.625, context:500000, img:true, aud:false, vid:false, batch:true, tier:"flagship" },
      { id:"gpt-4.1", name:"GPT-4.1", input:2.00, output:8.00, cachedInput:0.50, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"balanced" },
      { id:"gpt-4.1-mini", name:"GPT-4.1 Mini", input:0.40, output:1.60, cachedInput:0.10, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"balanced" },
      { id:"gpt-4.1-nano", name:"GPT-4.1 Nano", input:0.10, output:0.40, cachedInput:0.025, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"budget" },
      { id:"o3", name:"o3", input:2.00, output:8.00, cachedInput:0.50, context:200000, img:false, aud:false, vid:false, batch:true, tier:"reasoning" },
      { id:"o3-pro", name:"o3-Pro", input:20.00, output:80.00, cachedInput:5.00, context:200000, img:false, aud:false, vid:false, batch:false, tier:"reasoning" }
    ],
    imageTokensLow: 85,
    imageTokensHigh: 765,
    audioTokensPerSec: 0,
    videoTokensPerSec: 0,
    whisperPerMin: 0.006
  },
  xai: {
    name: "xAI Grok",
    color: "#1d9bf0",
    icon: "⚡",
    models: [
      { id:"grok-4.3", name:"Grok 4.3", input:1.25, output:2.50, cachedInput:0.13, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"flagship" },
      { id:"grok-4.20", name:"Grok 4.20", input:1.25, output:2.50, cachedInput:0.20, context:2000000, img:true, aud:false, vid:false, batch:true, tier:"flagship" },
      { id:"grok-4.1-fast", name:"Grok 4.1 Fast", input:0.20, output:0.50, cachedInput:0.02, context:2000000, img:true, aud:false, vid:false, batch:true, tier:"budget" }
    ],
    imageTokens: 258,
    audioTokensPerSec: 0,
    videoTokensPerSec: 0
  },
  anthropic: {
    name: "Anthropic Claude",
    color: "#d4a574",
    icon: "🟠",
    models: [
      { id:"claude-opus-4.7", name:"Claude Opus 4.7", input:5.00, output:25.00, cachedInput:0.50, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"flagship" },
      { id:"claude-sonnet-4.6", name:"Claude Sonnet 4.6", input:3.00, output:15.00, cachedInput:0.30, context:1000000, img:true, aud:false, vid:false, batch:true, tier:"balanced" },
      { id:"claude-haiku-4.5", name:"Claude Haiku 4.5", input:1.00, output:5.00, cachedInput:0.10, context:200000, img:true, aud:false, vid:false, batch:true, tier:"budget" }
    ],
    imageTokensPerPixel: 1/750,
    defaultImageTokens: 1400,
    audioTokensPerSec: 0,
    videoTokensPerSec: 0
  }
};

const IMAGE_RESOLUTIONS = [
  { label:"Small (512×512)", w:512, h:512 },
  { label:"Medium (1024×1024)", w:1024, h:1024 },
  { label:"Large (1920×1080)", w:1920, h:1080 },
  { label:"4K (3840×2160)", w:3840, h:2160 }
];

/* ---------- Token Estimation Functions ---------- */

function estimateImageTokens(provider, resolution, count) {
  if (count <= 0) return 0;
  const res = IMAGE_RESOLUTIONS[resolution] || IMAGE_RESOLUTIONS[1];
  let tokensPerImage = 0;
  if (provider === 'google' || provider === 'xai') {
    // Gemini/Grok: 258 tokens per 768×768 tile
    const tiles = Math.max(1, Math.ceil(res.w / 768) * Math.ceil(res.h / 768));
    tokensPerImage = tiles * 258;
  } else if (provider === 'openai') {
    // OpenAI: low=85, high=85 + 170×tiles (512px tiles after scaling to 768 short side)
    const shortSide = Math.min(res.w, res.h);
    const longSide = Math.max(res.w, res.h);
    const scale = 768 / shortSide;
    const scaledLong = Math.min(Math.round(longSide * scale), 2048);
    const tilesX = Math.ceil(768 / 512);
    const tilesY = Math.ceil(scaledLong / 512);
    tokensPerImage = 85 + (170 * tilesX * tilesY);
  } else if (provider === 'anthropic') {
    // Claude: ~(w×h)/750 tokens
    tokensPerImage = Math.round((res.w * res.h) / 750);
  }
  return tokensPerImage * count;
}

function estimateAudioTokens(provider, durationMinutes) {
  if (durationMinutes <= 0) return 0;
  const seconds = durationMinutes * 60;
  const providerData = MODELS[provider];
  if (providerData.audioTokensPerSec > 0) {
    return Math.round(providerData.audioTokensPerSec * seconds);
  }
  return 0;
}

function estimateVideoTokens(provider, durationMinutes) {
  if (durationMinutes <= 0) return 0;
  const seconds = durationMinutes * 60;
  const providerData = MODELS[provider];
  if (providerData.videoTokensPerSec > 0) {
    return Math.round(providerData.videoTokensPerSec * seconds);
  }
  return 0;
}

function wordsToTokens(words) {
  return Math.round(words * 1.33);
}

/* ---------- Cost Calculation ---------- */

function calculateCost(model, provider, inputTokens, outputTokens, useCache, useBatch, longContext) {
  let inputPrice = model.input;
  let outputPrice = model.output;

  // Long context pricing
  if (longContext && model.inputLong && inputTokens > (model.longThreshold || 200000)) {
    inputPrice = model.inputLong;
    outputPrice = model.outputLong;
  }

  // Cached input pricing
  if (useCache && model.cachedInput) {
    inputPrice = model.cachedInput;
  }

  let inputCost = (inputTokens / 1000000) * inputPrice;
  let outputCost = (outputTokens / 1000000) * outputPrice;
  let total = inputCost + outputCost;

  // Batch discount
  if (useBatch && model.batch) {
    total *= 0.5;
    inputCost *= 0.5;
    outputCost *= 0.5;
  }

  return { inputCost, outputCost, total };
}

/* ---------- UI Functions ---------- */

let selectedProvider = 'google';
let selectedModelIndex = 0;
let comparisonMode = false;

function initCalculator() {
  renderProviderTabs();
  renderModelSelector();
  renderImageResolutions();
  attachListeners();
  recalculate();
}

function renderProviderTabs() {
  const container = document.getElementById('provider-tabs');
  if (!container) return;
  container.innerHTML = '';
  Object.entries(MODELS).forEach(([key, prov]) => {
    const btn = document.createElement('button');
    btn.className = 'calc-provider-tab' + (key === selectedProvider ? ' active' : '');
    btn.dataset.provider = key;
    btn.innerHTML = `<span class="provider-icon">${prov.icon}</span><span class="provider-name">${prov.name}</span>`;
    btn.addEventListener('click', () => {
      selectedProvider = key;
      selectedModelIndex = 0;
      renderProviderTabs();
      renderModelSelector();
      updateMultimodalVisibility();
      recalculate();
    });
    container.appendChild(btn);
  });
}

function renderModelSelector() {
  const sel = document.getElementById('model-select');
  if (!sel) return;
  sel.innerHTML = '';
  const models = MODELS[selectedProvider].models;
  models.forEach((m, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = `${m.name} — $${m.input}/$${m.output} per 1M tokens`;
    if (i === selectedModelIndex) opt.selected = true;
    sel.appendChild(opt);
  });
}

function renderImageResolutions() {
  const sel = document.getElementById('image-resolution');
  if (!sel) return;
  sel.innerHTML = '';
  IMAGE_RESOLUTIONS.forEach((r, i) => {
    const opt = document.createElement('option');
    opt.value = i;
    opt.textContent = r.label;
    if (i === 1) opt.selected = true;
    sel.appendChild(opt);
  });
}

function updateMultimodalVisibility() {
  const models = MODELS[selectedProvider].models;
  const model = models[selectedModelIndex];
  const audioGroup = document.getElementById('audio-group');
  const videoGroup = document.getElementById('video-group');
  const audioNote = document.getElementById('audio-note');
  const videoNote = document.getElementById('video-note');

  const provData = MODELS[selectedProvider];
  const hasAudio = model.aud && provData.audioTokensPerSec > 0;
  const hasVideo = model.vid && provData.videoTokensPerSec > 0;

  if (audioGroup) audioGroup.style.opacity = hasAudio ? '1' : '0.4';
  if (videoGroup) videoGroup.style.opacity = hasVideo ? '1' : '0.4';
  if (audioNote) audioNote.style.display = hasAudio ? 'none' : 'block';
  if (videoNote) videoNote.style.display = hasVideo ? 'none' : 'block';
}

function attachListeners() {
  const fields = ['input-words','output-words','image-count','image-resolution','audio-minutes','video-minutes','requests-per-day','use-cache','use-batch'];
  fields.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener('input', recalculate);
    if (el) el.addEventListener('change', recalculate);
  });
  const modelSel = document.getElementById('model-select');
  if (modelSel) modelSel.addEventListener('change', (e) => {
    selectedModelIndex = parseInt(e.target.value);
    updateMultimodalVisibility();
    recalculate();
  });
  const compBtn = document.getElementById('compare-btn');
  if (compBtn) compBtn.addEventListener('click', toggleComparison);
}

function getInputValues() {
  return {
    inputWords: parseInt(document.getElementById('input-words')?.value) || 0,
    outputWords: parseInt(document.getElementById('output-words')?.value) || 0,
    imageCount: parseInt(document.getElementById('image-count')?.value) || 0,
    imageRes: parseInt(document.getElementById('image-resolution')?.value) || 1,
    audioMin: parseFloat(document.getElementById('audio-minutes')?.value) || 0,
    videoMin: parseFloat(document.getElementById('video-minutes')?.value) || 0,
    requestsPerDay: parseInt(document.getElementById('requests-per-day')?.value) || 1,
    useCache: document.getElementById('use-cache')?.checked || false,
    useBatch: document.getElementById('use-batch')?.checked || false
  };
}

function recalculate() {
  const v = getInputValues();
  const model = MODELS[selectedProvider].models[selectedModelIndex];

  // Token breakdown
  const textInputTokens = wordsToTokens(v.inputWords);
  const textOutputTokens = wordsToTokens(v.outputWords);
  const imageTokens = estimateImageTokens(selectedProvider, v.imageRes, v.imageCount);
  const audioTokens = estimateAudioTokens(selectedProvider, v.audioMin);
  const videoTokens = estimateVideoTokens(selectedProvider, v.videoMin);

  const totalInputTokens = textInputTokens + imageTokens + audioTokens + videoTokens;
  const totalOutputTokens = textOutputTokens;
  const longContext = totalInputTokens > (model.longThreshold || Infinity);

  // Cost
  const cost = calculateCost(model, selectedProvider, totalInputTokens, totalOutputTokens, v.useCache, v.useBatch, longContext);
  const perRequest = cost.total;
  const daily = perRequest * v.requestsPerDay;
  const monthly = daily * 30;
  const yearly = daily * 365;

  // Standard cost (no discounts)
  const stdCost = calculateCost(model, selectedProvider, totalInputTokens, totalOutputTokens, false, false, longContext);
  const savings = stdCost.total > 0 ? ((1 - cost.total / stdCost.total) * 100) : 0;

  // Update UI
  updateEl('text-input-tokens', formatNum(textInputTokens));
  updateEl('text-output-tokens', formatNum(textOutputTokens));
  updateEl('image-tokens-display', formatNum(imageTokens));
  updateEl('audio-tokens-display', formatNum(audioTokens));
  updateEl('video-tokens-display', formatNum(videoTokens));
  updateEl('total-input-tokens', formatNum(totalInputTokens));
  updateEl('total-output-tokens', formatNum(totalOutputTokens));
  updateEl('total-all-tokens', formatNum(totalInputTokens + totalOutputTokens));

  updateEl('cost-per-request', '$' + formatCost(perRequest));
  updateEl('cost-daily', '$' + formatCost(daily));
  updateEl('cost-monthly', '$' + formatCost(monthly));
  updateEl('cost-yearly', '$' + formatCost(yearly));

  updateEl('savings-pct', savings > 0 ? `Saving ${savings.toFixed(0)}% with optimizations` : 'No optimizations applied');

  // Context usage bar
  const contextPct = Math.min((totalInputTokens / model.context) * 100, 100);
  const bar = document.getElementById('context-bar');
  if (bar) {
    bar.style.width = contextPct + '%';
    bar.className = 'calc-context-fill' + (contextPct > 80 ? ' warning' : '');
  }
  updateEl('context-usage-text', `${formatNum(totalInputTokens)} / ${formatNum(model.context)} tokens (${contextPct.toFixed(1)}%)`);

  // Long context warning
  const lcWarn = document.getElementById('long-context-warning');
  if (lcWarn) lcWarn.style.display = longContext ? 'block' : 'none';

  // Update comparison if visible
  if (comparisonMode) renderComparison();
}

function toggleComparison() {
  comparisonMode = !comparisonMode;
  const section = document.getElementById('comparison-section');
  const btn = document.getElementById('compare-btn');
  if (section) section.style.display = comparisonMode ? 'block' : 'none';
  if (btn) btn.textContent = comparisonMode ? '✕ Hide Comparison' : '⚡ Compare All Models';
  if (comparisonMode) renderComparison();
}

function renderComparison() {
  const tbody = document.getElementById('comparison-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const v = getInputValues();

  let rows = [];
  Object.entries(MODELS).forEach(([provKey, prov]) => {
    prov.models.forEach(model => {
      const textIn = wordsToTokens(v.inputWords);
      const textOut = wordsToTokens(v.outputWords);
      const imgTok = estimateImageTokens(provKey, v.imageRes, v.imageCount);
      const audTok = estimateAudioTokens(provKey, v.audioMin);
      const vidTok = estimateVideoTokens(provKey, v.videoMin);
      const totalIn = textIn + imgTok + audTok + vidTok;
      const totalOut = textOut;
      const longCtx = totalIn > (model.longThreshold || Infinity);
      const cost = calculateCost(model, provKey, totalIn, totalOut, false, false, longCtx);
      const batchCost = calculateCost(model, provKey, totalIn, totalOut, false, true, longCtx);
      const cacheCost = calculateCost(model, provKey, totalIn, totalOut, true, false, longCtx);
      rows.push({ provider: prov.name, icon: prov.icon, color: prov.color, model: model.name, tier: model.tier, totalIn, totalOut, cost: cost.total, batchCost: batchCost.total, cacheCost: cacheCost.total, daily: cost.total * v.requestsPerDay, monthly: cost.total * v.requestsPerDay * 30 });
    });
  });

  rows.sort((a, b) => a.cost - b.cost);

  rows.forEach((r, i) => {
    const tr = document.createElement('tr');
    if (i === 0) tr.className = 'cheapest-row';
    tr.innerHTML = `
      <td><span style="color:${r.color}">${r.icon}</span> ${r.provider}</td>
      <td><strong>${r.model}</strong><span class="tier-badge tier-${r.tier}">${r.tier}</span></td>
      <td class="num">${formatNum(r.totalIn + r.totalOut)}</td>
      <td class="num cost-cell">${r.cost < 0.0001 && r.cost > 0 ? '<$0.0001' : '$' + formatCost(r.cost)}</td>
      <td class="num">${'$' + formatCost(r.daily)}</td>
      <td class="num">${'$' + formatCost(r.monthly)}</td>
      <td class="num">${'$' + formatCost(r.cacheCost)}</td>
      <td class="num">${'$' + formatCost(r.batchCost)}</td>
    `;
    tbody.appendChild(tr);
  });
}

/* ---------- Helpers ---------- */
function formatNum(n) { return n.toLocaleString('en-US'); }
function formatCost(n) { return n < 0.01 && n > 0 ? n.toFixed(6) : n < 1 ? n.toFixed(4) : n < 100 ? n.toFixed(2) : n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}); }
function updateEl(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

document.addEventListener('DOMContentLoaded', initCalculator);
