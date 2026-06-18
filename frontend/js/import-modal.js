/**
 * Import Modal — CSV upload with drag-drop, field mapping preview, progress.
 *
 * Flow: Select platform → Upload CSV → Preview mapping → Confirm → Import → Done
 */
const ImportModal = {
  state: {
    step: 0,
    platformId: null,
    platformCode: null,
    file: null,
    previewData: null,   // from /api/upload-csv/preview
    importResult: null,  // from /api/upload-csv
  },

  async open() {
    this.reset();
    this.show();
    this.goStep(0);
    await this.loadPlatforms();
  },

  close() {
    document.getElementById('import-overlay')?.classList.remove('visible');
    document.getElementById('import-modal')?.classList.remove('visible');
  },

  show() {
    document.getElementById('import-overlay')?.classList.add('visible');
    document.getElementById('import-modal')?.classList.add('visible');
  },

  reset() {
    this.state = { step: 0, platformId: null, platformCode: null, file: null, previewData: null, importResult: null };
    const fi = document.getElementById('im-file-input');
    if (fi) fi.value = '';
    const fn = document.getElementById('im-file-name');
    if (fn) fn.textContent = '';
    const fill = document.getElementById('im-progress-fill');
    if (fill) fill.style.width = '0%';
  },

  /* ── Platform — fetch directly from API, not App.state ─── */
  async loadPlatforms() {
    const container = document.getElementById('im-platforms');
    if (!container) return;

    container.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">⏳ 加载平台列表...</div>';

    try {
      const res = await fetch('http://localhost:8000/api/platforms');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const platforms = await res.json();
      if (!platforms.length) throw new Error('平台列表为空');

      const icons = { amazon: '🛒', tiktok: '🎵', shopee: '🛍️' };
      const currentCode = window.App?.state?.currentPlatform?.code || null;

      container.innerHTML = platforms.map(p => {
        const isDefault = p.code === currentCode;
        // Auto-select if it matches current dashboard platform
        if (isDefault && !this.state.platformId) {
          this.state.platformId = p.id;
          this.state.platformCode = p.code;
        }
        return `
          <div class="im-platform-opt ${isDefault ? 'selected' : ''}"
               data-id="${p.id}" data-code="${p.code}"
               onclick="ImportModal.selectPlatform(${p.id}, '${p.code}')">
            <span class="im-plat-icon">${icons[p.code] || '📊'}</span>
            ${p.name}
          </div>
        `;
      }).join('');

      this.updateBtn();

    } catch (err) {
      container.innerHTML = `
        <div style="text-align:center;padding:20px;color:var(--danger);">
          ❌ 无法加载平台列表<br>
          <small>${this.esc(err.message)}</small><br>
          <button class="btn btn-secondary" onclick="ImportModal.loadPlatforms()" style="margin-top:10px">重试</button>
        </div>
      `;
    }
  },

  selectPlatform(id, code) {
    this.state.platformId = id;
    this.state.platformCode = code;
    document.querySelectorAll('.im-platform-opt').forEach(el =>
      el.classList.toggle('selected', parseInt(el.dataset.id) === id)
    );
    this.updateBtn();
  },

  /* ── File ──────────────────────────────────────────────── */
  setupDropzone() {
    const dz = document.getElementById('im-dropzone');
    const fi = document.getElementById('im-file-input');
    if (!dz || !fi) return;
    dz.onclick = () => fi.click();
    dz.ondragover = (e) => { e.preventDefault(); dz.classList.add('dragover'); };
    dz.ondragleave = () => dz.classList.remove('dragover');
    dz.ondrop = (e) => {
      e.preventDefault(); dz.classList.remove('dragover');
      if (e.dataTransfer.files[0]) this.setFile(e.dataTransfer.files[0]);
    };
    fi.onchange = () => { if (fi.files[0]) this.setFile(fi.files[0]); };
  },

  setFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) { alert('仅支持 CSV 文件'); return; }
    this.state.file = file;
    document.getElementById('im-file-name').textContent =
      '📄 ' + file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
    this.updateBtn();
  },

  /* ── Steps ─────────────────────────────────────────────── */
  goStep(n) {
    this.state.step = n;
    ['im-step-platform', 'im-step-file', 'im-step-mapping', 'im-step-progress', 'im-step-result']
      .forEach((id, i) => {
        const el = document.getElementById(id);
        if (el) el.style.display = i === n ? 'block' : 'none';
      });

    const btn = document.getElementById('im-btn-action');
    if (!btn) return;
    btn.style.display = (n === 3) ? 'none' : '';

    if (n === 0) { btn.textContent = '下一步'; btn.onclick = () => this.nextStep(); }
    else if (n === 1) { this.setupDropzone(); btn.textContent = '预览字段映射'; btn.onclick = () => this.doPreview(); }
    else if (n === 2) { btn.textContent = '确认导入'; btn.onclick = () => this.doImport(); }
    else if (n === 4) {
      btn.textContent = '完成';
      btn.style.display = '';
      btn.onclick = () => {
        this.close();
        if (window.App) {
          window.App.refreshDashboard();
          const dates = this.state.importResult?.imported_dates || [];
          if (dates.length > 0) {
            const picker = document.getElementById('date-picker');
            if (picker) {
              // Extend min backward if imported data is older than current min
              if (dates[0] < picker.min) picker.min = dates[0];
              // Max is capped at real-world today by App.updateDateDisplay()
            }
          }
        }
      };
    }
    this.updateBtn();
  },

  updateBtn() {
    const btn = document.getElementById('im-btn-action');
    if (!btn) return;
    if (this.state.step === 0) btn.disabled = !this.state.platformId;
    else if (this.state.step === 1) btn.disabled = !this.state.file;
    else btn.disabled = false;
  },

  nextStep() {
    if (!this.state.platformId) { alert('请先选择平台'); return; }
    this.goStep(1);
  },

  /* ── Preview: send to /api/upload-csv/preview ──────────── */
  async doPreview() {
    if (!this.state.file) { alert('请先选择文件'); return; }

    this.goStep(3);
    this.setProgress(20, '解析 CSV 表头...');

    try {
      const form = new FormData();
      form.append('platform_id', this.state.platformId);
      form.append('file', this.state.file);

      this.setProgress(50, '匹配字段映射...');
      const res = await fetch('http://localhost:8000/api/upload-csv/preview', { method: 'POST', body: form });
      const data = await res.json();
      this.setProgress(100, '');

      if (!res.ok) {
        this.showResult(false, data.detail || '预览失败');
        return;
      }

      this.state.previewData = data;
      this.renderMapping(data);
      this.goStep(2);

    } catch (err) {
      this.showResult(false, '预览失败: ' + err.message);
    }
  },

  /* ── Import: send to /api/upload-csv ───────────────────── */
  async doImport() {
    this.goStep(3);
    this.setProgress(30, '导入中...');

    try {
      const form = new FormData();
      form.append('platform_id', this.state.platformId);
      form.append('file', this.state.file);

      this.setProgress(70, '写入数据库...');
      const res = await fetch('http://localhost:8000/api/upload-csv', { method: 'POST', body: form });
      const data = await res.json();
      this.setProgress(100, '');

      if (!res.ok) {
        this.showResult(false, data.detail || '导入失败');
        return;
      }

      this.state.importResult = data;
      this.showResult(true, data);

    } catch (err) {
      this.showResult(false, '导入失败: ' + err.message);
    }
  },

  /* ── Mapping Table ─────────────────────────────────────── */
  renderMapping(data) {
    const container = document.getElementById('im-mapping-table');
    if (!container) return;

    const mapping = data.column_mapping || {};
    const entries = Object.entries(mapping);
    if (entries.length === 0) {
      container.innerHTML = '<div class="im-result error">未识别到任何已知字段，请检查 CSV 列名</div>';
      return;
    }

    container.innerHTML = `
      <table class="im-mapping-table">
        <thead><tr><th>CSV 列名</th><th></th><th>系统指标</th></tr></thead>
        <tbody>
          ${entries.map(([csvCol, info]) => `
            <tr>
              <td>${this.esc(csvCol)}</td>
              <td class="map-arrow">→</td>
              <td class="map-target">${this.esc(info.metric_name)} (${this.esc(info.metric_key)})</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      <div class="im-mapping-summary">
        识别到 ${entries.length} 个字段映射，将导入 ${data.data_rows} 行数据
        ${(data.unmapped_columns || []).length > 0 ? '<br>未识别列: ' + data.unmapped_columns.map(c => this.esc(c)).join(', ') : ''}
      </div>
    `;
  },

  /* ── Result ────────────────────────────────────────────── */
  showResult(ok, data) {
    this.goStep(4);
    const container = document.getElementById('im-result-content');
    if (!container) return;

    if (!ok) {
      container.innerHTML = `
        <div class="im-result-icon">❌</div>
        <div class="im-result error">${this.esc(typeof data === 'string' ? data : (data.detail || ''))}</div>
      `;
      return;
    }

    const r = data;
    const hasErrors = r.error_count > 0;
    container.innerHTML = `
      <div class="im-result-icon">${hasErrors ? '⚠️' : '✅'}</div>
      <div class="im-result ${hasErrors ? 'error' : 'success'}">
        <strong>${hasErrors ? '导入完成（部分成功）' : '导入成功！'}</strong><br><br>
        平台: ${r.platform}<br>
        插入: ${r.inserted} 条 &nbsp;|&nbsp; 更新: ${r.updated} 条 &nbsp;|&nbsp; 跳过: ${r.skipped} 条<br>
        覆盖日期: ${r.imported_date_count} 天
        ${hasErrors ? `
          <ul class="im-result-errors">
            ${(r.errors || []).map(e => '<li>' + this.esc(e) + '</li>').join('')}
            ${r.error_count > (r.errors || []).length ? '<li>... 还有 ' + (r.error_count - (r.errors || []).length) + ' 条错误</li>' : ''}
          </ul>
        ` : ''}
      </div>
    `;
  },

  /* ── Helpers ───────────────────────────────────────────── */
  setProgress(pct, text) {
    const fill = document.getElementById('im-progress-fill');
    const txt = document.getElementById('im-progress-text');
    if (fill) fill.style.width = pct + '%';
    if (txt) txt.textContent = text;
  },

  esc(str) {
    const div = document.createElement('div');
    div.textContent = String(str);
    return div.innerHTML;
  },
};
