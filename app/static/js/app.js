/**
 * TikTok Auto DM Pro - Interactive Web Application
 */

const API = {
  status: '/api/bot/status',
  start: '/api/bot/start',
  stop: '/api/bot/stop',
  restart: '/api/bot/restart',
  screenshot: '/api/bot/screenshot',
  captureScreenshot: '/api/bot/screenshot/capture',
  settings: '/api/bot/settings',
  rules: '/api/rules',
  ruleToggle: (id) => `/api/rules/${id}/toggle`,
  ruleDetail: (id) => `/api/rules/${id}`,
  testRule: '/api/rules/test',
  logs: '/api/logs',
  stats: '/api/logs/stats'
};

let statusPollTimer = null;
let screenshotTimer = null;
let currentEditingRuleId = null;
let lastBotIsActive = false;

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initBotControls();
  initRules();
  initSimulator();
  initSettingsForm();

  // Initial data load
  refreshStatus();
  refreshStats();
  loadRules();
  loadLogs();

  // Try to show screenshot on initial load (even if bot was previously running)
  updateScreenshotImage();

  // Polling intervals
  statusPollTimer = setInterval(refreshStatus, 4000);
  setInterval(refreshStats, 8000);
  setInterval(loadLogs, 6000);
});

// Toast notification helper
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}</span> <div>${message}</div>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Navigation Tabs
function initTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetTab = document.getElementById(targetId);
      if (targetTab) targetTab.classList.add('active');

      if (targetId === 'tabLogs') loadLogs();
      if (targetId === 'tabRules') loadRules();
    });
  });
}

// Bot Control & Status
async function refreshStatus() {
  try {
    const res = await fetch(API.status);
    const json = await res.json();
    if (json.status === 'success') {
      const data = json.data;
      updateStatusUI(data);
    }
  } catch (err) {
    console.error('Error fetching bot status:', err);
  }
}

function updateStatusUI(data) {
  const statusPill = document.getElementById('botStatusPill');
  const statusText = document.getElementById('botStatusText');
  const statusMsg = document.getElementById('botStatusMessage');
  const btnStart = document.getElementById('btnStartBot');
  const btnStop = document.getElementById('btnStopBot');
  const uptimeElem = document.getElementById('botUptime');
  const qrBanner = document.getElementById('qrScanBanner');
  const browserContainer = document.getElementById('browserViewContainer');

  statusPill.className = 'status-pill';
  const isNeedsLogin = data.status === 'NEEDS_LOGIN';
  const needsVerification = data.status === 'NEEDS_VERIFICATION';

  // Toggle QR scan banner & pulsing border
  if (qrBanner) {
    if (isNeedsLogin) {
      qrBanner.classList.add('visible');
    } else {
      qrBanner.classList.remove('visible');
    }
  }
  if (browserContainer) {
    if (isNeedsLogin) {
      browserContainer.classList.add('qr-mode');
    } else {
      browserContainer.classList.remove('qr-mode');
    }
  }

  if (data.status === 'RUNNING') {
    statusPill.classList.add('running');
    statusText.textContent = 'ONLINE (24/7)';
    btnStart.style.display = 'none';
    btnStop.style.display = 'inline-flex';
  } else if (isNeedsLogin) {
    statusPill.classList.add('needs-login');
    statusText.textContent = 'BUTUH SCAN QR TIKTOK';
    btnStart.style.display = 'none';
    btnStop.style.display = 'inline-flex';
  } else if (needsVerification) {
    statusPill.classList.add('needs-login');
    statusText.textContent = 'VERIFIKASI DIPERLUKAN';
    btnStart.style.display = 'none';
    btnStop.style.display = 'inline-flex';
  } else if (data.status === 'STARTING') {
    statusPill.classList.add('needs-login');
    statusText.textContent = 'MEMULAI BROWSER...';
    btnStart.style.display = 'none';
    btnStop.style.display = 'inline-flex';
  } else {
    statusText.textContent = 'OFFLINE (BERHENTI)';
    btnStart.style.display = 'inline-flex';
    btnStop.style.display = 'none';
  }

  statusMsg.textContent = data.status_message || '-';

  if (uptimeElem) {
    if (data.is_running && data.uptime_seconds > 0) {
      const hrs = Math.floor(data.uptime_seconds / 3600);
      const mins = Math.floor((data.uptime_seconds % 3600) / 60);
      const secs = data.uptime_seconds % 60;
      uptimeElem.textContent = `${hrs}j ${mins}m ${secs}dtk`;
    } else {
      uptimeElem.textContent = '0j 0m 0dtk';
    }
  }

  // Manage screenshot polling timer based on bot activity
  const isActive = data.is_running || data.status === 'NEEDS_LOGIN' || data.status === 'STARTING';
  if (isActive && !lastBotIsActive) {
    // Bot just became active — start screenshot polling every 5 seconds
    updateScreenshotImage();
    if (screenshotTimer) clearInterval(screenshotTimer);
    screenshotTimer = setInterval(updateScreenshotImage, 5000);
  } else if (!isActive && lastBotIsActive) {
    // Bot just stopped — take one final screenshot update then stop polling
    updateScreenshotImage();
    if (screenshotTimer) {
      clearInterval(screenshotTimer);
      screenshotTimer = null;
    }
  } else if (data.has_screenshot && !screenshotTimer && !isActive) {
    // Screenshot exists from previous session, show it once
    updateScreenshotImage();
  }
  lastBotIsActive = isActive;
}

function updateScreenshotImage() {
  const imgElem = document.getElementById('browserScreenshotImg');
  const placeholder = document.getElementById('browserPlaceholder');
  const timeElem = document.getElementById('screenshotTimestamp');

  imgElem.src = `${API.screenshot}?t=${Date.now()}`;
  imgElem.onload = () => {
    imgElem.style.display = 'block';
    placeholder.style.display = 'none';
    if (timeElem) timeElem.textContent = new Date().toLocaleTimeString();
  };
  imgElem.onerror = () => {
    imgElem.style.display = 'none';
    placeholder.style.display = 'flex';
  };
}

function initBotControls() {
  const btnStart = document.getElementById('btnStartBot');
  const btnStop = document.getElementById('btnStopBot');
  const btnRestart = document.getElementById('btnRestartBot');
  const btnRefreshShot = document.getElementById('btnRefreshScreenshot');

  btnStart.addEventListener('click', async () => {
    btnStart.disabled = true;
    showToast('Memulai TikTok bot di latar belakang...', 'info');
    try {
      const res = await fetch(API.start, { method: 'POST' });
      const json = await res.json();
      showToast(json.message, 'success');
      await refreshStatus();
    } catch (e) {
      showToast('Gagal memulai bot: ' + e, 'error');
    } finally {
      btnStart.disabled = false;
    }
  });

  btnStop.addEventListener('click', async () => {
    btnStop.disabled = true;
    showToast('Menghentikan bot...', 'info');
    try {
      const res = await fetch(API.stop, { method: 'POST' });
      const json = await res.json();
      showToast(json.message, 'info');
      await refreshStatus();
    } catch (e) {
      showToast('Gagal menghentikan bot: ' + e, 'error');
    } finally {
      btnStop.disabled = false;
    }
  });

  btnRestart.addEventListener('click', async () => {
    if (!confirm('Restart bot TikTok sekarang?')) return;
    showToast('Merestart bot...', 'info');
    try {
      const res = await fetch(API.restart, { method: 'POST' });
      const json = await res.json();
      showToast(json.message, 'success');
      await refreshStatus();
    } catch (e) {
      showToast('Gagal restart bot: ' + e, 'error');
    }
  });

  btnRefreshShot.addEventListener('click', async () => {
    try {
      await fetch(API.captureScreenshot, { method: 'POST' });
      updateScreenshotImage();
      showToast('Screenshot browser diperbarui', 'info');
    } catch (e) {
      updateScreenshotImage();
    }
  });
}

// Stats
async function refreshStats() {
  try {
    const res = await fetch(API.stats);
    const json = await res.json();
    if (json.status === 'success') {
      const s = json.stats;
      document.getElementById('statSentToday').textContent = s.sent_today;
      document.getElementById('statTotalSent').textContent = s.total_sent;
      document.getElementById('statActiveRules').textContent = s.active_rules;
      document.getElementById('statUniqueUsers').textContent = s.unique_users;
    }
  } catch (err) {
    console.error('Error fetching stats:', err);
  }
}

// Rules CRUD
async function loadRules() {
  try {
    const res = await fetch(API.rules);
    const json = await res.json();
    if (json.status === 'success') {
      renderRulesTable(json.rules);
    }
  } catch (e) {
    console.error('Error loading rules:', e);
  }
}

function renderRulesTable(rules) {
  const tbody = document.getElementById('rulesTableBody');
  tbody.innerHTML = '';

  if (!rules || rules.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 30px; color: var(--text-muted);">Belum ada aturan keyword. Klik tombol "+ Tambah Keyword Baru" di atas!</td></tr>`;
    return;
  }

  rules.forEach(rule => {
    const tr = document.createElement('tr');
    
    // Match type badge style
    let badgeClass = 'badge-cyan';
    if (rule.match_type === 'exact') badgeClass = 'badge-pink';
    if (rule.match_type === 'regex') badgeClass = 'badge-yellow';

    // Format cooldown
    let cdText = `${rule.cooldown_seconds} detik`;
    if (rule.cooldown_seconds >= 3600) {
      cdText = `${Math.floor(rule.cooldown_seconds / 3600)} jam`;
    } else if (rule.cooldown_seconds >= 60) {
      cdText = `${Math.floor(rule.cooldown_seconds / 60)} menit`;
    }

    tr.innerHTML = `
      <td>
        <strong style="color: #fff; font-size: 1rem;">"${escapeHtml(rule.keyword)}"</strong>
      </td>
      <td>
        <span class="badge ${badgeClass}">${rule.match_type.toUpperCase()}</span>
      </td>
      <td style="max-width: 320px; white-space: pre-wrap; word-break: break-word; color: #cbd5e1;">
        ${escapeHtml(rule.reply_message)}
      </td>
      <td>
        <span class="badge badge-gray">⏱️ ${cdText}</span>
      </td>
      <td>
        <label class="switch">
          <input type="checkbox" ${rule.is_active ? 'checked' : ''} onchange="toggleRule(${rule.id})">
          <span class="slider"></span>
        </label>
      </td>
      <td>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-secondary btn-sm" onclick="editRule(${rule.id})">✏️ Edit</button>
          <button class="btn btn-danger btn-sm" onclick="deleteRule(${rule.id})">🗑️</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function initRules() {
  const modal = document.getElementById('ruleModal');
  const btnOpenModal = document.getElementById('btnOpenAddRule');
  const btnCloseModal = document.getElementById('btnCloseModal');
  const btnCancelModal = document.getElementById('btnCancelModal');
  const form = document.getElementById('ruleForm');

  btnOpenModal.addEventListener('click', () => {
    currentEditingRuleId = null;
    document.getElementById('modalTitle').textContent = 'Tambah Keyword Auto DM Baru';
    form.reset();
    document.getElementById('ruleCooldown').value = 3600;
    openModal();
  });

  btnCloseModal.addEventListener('click', closeModal);
  btnCancelModal.addEventListener('click', closeModal);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const keyword = document.getElementById('ruleKeyword').value.trim();
    const match_type = document.getElementById('ruleMatchType').value;
    const reply_message = document.getElementById('ruleReply').value.trim();
    const cooldown_seconds = parseInt(document.getElementById('ruleCooldown').value, 10) || 3600;

    const payload = {
      keyword,
      match_type,
      reply_message,
      cooldown_seconds,
      is_active: 1
    };

    try {
      if (currentEditingRuleId) {
        // Edit existing
        const res = await fetch(API.ruleDetail(currentEditingRuleId), {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.status === 'success') {
          showToast('Aturan berhasil diubah', 'success');
        }
      } else {
        // Create new
        const res = await fetch(API.rules, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.status === 'success') {
          showToast('Keyword baru berhasil ditambahkan!', 'success');
        }
      }
      closeModal();
      loadRules();
      refreshStats();
    } catch (err) {
      showToast('Gagal menyimpan aturan: ' + err, 'error');
    }
  });
}

function openModal() {
  const modal = document.getElementById('ruleModal');
  modal.classList.add('show');
}

function closeModal() {
  const modal = document.getElementById('ruleModal');
  modal.classList.remove('show');
  currentEditingRuleId = null;
}

async function toggleRule(id) {
  try {
    const res = await fetch(API.ruleToggle(id), { method: 'POST' });
    const json = await res.json();
    if (json.status === 'success') {
      showToast(`Status keyword diperbarui: ${json.is_active ? 'Aktif' : 'Non-aktif'}`, 'info');
      refreshStats();
    }
  } catch (e) {
    showToast('Gagal mengubah status: ' + e, 'error');
  }
}

async function editRule(id) {
  try {
    const res = await fetch(API.rules);
    const json = await res.json();
    const rule = json.rules.find(r => r.id === id);
    if (!rule) return;

    currentEditingRuleId = id;
    document.getElementById('modalTitle').textContent = 'Edit Aturan Keyword';
    document.getElementById('ruleKeyword').value = rule.keyword;
    document.getElementById('ruleMatchType').value = rule.match_type;
    document.getElementById('ruleReply').value = rule.reply_message;
    document.getElementById('ruleCooldown').value = rule.cooldown_seconds;
    openModal();
  } catch (e) {
    showToast('Gagal memuat detail aturan: ' + e, 'error');
  }
}

async function deleteRule(id) {
  if (!confirm('Apakah Anda yakin ingin menghapus keyword auto DM ini?')) return;
  try {
    const res = await fetch(API.ruleDetail(id), { method: 'DELETE' });
    const json = await res.json();
    if (json.status === 'success') {
      showToast('Keyword berhasil dihapus', 'info');
      loadRules();
      refreshStats();
    }
  } catch (e) {
    showToast('Gagal menghapus: ' + e, 'error');
  }
}

// Simulator Sandbox
function initSimulator() {
  const btnTest = document.getElementById('btnTestRule');
  const testInput = document.getElementById('testInputMessage');
  const resultContainer = document.getElementById('simulatorResult');

  btnTest.addEventListener('click', async () => {
    const message = testInput.value.trim();
    if (!message) {
      showToast('Masukkan contoh pesan uji coba terlebih dahulu', 'error');
      return;
    }

    resultContainer.style.display = 'block';
    resultContainer.innerHTML = '<em>Sedang mencocokkan dengan aturan aktif...</em>';

    try {
      const res = await fetch(API.testRule, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message, username: "farrel_official" })
      });
      const data = await res.json();

      if (data.status === 'matched') {
        const rule = data.matched_rule;
        resultContainer.innerHTML = `
          <div style="color: var(--status-green); font-weight: 700; margin-bottom: 8px;">
            🎉 Cocok dengan Keyword: "${rule.keyword}" (${rule.match_type.toUpperCase()})
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">
            <div class="chat-bubble inbound">
              <strong>User:</strong> ${escapeHtml(data.input_message)}
            </div>
            <div class="chat-bubble outbound">
              <strong>TikTok Bot Auto Reply:</strong><br>${escapeHtml(data.simulated_reply)}
            </div>
          </div>
        `;
      } else {
        resultContainer.innerHTML = `
          <div style="color: var(--status-yellow); font-weight: 600;">
            ⚠️ Tidak ada keyword yang cocok dengan pesan ini.
          </div>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
            Pesan tidak akan memicu balasan otomatis.
          </p>
        `;
      }
    } catch (e) {
      resultContainer.innerHTML = `<span style="color: var(--status-red)">Error: ${e}</span>`;
    }
  });
}

// Logs
async function loadLogs() {
  try {
    const res = await fetch(API.logs);
    const json = await res.json();
    if (json.status === 'success') {
      renderLogsTable(json.logs);
    }
  } catch (e) {
    console.error('Error loading logs:', e);
  }
}

function renderLogsTable(logs) {
  const tbody = document.getElementById('logsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (!logs || logs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color: var(--text-muted);">Belum ada riwayat DM masuk atau balasan terkirim.</td></tr>`;
    return;
  }

  logs.forEach(log => {
    const tr = document.createElement('tr');
    
    let statusBadge = `<span class="badge badge-green">Terkirim</span>`;
    if (log.status === 'cooldown') {
      statusBadge = `<span class="badge badge-yellow">Cooldown</span>`;
    } else if (log.status === 'error') {
      statusBadge = `<span class="badge badge-pink">Error</span>`;
    } else if (log.status === 'rate_limited') {
      statusBadge = `<span class="badge badge-pink">Batas Limit</span>`;
    }

    tr.innerHTML = `
      <td style="color: var(--text-muted); font-size: 0.8rem; white-space: nowrap;">
        ${log.timestamp || '-'}
      </td>
      <td>
        <strong style="color: #fff;">@${escapeHtml(log.chat_username || 'unknown')}</strong>
      </td>
      <td style="color: #cbd5e1; max-width: 220px; word-break: break-word;">
        ${escapeHtml(log.incoming_message || '-')}
      </td>
      <td>
        ${log.matched_keyword ? `<span class="badge badge-cyan">${escapeHtml(log.matched_keyword)}</span>` : '-'}
      </td>
      <td style="color: #e2e8f0; max-width: 260px; word-break: break-word;">
        ${escapeHtml(log.replied_message || '-')}
      </td>
      <td>${statusBadge}</td>
    `;
    tbody.appendChild(tr);
  });
}

const btnClearLogs = document.getElementById('btnClearLogs');
if (btnClearLogs) {
  btnClearLogs.addEventListener('click', async () => {
    if (!confirm('Bersihkan semua riwayat log?')) return;
    try {
      await fetch(API.logs, { method: 'DELETE' });
      showToast('Log aktivitas dibersihkan', 'info');
      loadLogs();
      refreshStats();
    } catch (e) {
      showToast('Gagal membersihkan log: ' + e, 'error');
    }
  });
}

// Settings Form
function initSettingsForm() {
  const form = document.getElementById('settingsForm');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const interval = parseInt(document.getElementById('settingCheckInterval').value, 10);
    const maxDm = parseInt(document.getElementById('settingMaxDm').value, 10);

    try {
      const res = await fetch(API.settings, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          check_interval: interval,
          max_dm_per_hour: maxDm
        })
      });
      const json = await res.json();
      if (json.status === 'success') {
        showToast('Pengaturan bot berhasil disimpan', 'success');
      }
    } catch (e) {
      showToast('Gagal menyimpan pengaturan: ' + e, 'error');
    }
  });
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
