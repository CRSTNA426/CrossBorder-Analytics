/**
 * Insight Engine — Renders rule-based operational insights between charts and health.
 */
const InsightEngine = {
  async render(dashboardId, selectedDate) {
    const container = document.getElementById('insight-section');
    if (!container) return;
    if (!dashboardId) { container.innerHTML = ''; return; }

    try {
      const res = await fetch(
        `http://localhost:8000/api/insights?dashboard_id=${dashboardId}&date=${selectedDate}`
      );
      const data = await res.json();

      if (data.empty) {
        container.innerHTML = `
          <div class="insight-section-box">
            <div class="section-header"><h3>📊 经营洞察</h3></div>
            <div class="insight-empty">暂无数据，导入后可查看洞察</div>
          </div>`;
        return;
      }

      const insights = data.insights || [];
      const score = data.score;
      let html = '<div class="insight-section-box">';

      // Score bar
      if (score) {
        const sc = score.total;
        const ratingColor = sc >= 80 ? 'success' : sc >= 60 ? 'warning' : 'danger';
        html += `
          <div class="section-header">
            <h3>📊 经营洞察</h3>
            <span class="alert-badge ${ratingColor}">${sc}/100 · ${score.rating}</span>
          </div>
          <div class="insight-score-bar">
            <div class="insight-score-item">
              <span class="score-label">库存健康</span>
              <span class="score-val">${score.inventory}/30</span>
              <div class="score-track"><div class="score-fill" style="width:${score.inventory / 30 * 100}%"></div></div>
            </div>
            <div class="insight-score-item">
              <span class="score-label">广告效率</span>
              <span class="score-val">${score.ad}/30</span>
              <div class="score-track"><div class="score-fill" style="width:${score.ad / 30 * 100}%"></div></div>
            </div>
            <div class="insight-score-item">
              <span class="score-label">利润水平</span>
              <span class="score-val">${score.profit}/40</span>
              <div class="score-track"><div class="score-fill" style="width:${score.profit / 40 * 100}%"></div></div>
            </div>
          </div>`;
      } else {
        html += `<div class="section-header"><h3>📊 经营洞察</h3></div>`;
      }

      // Insight cards
      if (insights.length === 0) {
        html += '<div class="insight-empty">✅ 今日暂无异常，经营状态良好</div>';
      } else {
        html += '<div class="insight-cards">';
        insights.forEach(i => {
          html += `
            <div class="insight-card insight-${i.color}">
              <div class="insight-card-title">${i.title} <span class="insight-priority insight-p-${i.priority}">${i.priority === 'high' ? '高优先' : i.priority === 'medium' ? '中优先' : '低优先'}</span></div>
              <div class="insight-card-body">${this.esc(i.content)}</div>
            </div>`;
        });
        html += '</div>';
      }

      html += '</div>';
      container.innerHTML = html;

    } catch (err) {
      console.error('Insight engine error:', err);
      container.innerHTML = '';
    }
  },

  esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  },
};
