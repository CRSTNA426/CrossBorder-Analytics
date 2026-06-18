/**
 * CrossBorder Analytics — Main Application Controller
 */
const App = {
  // Fixed lower bound: allow browsing any date, missing data shows "-"
  MIN_DATE: '2020-01-01',

  state: {
    platforms: [],
    currentPlatform: null,
    dashboard: null,
    allMetrics: [],
    dashboardMetrics: [],
    trendData: null,
    selectedDate: '',   // set at init
    todayShanghai: '',  // Asia/Shanghai real-world today
  },

  /* ================================================================
   *  INITIALIZATION
   * ================================================================ */
  async init() {
    // Today in Asia/Shanghai timezone (not UTC, not user-local)
    this.state.todayShanghai = this._getShanghaiToday();

    // Default to today or the latest seeded date (MAX_DATA_DATE),
    // whichever is earlier — so we never default to a future date
    // with no data, but also never show a stale date if today has data.
    const today = this.state.todayShanghai;
    this.state.selectedDate = today;

    try {
      this.state.platforms = await api.getPlatforms();
      if (this.state.platforms.length > 0) {
        await this.selectPlatform(this.state.platforms[0]);
      }
    } catch (err) {
      console.error('Init failed:', err);
      this.showError('无法连接到后端服务，请确认服务器已启动 (localhost:8000)');
    }
  },

  /**
   * Get today's date string (YYYY-MM-DD) in Asia/Shanghai timezone.
   * Uses Intl.DateTimeFormat so it works regardless of user's local TZ.
   */
  _getShanghaiToday() {
    const now = new Date();
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(now);
    // en-CA outputs YYYY-MM-DD order: year, literal, month, literal, day
    const y = parts.find(p => p.type === 'year').value;
    const m = parts.find(p => p.type === 'month').value;
    const d = parts.find(p => p.type === 'day').value;
    return `${y}-${m}-${d}`;
  },

  /**
   * Format a Date object to YYYY-MM-DD using Asia/Shanghai timezone.
   */
  _formatShanghai(d) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(d);
    const y = parts.find(p => p.type === 'year').value;
    const m = parts.find(p => p.type === 'month').value;
    const day = parts.find(p => p.type === 'day').value;
    return `${y}-${m}-${day}`;
  },

  /* ================================================================
   *  PLATFORM SWITCHING
   * ================================================================ */
  async selectPlatform(platform) {
    this.state.currentPlatform = platform;
    this.state.dashboard = null;
    this.state.allMetrics = [];
    this.state.dashboardMetrics = [];

    // Highlight active tab
    document.querySelectorAll('.platform-tab').forEach(el => {
      el.classList.toggle('active', el.dataset.code === platform.code);
    });

    // Load platform metrics
    this.state.allMetrics = await api.getPlatformMetrics(platform.id);

    // Try to load existing dashboard for this platform, or create one
    const dashboards = await api.listDashboards();
    const existing = dashboards.find(d => d.platform_id === platform.id);
    if (existing) {
      this.state.dashboard = existing;
    } else {
      // Auto-create with default metrics
      const defaultMetrics = await api.getDefaultMetrics(platform.id);
      this.state.dashboard = await api.createDashboard({
        name: `${platform.name} Dashboard`,
        platform_id: platform.id,
        metric_ids: defaultMetrics.map(m => m.id),
      });
    }

    await this.refreshDashboard();
    this.renderPlatformTabs();
    this.renderMetricPanel();
  },

  /* ================================================================
   *  DATA REFRESH
   * ================================================================ */
  async refreshDashboard() {
    if (!this.state.dashboard) return;

    try {
      const data = await api.getDashboardData(this.state.dashboard.id, this.state.selectedDate);
      this.state.dashboardMetrics = data.metrics || [];

      // Fetch trend data for visible line-chart metrics
      const lineKeys = this.state.dashboardMetrics
        .filter(m => m.widget_type === 'line')
        .map(m => m.metric_key);
      if (lineKeys.length > 0) {
        this.state.trendData = await api.getTrendData(
          this.state.dashboard.id,
          lineKeys.join(','),
          30
        );
      } else {
        // Default: always fetch trend for key overview metrics
        const trendKeys = ['gmv', 'orders', 'acos'];
        this.state.trendData = await api.getTrendData(
          this.state.dashboard.id,
          trendKeys.join(','),
          30
        );
      }

      this.renderDashboard();
    } catch (err) {
      console.error('Data refresh failed:', err);
      this.showError('数据加载失败: ' + err.message);
    }
  },

  /* ================================================================
   *  RENDER: PLATFORM TABS
   * ================================================================ */
  renderPlatformTabs() {
    const container = document.getElementById('platform-tabs');
    if (!container) return;
    container.innerHTML = this.state.platforms.map(p => `
      <button class="platform-tab ${p.id === this.state.currentPlatform?.id ? 'active' : ''}"
              data-code="${p.code}"
              onclick="App.selectPlatform(App.state.platforms.find(pl=>pl.id===${p.id}))">
        <span class="platform-icon">${this.getIcon(p.code)}</span>
        ${p.name}
      </button>
    `).join('');
  },

  getIcon(code) {
    const icons = { amazon: '🛒', tiktok: '🎵', shopee: '🛍️' };
    return icons[code] || '📊';
  },

  /* ================================================================
   *  RENDER: DASHBOARD (KPIs + Charts + Inventory Table)
   * ================================================================ */
  renderDashboard() {
    this.renderKpiCards();
    this.renderCharts();
    this.renderHealthModule();
    this.updateDateDisplay();
  },

  /* ── KPI Cards ─────────────────────────────────────────── */
  renderKpiCards() {
    const grid = document.getElementById('kpi-grid');
    if (!grid) return;

    const metrics = this.state.dashboardMetrics;
    if (metrics.length === 0) {
      grid.innerHTML = '<div class="empty-state">暂无指标，请点击"编辑指标"添加</div>';
      return;
    }

    // If ALL metrics have null values → database has no daily_data at all
    const allNull = metrics.every(m => m.value === null || m.value === undefined);
    if (allNull) {
      grid.innerHTML = `
        <div class="welcome-state">
          <div class="welcome-icon">📋</div>
          <div class="welcome-title">暂无运营数据</div>
          <div class="welcome-subtitle">
            请通过右上角 <strong>📤 导入数据</strong> 上传 CSV，或在终端运行：<br>
            <code id="seed-cmd">python run.py --seed</code>
            <button class="btn-copy" onclick="App.copySeedCmd()" title="复制命令">📋</button>
          </div>
        </div>`;
      return;
    }

    grid.innerHTML = metrics.map(m => this.buildKpiCard(m)).join('');
  },

  copySeedCmd() {
    const code = document.getElementById('seed-cmd');
    if (!code) return;
    navigator.clipboard.writeText(code.textContent).then(() => {
      const btn = document.querySelector('.btn-copy');
      if (btn) { btn.textContent = '✅'; setTimeout(() => { btn.textContent = '📋'; }, 1500); }
    }).catch(() => { /* fallback: ignore */ });
  },

  buildKpiCard(metric) {
    const value = metric.value;
    const formatted = this.formatValue(value, metric.data_type, metric.unit);
    const changeClass = this.getChangeClass(metric);

    return `
      <div class="kpi-card" data-key="${metric.metric_key}">
        <div class="kpi-header">
          <span class="kpi-name">${metric.name}</span>
          <span class="kpi-category-tag ${metric.category}">${this.categoryLabel(metric.category)}</span>
        </div>
        <div class="kpi-value ${changeClass}">${formatted}</div>
        <div class="kpi-footer">
          <span class="kpi-date">${this.state.selectedDate}</span>
          <span class="kpi-unit">${metric.unit}</span>
        </div>
      </div>
    `;
  },

  formatValue(val, dataType, unit) {
    if (val === null || val === undefined) return '-';
    switch (dataType) {
      case 'currency':
        return '$' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
      case 'percentage':
        return Number(val).toFixed(1) + '%';
      case 'number':
        return Number(val).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 1 });
      default:
        return Number(val).toLocaleString();
    }
  },

  getChangeClass(metric) {
    // Colour-code certain metrics based on thresholds
    const val = metric.value;
    if (val === null || val === undefined) return 'neutral';
    switch (metric.metric_key) {
      case 'acos':
        return val > 35 ? 'danger' : val > 25 ? 'warning' : 'success';
      case 'refund_rate':
        return val > 6 ? 'danger' : val > 4 ? 'warning' : 'success';
      case 'conversion_rate':
        return val < 5 ? 'danger' : val < 10 ? 'warning' : 'success';
      default:
        return 'neutral';
    }
  },

  categoryLabel(cat) {
    const labels = {
      overview: '概览', traffic: '流量', conversion: '转化',
      order: '订单', inventory: '库存', profit: '利润', custom: '自定义'
    };
    return labels[cat] || cat;
  },

  /* ── Charts Section ────────────────────────────────────── */
  renderCharts() {
    const container = document.getElementById('charts-section');
    if (!container) return;

    // Always clear to avoid stale chart boxes from previous platform
    ChartRenderer.disposeAll();
    container.innerHTML = '';

    const trendData = this.state.trendData;
    if (!trendData || !trendData.points || trendData.points.length === 0) {
      return;
    }

    // Build metric meta map from dashboard metrics
    const metricMetaMap = {};
    this.state.dashboardMetrics.forEach(m => {
      metricMetaMap[m.metric_key] = {
        name: m.name,
        unit: m.unit,
        data_type: m.data_type,
      };
    });

    // Build the trend chart box
    this._buildTrendChartBox(container, trendData, metricMetaMap);
  },

  _buildTrendChartBox(container, trendData, metricMetaMap) {
    const domId = 'chart-trend-main';

    // Filter to keys that actually exist in the dashboard
    const dashKeys = new Set(this.state.dashboardMetrics.map(m => m.metric_key));
    const trendKeys = (trendData.metric_keys || []).filter(k => dashKeys.has(k));
    // Limit to a reasonable set of core metrics for readability
    const coreKeys = trendKeys.filter(k =>
      ['gmv', 'orders', 'acos', 'conversion_rate', 'refund_rate',
       'content_gmv', 'video_views', 'live_views',
       'cod_orders', 'chat_response_rate', 'nfr_rate'
      ].includes(k)
    );
    const displayKeys = coreKeys.length >= 2 ? coreKeys : trendKeys.slice(0, 4);
    if (displayKeys.length === 0) return;

    const box = document.createElement('div');
    box.className = 'chart-box full-width';
    box.innerHTML = `
      <div class="chart-title">📈 核心指标趋势（30天）</div>
      <div id="${domId}" class="chart-container" style="height:320px"></div>
    `;
    container.appendChild(box);

    ChartRenderer.renderTrendChart(domId, {
      ...trendData,
      metric_keys: displayKeys,
    }, metricMetaMap);
  },

  /* ── Health Module (platform-aware) ────────────────────── */
  renderHealthModule() {
    const code = this.state.currentPlatform?.code;
    if (code === 'amazon') this._renderAmazonHealth();
    else if (code === 'tiktok') this._renderTikTokHealth();
    else if (code === 'shopee') this._renderShopeeHealth();
  },

  _findVal(key) {
    const m = this.state.dashboardMetrics.find(x => x.metric_key === key);
    return m?.value;
  },
  _alert(v, danger, warn) {
    if (v === null || v === undefined) return 'neutral';
    if (danger(v)) return 'danger';
    if (warn && warn(v)) return 'warning';
    return 'success';
  },
  _badge(label, level) {
    return `<span class="alert-badge ${level}">${label}</span>`;
  },
  _card(name, value, unit, level) {
    return `<div class="inv-card ${level ? 'alert-' + level : ''}">
      <div class="inv-name">${name}</div>
      <div class="inv-value">${this.formatValue(value, undefined, unit)}</div>
    </div>`;
  },

  /* ── Amazon: 库存健康 ─────────────────────────────────── */
  _renderAmazonHealth() {
    const container = document.getElementById('inventory-section');
    if (!container) return;

    const days = this._findVal('inventory_days');
    const fq = this._findVal('fulfillable_qty');
    const iq = this._findVal('inbound_qty');
    const ds = this._findVal('daily_sales');

    if (days === undefined && fq === undefined) { container.innerHTML = ''; return; }

    const level = this._alert(days, v => v < 7, v => v < 14);
    container.innerHTML = `
      <div class="section-header"><h3>📦 库存健康</h3>${this._badge(days !== null && days !== undefined ? days + '天' : '-', level)}</div>
      <div class="inventory-grid">
        ${this._card('可售天数', days, '天', level === 'danger' ? 'danger' : level === 'warning' ? 'warning' : 'good')}
        ${this._card('可售库存', fq, '件', '')}
        ${this._card('在途库存', iq, '件', '')}
        ${this._card('日均销量', ds, '件', '')}
      </div>`;
  },

  /* ── TikTok: 物流健康 ─────────────────────────────────── */
  _renderTikTokHealth() {
    const container = document.getElementById('inventory-section');
    if (!container) return;

    const ship = this._findVal('avg_shipping_time');
    const score = this._findVal('shop_score');
    const penalty = this._findVal('penalty_points');

    if (ship === undefined && score === undefined) { container.innerHTML = ''; return; }

    const shipLevel = this._alert(ship, v => v > 48, v => v > 24);
    const scoreLevel = this._alert(score, v => v < 4.5, v => v < 4.7);

    container.innerHTML = `
      <div class="section-header"><h3>📦 物流健康</h3>${this._badge(ship !== null && ship !== undefined ? ship + 'h' : '-', shipLevel)}</div>
      <div class="inventory-grid">
        ${this._card('平均发货时效', ship, '小时', shipLevel === 'danger' ? 'danger' : shipLevel === 'warning' ? 'warning' : 'good')}
        ${this._card('店铺评分', score, '分', scoreLevel === 'danger' ? 'danger' : scoreLevel === 'warning' ? 'warning' : 'good')}
        ${this._card('违规扣分', penalty, '分', penalty > 0 ? 'warning' : 'good')}
        <div class="inv-card" style="grid-column:1/-1;font-size:12px;color:var(--text-muted);padding:8px 12px;">
          ⚠️ 平台要求发货≤48h · 店铺评分<4.5 限流 · 扣分累计会封店
        </div>
      </div>`;
  },

  /* ── Shopee: 履约健康 ─────────────────────────────────── */
  _renderShopeeHealth() {
    const container = document.getElementById('inventory-section');
    if (!container) return;

    const nfr = this._findVal('nfr_rate');
    const late = this._findVal('late_shipment_rate');
    const first = this._findVal('first_attempt_delivery_rate');
    const chat = this._findVal('chat_response_rate');

    if (nfr === undefined && late === undefined && first === undefined && chat === undefined) {
      container.innerHTML = ''; return;
    }

    const nfrLevel = this._alert(nfr, v => v > 5);
    const lateLevel = this._alert(late, v => v > 5);
    const firstLevel = this._alert(first, v => v < 70);
    const chatLevel = this._alert(chat, v => v < 80);

    container.innerHTML = `
      <div class="section-header"><h3>📦 履约健康</h3>${this._badge(nfr !== null && nfr !== undefined ? nfr + '%' : '-', nfrLevel)}</div>
      <div class="inventory-grid">
        ${this._card('不履约率(NFR)', nfr, '%', nfrLevel === 'danger' ? 'danger' : nfrLevel === 'warning' ? 'warning' : 'good')}
        ${this._card('迟发货率', late, '%', lateLevel === 'danger' ? 'danger' : lateLevel === 'warning' ? 'warning' : 'good')}
        ${this._card('一次派送成功率', first, '%', firstLevel === 'danger' ? 'danger' : firstLevel === 'warning' ? 'warning' : 'good')}
        ${this._card('聊聊回复率', chat, '%', chatLevel === 'danger' ? 'danger' : chatLevel === 'warning' ? 'warning' : 'good')}
        <div class="inv-card" style="grid-column:1/-1;font-size:12px;color:var(--text-muted);padding:8px 12px;">
          ⚠️ NFR>5%限流 · 迟发货>5%扣分 · 派送<70%重派成本高 · 聊聊<80%降权
        </div>
      </div>`;
  },

  /* ── Date Display ──────────────────────────────────────── */
  updateDateDisplay() {
    const picker = document.getElementById('date-picker');
    if (picker) {
      picker.value = this.state.selectedDate;
      // Dynamically set bounds every render so imported-data extension sticks
      picker.min = this.MIN_DATE;
      picker.max = this.state.todayShanghai;
    }
  },

  /* ── Date Picker Handler ───────────────────────────────── */
  async onDatePickerChange(value) {
    if (!value) return;
    const today = this.state.todayShanghai;
    if (value < this.MIN_DATE || value > today) return;
    this.state.selectedDate = value;
    await this.refreshDashboard();
  },

  /* ================================================================
   *  METRIC CONFIG PANEL (Slide-out)
   * ================================================================ */
  toggleMetricPanel() {
    const panel = document.getElementById('metric-panel');
    const overlay = document.getElementById('panel-overlay');
    if (!panel || !overlay) return;
    const open = panel.classList.contains('open');
    if (open) {
      panel.classList.remove('open');
      overlay.classList.remove('visible');
    } else {
      this.renderMetricPanel();
      panel.classList.add('open');
      overlay.classList.add('visible');
    }
  },

  async renderMetricPanel() {
    const addedList = document.getElementById('panel-added-list');
    const libraryList = document.getElementById('panel-library-list');
    const deletedList = document.getElementById('panel-deleted-list');
    if (!addedList || !libraryList || !deletedList) return;
    if (!this.state.dashboard) return;

    try {
      // Reload dashboard to get fresh widget list
      const d = await api.getDashboard(this.state.dashboard.id);
      this.state.dashboard = d;

      // Added metrics
      const added = d.widgets || [];
      addedList.innerHTML = added.length === 0
        ? '<div class="panel-empty">暂无指标</div>'
        : added.map(w => this.buildPanelMetricItem(w)).join('');

      // Library: metrics NOT on the dashboard
      const addedIds = new Set(added.map(w => w.metric_id));
      const library = this.state.allMetrics.filter(m => !addedIds.has(m.id) && !m.is_deleted);
      libraryList.innerHTML = library.length === 0
        ? '<div class="panel-empty">指标库为空</div>'
        : library.map(m => this.buildLibraryMetricItem(m)).join('');

      // Deleted custom metrics
      const deleted = await api.listDeletedMetrics(this.state.currentPlatform.id);
      const deletedSection = document.getElementById('panel-deleted-section');
      if (deleted.length > 0 && deletedSection) {
        deletedSection.style.display = 'block';
        deletedList.innerHTML = deleted.map(m => this.buildDeletedMetricItem(m)).join('');
      } else if (deletedSection) {
        deletedSection.style.display = 'none';
      }

      // Bind events
      this.bindPanelEvents();
      this.bindDeletedEvents();
    } catch (err) {
      console.error('Failed to load panel:', err);
    }
  },

  buildPanelMetricItem(widget) {
    const m = widget.metric;
    return `
      <div class="panel-metric-item" data-widget-id="${widget.id}" data-metric-id="${widget.metric_id}">
        <div class="panel-reorder">
          <button class="btn-reorder-up" data-widget-id="${widget.id}" data-position="${widget.position}" title="上移">▲</button>
          <button class="btn-reorder-down" data-widget-id="${widget.id}" data-position="${widget.position}" title="下移">▼</button>
        </div>
        <div class="panel-metric-info">
          <span class="panel-metric-name">${m?.name || 'Unknown'}</span>
          <span class="panel-metric-key">${m?.key || ''}</span>
          ${m && !m.is_builtin ? '<span class="tag-custom">自定义</span>' : ''}
        </div>
        <div class="panel-metric-actions">
          <select class="widget-type-select" data-widget-id="${widget.id}">
            <option value="kpi" ${widget.widget_type === 'kpi' ? 'selected' : ''}>KPI</option>
            <option value="line" ${widget.widget_type === 'line' ? 'selected' : ''}>折线</option>
            <option value="bar" ${widget.widget_type === 'bar' ? 'selected' : ''}>柱状</option>
          </select>
          <button class="btn-icon btn-remove" data-widget-id="${widget.id}" title="从看板移除">✕</button>
        </div>
      </div>
    `;
  },

  buildLibraryMetricItem(metric) {
    return `
      <div class="panel-metric-item library-item" data-metric-id="${metric.id}">
        <div class="panel-metric-info">
          <span class="panel-metric-name">${metric.name}</span>
          <span class="panel-metric-key">${metric.key}</span>
          ${metric.formula ? '<span class="tag-custom">自定义</span>' : ''}
        </div>
        <button class="btn-icon btn-add" data-metric-id="${metric.id}" title="添加到看板">+</button>
      </div>
    `;
  },

  bindPanelEvents() {
    // Remove widget
    document.querySelectorAll('.btn-remove').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const widgetId = parseInt(btn.dataset.widgetId);
        if (!confirm('确定从看板移除此指标？')) return;
        try {
          await api.removeWidget(this.state.dashboard.id, widgetId);
          await this.renderMetricPanel();
          await this.refreshDashboard();
        } catch (err) {
          alert('移除失败: ' + err.message);
        }
      };
    });

    // Add from library
    document.querySelectorAll('.btn-add').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const metricId = parseInt(btn.dataset.metricId);
        try {
          await api.addWidget(this.state.dashboard.id, { metric_id: metricId });
          await this.renderMetricPanel();
          await this.refreshDashboard();
        } catch (err) {
          alert('添加失败: ' + err.message);
        }
      };
    });

    // Widget type change
    document.querySelectorAll('.widget-type-select').forEach(sel => {
      sel.onchange = async (e) => {
        const widgetId = parseInt(sel.dataset.widgetId);
        try {
          await api.updateWidget(this.state.dashboard.id, widgetId, {
            widget_type: sel.value,
          });
          await this.refreshDashboard();
        } catch (err) {
          alert('更新失败: ' + err.message);
        }
      };
    });

    // Drag to reorder (simple: move up/down buttons)
    this.bindReorderButtons();
  },

  bindReorderButtons() {
    document.querySelectorAll('.btn-reorder-up').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const widgetId = parseInt(btn.dataset.widgetId);
        const pos = parseInt(btn.dataset.position);
        if (pos <= 0) return;
        // Swap with previous widget
        const widgets = this.state.dashboard.widgets.filter(w => !w.is_deleted);
        const prev = widgets.find(w => w.position === pos - 1);
        if (prev) {
          await api.updateWidget(this.state.dashboard.id, widgetId, { position: pos - 1 });
          await api.updateWidget(this.state.dashboard.id, prev.id, { position: pos });
        }
        await this.renderMetricPanel();
        await this.refreshDashboard();
      };
    });

    document.querySelectorAll('.btn-reorder-down').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const widgetId = parseInt(btn.dataset.widgetId);
        const pos = parseInt(btn.dataset.position);
        const widgets = this.state.dashboard.widgets.filter(w => !w.is_deleted);
        const maxPos = widgets.length - 1;
        if (pos >= maxPos) return;
        const next = widgets.find(w => w.position === pos + 1);
        if (next) {
          await api.updateWidget(this.state.dashboard.id, widgetId, { position: pos + 1 });
          await api.updateWidget(this.state.dashboard.id, next.id, { position: pos });
        }
        await this.renderMetricPanel();
        await this.refreshDashboard();
      };
    });
  },

  /* ── Deleted Metrics ──────────────────────────────────── */
  buildDeletedMetricItem(metric) {
    return `
      <div class="panel-metric-item deleted-item" data-metric-id="${metric.id}">
        <div class="panel-metric-info">
          <span class="panel-metric-name">${metric.name}</span>
          <span class="panel-metric-key">${metric.key}</span>
          <span class="tag-deleted">已删除</span>
        </div>
        <div class="panel-metric-actions">
          <button class="btn-mini btn-restore" data-metric-id="${metric.id}">恢复</button>
          <button class="btn-mini btn-permanent-delete" data-metric-id="${metric.id}">彻底删除</button>
        </div>
      </div>
    `;
  },

  bindDeletedEvents() {
    // Restore
    document.querySelectorAll('.btn-restore').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const metricId = parseInt(btn.dataset.metricId);
        try {
          await api.restoreMetric(metricId);
          this.state.allMetrics = await api.getPlatformMetrics(this.state.currentPlatform.id);
          await this.renderMetricPanel();
        } catch (err) {
          alert('恢复失败: ' + err.message);
        }
      };
    });

    // Permanent delete
    document.querySelectorAll('.btn-permanent-delete').forEach(btn => {
      btn.onclick = async (e) => {
        e.stopPropagation();
        const metricId = parseInt(btn.dataset.metricId);
        if (!confirm('⚠️ 彻底删除将清空该指标的所有数据，且不可恢复。确定继续？')) return;
        try {
          await api.permanentDeleteMetric(metricId);
          await this.renderMetricPanel();
        } catch (err) {
          alert('彻底删除失败: ' + err.message);
        }
      };
    });
  },

  /* ================================================================
   *  FORMULA EDITOR
   * ================================================================ */
  openFormulaEditor() {
    if (!this.state.currentPlatform) {
      alert('请先选择平台');
      return;
    }
    FormulaEditor.open(this.state.allMetrics, (metric) => {
      console.log('Custom metric created:', metric.key);
    });
  },

  /* ================================================================
   *  ERROR DISPLAY
   * ================================================================ */
  showError(msg) {
    const grid = document.getElementById('kpi-grid');
    if (grid) {
      grid.innerHTML = `<div class="error-state">⚠️ ${msg}</div>`;
    }
  },
};

// ── Boot ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => App.init());
