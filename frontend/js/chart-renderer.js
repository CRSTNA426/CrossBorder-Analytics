/**
 * ECharts rendering wrapper.
 */
const ChartRenderer = {
  instances: {},

  /**
   * Render a line chart for trend data.
   * @param {string} domId - DOM element ID
   * @param {object} trendData - { points: [{date, values: {key: val}}], metric_keys: [...] }
   * @param {object} metricMetaMap - { key: { name, unit, data_type } }
   */
  renderTrendChart(domId, trendData, metricMetaMap) {
    const dom = document.getElementById(domId);
    if (!dom) return;

    // Dispose old instance
    if (this.instances[domId]) {
      this.instances[domId].dispose();
    }

    const chart = echarts.init(dom);
    this.instances[domId] = chart;

    const dates = trendData.points.map(p => p.date);
    const keys = trendData.metric_keys;
    const colors = ['#4F8CF7', '#34D399', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];

    const series = keys.map((key, i) => {
      const meta = metricMetaMap[key] || {};
      return {
        name: meta.name || key,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: colors[i % colors.length] },
        itemStyle: { color: colors[i % colors.length] },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: colors[i % colors.length] + '30' },
            { offset: 1, color: colors[i % colors.length] + '05' },
          ]),
        },
        data: trendData.points.map(p => p.values[key] ?? null),
      };
    });

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1F2937',
        borderColor: '#374151',
        textStyle: { color: '#F9FAFB', fontSize: 12 },
      },
      legend: {
        bottom: 0,
        textStyle: { color: '#9CA3AF', fontSize: 11 },
        itemWidth: 12,
        itemHeight: 8,
      },
      grid: { left: '3%', right: '4%', top: 12, bottom: 30, containLabel: true },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#374151' } },
        axisTick: { show: false },
        axisLabel: {
          color: '#9CA3AF',
          fontSize: 10,
          formatter: (v) => v.slice(5), // MM-DD
        },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#1F2937' } },
        axisLabel: { color: '#9CA3AF', fontSize: 10 },
      },
      series,
    });

    // Responsive resize
    window.addEventListener('resize', () => chart.resize());
  },

  /**
   * Render a simple bar chart.
   */
  renderBarChart(domId, categories, values, name) {
    const dom = document.getElementById(domId);
    if (!dom) return;

    if (this.instances[domId]) {
      this.instances[domId].dispose();
    }

    const chart = echarts.init(dom);
    this.instances[domId] = chart;

    chart.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: '#1F2937',
        borderColor: '#374151',
        textStyle: { color: '#F9FAFB', fontSize: 12 },
      },
      grid: { left: '3%', right: '4%', top: 12, bottom: 20, containLabel: true },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { color: '#9CA3AF', fontSize: 10, rotate: 30 },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#1F2937' } },
        axisLabel: { color: '#9CA3AF', fontSize: 10 },
      },
      series: [{
        name,
        type: 'bar',
        data: values,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#4F8CF7' },
            { offset: 1, color: '#2563EB' },
          ]),
        },
      }],
    });

    window.addEventListener('resize', () => chart.resize());
  },

  disposeAll() {
    Object.keys(this.instances).forEach(key => {
      this.instances[key].dispose();
      delete this.instances[key];
    });
  },
};
