/**
 * Formula Editor — Custom metric creation form with autocomplete and validation.
 */
const FormulaEditor = {
  state: {
    availableKeys: [],    // [{key, name, unit}] for suggestions
    selectedKey: null,    // currently highlighted suggestion index
  },

  /**
   * Open the formula creation modal.
   * @param {Array} availableMetrics - all metrics for current platform
   * @param {Function} onSave - callback(metric) after successful creation
   */
  open(availableMetrics, onSave) {
    this.state.availableKeys = availableMetrics
      .filter(m => m.is_builtin || !m.is_deleted)
      .map(m => ({ key: m.key, name: m.name, unit: m.unit }));

    const overlay = document.getElementById('formula-modal-overlay');
    const modal = document.getElementById('formula-modal');
    if (!overlay || !modal) {
      this.createModal();
      return this.open(availableMetrics, onSave);
    }

    this._onSave = onSave;
    this.resetForm();
    overlay.classList.add('visible');
    modal.classList.add('visible');

    // Focus name input
    setTimeout(() => document.getElementById('fm-name')?.focus(), 200);
  },

  close() {
    document.getElementById('formula-modal-overlay')?.classList.remove('visible');
    document.getElementById('formula-modal')?.classList.remove('visible');
  },

  resetForm() {
    const nameEl = document.getElementById('fm-name');
    const keyEl = document.getElementById('fm-key');
    const formulaEl = document.getElementById('fm-formula');
    const typeEl = document.getElementById('fm-type');
    const unitEl = document.getElementById('fm-unit');
    const resultEl = document.getElementById('fm-result');
    const suggestBox = document.getElementById('fm-suggestions');

    if (nameEl) nameEl.value = '';
    if (keyEl) keyEl.value = 'custom_';
    if (formulaEl) formulaEl.value = '';
    if (typeEl) typeEl.value = 'number';
    if (unitEl) unitEl.value = '';
    if (resultEl) resultEl.innerHTML = '';
    if (suggestBox) suggestBox.innerHTML = '';
    this.state.selectedKey = null;
  },

  /* ── Create Modal DOM ─────────────────────────────────── */
  createModal() {
    const html = `
      <div id="formula-modal-overlay" class="formula-modal-overlay" onclick="FormulaEditor.close()"></div>
      <div id="formula-modal" class="formula-modal">
        <div class="fm-header">
          <h3>➕ 创建自定义指标</h3>
          <button class="btn-close" onclick="FormulaEditor.close()">✕</button>
        </div>
        <div class="fm-body">
          <div class="fm-field">
            <label>指标名称 <span class="required">*</span></label>
            <input id="fm-name" type="text" placeholder="例如：毛利" oninput="FormulaEditor.onNameChange()" maxlength="100">
          </div>
          <div class="fm-field">
            <label>指标 Key <span class="required">*</span></label>
            <input id="fm-key" type="text" placeholder="custom_" value="custom_" maxlength="100">
            <span class="fm-hint">必须以 custom_ 开头</span>
          </div>
          <div class="fm-field">
            <label>计算公式 <span class="required">*</span></label>
            <div class="fm-formula-wrapper">
              <textarea id="fm-formula" rows="2" placeholder="例如：gmv * (1 - refund_rate/100) - cogs"
                        oninput="FormulaEditor.onFormulaInput()"
                        onkeydown="FormulaEditor.onFormulaKeydown(event)"></textarea>
              <button class="btn-insert-metric" onclick="FormulaEditor.toggleSuggestions()" title="插入指标变量">
                📋 插入指标
              </button>
            </div>
            <div id="fm-suggestions" class="fm-suggestions"></div>
          </div>
          <div class="fm-row">
            <div class="fm-field fm-half">
              <label>数据类型</label>
              <select id="fm-type">
                <option value="number">数字 (number)</option>
                <option value="percentage">百分比 (percentage)</option>
                <option value="currency">货币 (currency)</option>
              </select>
            </div>
            <div class="fm-field fm-half">
              <label>单位</label>
              <input id="fm-unit" type="text" placeholder="如：USD, %, 分" maxlength="20">
            </div>
          </div>
          <div id="fm-result" class="fm-result"></div>
        </div>
        <div class="fm-footer">
          <button class="btn btn-secondary" onclick="FormulaEditor.close()">取消</button>
          <button class="btn btn-secondary" onclick="FormulaEditor.validate()">🔍 验证公式</button>
          <button class="btn btn-primary" onclick="FormulaEditor.save()">💾 保存</button>
        </div>
      </div>
    `;

    const container = document.createElement('div');
    container.innerHTML = html;
    document.body.appendChild(container);
  },

  /* ── Name → Key auto-generation ───────────────────────── */
  onNameChange() {
    const nameEl = document.getElementById('fm-name');
    const keyEl = document.getElementById('fm-key');
    if (!nameEl || !keyEl) return;
    // Auto-generate key from name (pinyin-like: just use a sanitized version)
    const name = nameEl.value.trim();
    if (name && keyEl.value === 'custom_') {
      const slug = name
        .replace(/[^\w一-鿿]/g, '_')
        .replace(/_{2,}/g, '_')
        .toLowerCase();
      keyEl.value = 'custom_' + (slug || 'metric');
    }
  },

  /* ── Formula Input + Autocomplete ─────────────────────── */
  onFormulaInput() {
    const formulaEl = document.getElementById('fm-formula');
    const suggestBox = document.getElementById('fm-suggestions');
    if (!formulaEl || !suggestBox) return;

    const text = formulaEl.value;
    const cursorPos = formulaEl.selectionStart;

    // Find the partial token at cursor position
    const beforeCursor = text.slice(0, cursorPos);
    const tokenMatch = beforeCursor.match(/([a-zA-Z_]\w*)$/);
    const partial = tokenMatch ? tokenMatch[1].toLowerCase() : '';

    if (partial.length >= 1) {
      const matches = this.state.availableKeys.filter(k =>
        k.key.toLowerCase().includes(partial)
      ).slice(0, 8);

      if (matches.length > 0) {
        this.state.selectedKey = 0;
        suggestBox.innerHTML = matches.map((k, i) => `
          <div class="fm-suggestion-item ${i === 0 ? 'selected' : ''}"
               data-key="${k.key}"
               data-idx="${i}"
               onmousedown="FormulaEditor.insertKey('${k.key}')">
            <span class="sugg-key">${k.key}</span>
            <span class="sugg-name">${k.name}</span>
            <span class="sugg-unit">${k.unit || ''}</span>
          </div>
        `).join('');
        suggestBox.style.display = 'block';
        return;
      }
    }

    // Also show suggestions when user types '$'
    if (beforeCursor.endsWith('$')) {
      const matches = this.state.availableKeys.slice(0, 8);
      if (matches.length > 0) {
        this.state.selectedKey = 0;
        suggestBox.innerHTML = matches.map((k, i) => `
          <div class="fm-suggestion-item ${i === 0 ? 'selected' : ''}"
               data-key="${k.key}"
               data-idx="${i}"
               onmousedown="FormulaEditor.insertKey('${k.key}')">
            <span class="sugg-key">${k.key}</span>
            <span class="sugg-name">${k.name}</span>
          </div>
        `).join('');
        suggestBox.style.display = 'block';
        return;
      }
    }

    suggestBox.style.display = 'none';
    this.state.selectedKey = null;
  },

  onFormulaKeydown(e) {
    const suggestBox = document.getElementById('fm-suggestions');
    if (!suggestBox || suggestBox.style.display === 'none') return;

    const items = suggestBox.querySelectorAll('.fm-suggestion-item');
    if (items.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this.state.selectedKey = Math.min((this.state.selectedKey ?? -1) + 1, items.length - 1);
      this.updateSuggestionHighlight(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this.state.selectedKey = Math.max((this.state.selectedKey ?? 1) - 1, 0);
      this.updateSuggestionHighlight(items);
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      const selected = items[this.state.selectedKey ?? 0];
      if (selected) {
        this.insertKey(selected.dataset.key);
      }
    } else if (e.key === 'Escape') {
      suggestBox.style.display = 'none';
      this.state.selectedKey = null;
    }
  },

  updateSuggestionHighlight(items) {
    items.forEach((item, i) => {
      item.classList.toggle('selected', i === this.state.selectedKey);
    });
  },

  insertKey(key) {
    const formulaEl = document.getElementById('fm-formula');
    const suggestBox = document.getElementById('fm-suggestions');
    if (!formulaEl) return;

    const text = formulaEl.value;
    const cursorPos = formulaEl.selectionStart;
    const beforeCursor = text.slice(0, cursorPos);

    // Replace the partial token or '$' trigger
    let newBefore;
    const tokenMatch = beforeCursor.match(/([a-zA-Z_]\w*)$/);
    if (tokenMatch) {
      newBefore = beforeCursor.slice(0, -tokenMatch[1].length) + key;
    } else if (beforeCursor.endsWith('$')) {
      newBefore = beforeCursor.slice(0, -1) + key;
    } else {
      newBefore = beforeCursor + ' ' + key;
    }

    const newText = newBefore + text.slice(cursorPos);
    formulaEl.value = newText;
    formulaEl.focus();
    const newPos = newBefore.length;
    formulaEl.setSelectionRange(newPos, newPos);

    if (suggestBox) suggestBox.style.display = 'none';
    this.state.selectedKey = null;

    // Trigger input to re-validate
    this.onFormulaInput();
  },

  toggleSuggestions() {
    const suggestBox = document.getElementById('fm-suggestions');
    if (!suggestBox) return;

    if (suggestBox.style.display === 'block') {
      suggestBox.style.display = 'none';
    } else {
      const matches = this.state.availableKeys.slice(0, 8);
      if (matches.length > 0) {
        suggestBox.innerHTML = matches.map((k, i) => `
          <div class="fm-suggestion-item ${i === 0 ? 'selected' : ''}"
               data-key="${k.key}" data-idx="${i}"
               onmousedown="FormulaEditor.insertKey('${k.key}')">
            <span class="sugg-key">${k.key}</span>
            <span class="sugg-name">${k.name}</span>
          </div>
        `).join('');
        suggestBox.style.display = 'block';
        this.state.selectedKey = 0;
      }
    }
  },

  /* ── Validate Formula via Backend ─────────────────────── */
  async validate() {
    const formula = document.getElementById('fm-formula')?.value.trim();
    const resultEl = document.getElementById('fm-result');
    if (!resultEl) return;

    if (!formula) {
      resultEl.innerHTML = '<div class="fm-error">请输入计算公式</div>';
      return;
    }

    // Get current platform ID from the main app
    const platformId = window.App?.state?.currentPlatform?.id;
    if (!platformId) {
      resultEl.innerHTML = '<div class="fm-error">请先选择平台</div>';
      return;
    }

    resultEl.innerHTML = '<div class="fm-validating">⏳ 验证中...</div>';

    try {
      const res = await api.validateFormula({ formula, platform_id: platformId });
      if (res.valid) {
        const sampleStr = res.sample_result !== null
          ? `样本计算结果: <strong>${res.sample_result}</strong>`
          : '';
        resultEl.innerHTML = `
          <div class="fm-success">
            ✅ 公式有效！
            ${sampleStr}
            <div class="fm-vars">检测变量: ${res.variables.map(v => `<code>${v}</code>`).join(', ')}</div>
          </div>
        `;
      } else {
        resultEl.innerHTML = `<div class="fm-error">❌ ${res.error}</div>`;
      }
    } catch (err) {
      resultEl.innerHTML = `<div class="fm-error">❌ 验证失败: ${err.message}</div>`;
    }
  },

  /* ── Save Custom Metric ───────────────────────────────── */
  async save() {
    const name = document.getElementById('fm-name')?.value.trim();
    const key = document.getElementById('fm-key')?.value.trim();
    const formula = document.getElementById('fm-formula')?.value.trim();
    const dataType = document.getElementById('fm-type')?.value || 'number';
    const unit = document.getElementById('fm-unit')?.value.trim() || '';
    const resultEl = document.getElementById('fm-result');

    // Client-side validation
    if (!name) return this.showFieldError('fm-name', '请输入指标名称');
    if (!key || !key.startsWith('custom_')) return this.showFieldError('fm-key', 'Key 必须以 custom_ 开头');
    if (key === 'custom_') return this.showFieldError('fm-key', '请输入完整的 key');
    if (!formula) return this.showFieldError('fm-formula', '请输入计算公式');
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key)) {
      return this.showFieldError('fm-key', 'Key 只能包含字母、数字和下划线');
    }

    const platformId = window.App?.state?.currentPlatform?.id;
    if (!platformId) {
      if (resultEl) resultEl.innerHTML = '<div class="fm-error">请先选择平台</div>';
      return;
    }

    // Save button shows loading state
    const saveBtn = document.querySelector('.fm-footer .btn-primary');
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = '⏳ 保存中...';
    }

    try {
      const metric = await api.createMetric({
        name,
        key,
        formula,
        data_type: dataType,
        unit,
        platform_id: platformId,
      });

      // Add to current dashboard
      if (window.App?.state?.dashboard) {
        await api.addWidget(window.App.state.dashboard.id, {
          metric_id: metric.id,
        });
      }

      this.close();

      // Refresh the app
      if (window.App) {
        window.App.state.allMetrics = await api.getPlatformMetrics(platformId);
        await window.App.refreshDashboard();
        if (window.App.state.dashboard) {
          window.App.renderMetricPanel();
        }
      }

      if (this._onSave) this._onSave(metric);
    } catch (err) {
      if (resultEl) resultEl.innerHTML = `<div class="fm-error">❌ 保存失败: ${err.message}</div>`;
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 保存';
      }
    }
  },

  showFieldError(fieldId, msg) {
    const el = document.getElementById(fieldId);
    if (el) {
      el.style.borderColor = '#EF4444';
      el.focus();
      setTimeout(() => { el.style.borderColor = ''; }, 2000);
    }
    const resultEl = document.getElementById('fm-result');
    if (resultEl) resultEl.innerHTML = `<div class="fm-error">${msg}</div>`;
  },
};
