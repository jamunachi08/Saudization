frappe.pages['executive-scorecard'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Executive Scorecard'),
    single_column: true
  });

  $(wrapper).find('.layout-main-section').addClass('saud-exec-wrap');

  const $container = $('<div class="saud-exec-root"></div>').appendTo(page.body);
  const $kpis = $('<div class="saud-kpis"></div>').appendTo($container);
  const $trendSection = $('<div class="saud-section"><h4>'+__('Monthly Trend')+'</h4><div class="saud-chart" id="saud-exec-trend"></div></div>').appendTo($container);
  const $riskSection = $('<div class="saud-section"><h4>'+__('Holding / Subsidiary Risk')+'</h4><div class="saud-chart" id="saud-exec-risk"></div></div>').appendTo($container);
  const $riskTable = $('<div class="saud-mini-table" id="saud-exec-risk-table"></div>').appendTo($riskSection);
  const $posSection = $('<div class="saud-section"><h4>'+__('Top Risky Positions')+'</h4><div class="saud-mini-table" id="saud-exec-risky-positions"></div></div>').appendTo($container);

  let trendChart = null;
  let riskChart = null;

  const fg = new frappe.ui.FieldGroup({
    fields: [
      {fieldname:'holding_company', label:__('Holding Company'), fieldtype:'Link', options:'Company'},
      {fieldname:'company', label:__('Company'), fieldtype:'Link', options:'Company'},
      {fieldname:'branch', label:__('Branch'), fieldtype:'Link', options:'Branch'},
      {fieldname:'as_on_date', label:__('As On Date'), fieldtype:'Date', default: frappe.datetime.get_today()},
      {fieldname:'months_back', label:__('Months Back'), fieldtype:'Int', default: 12}
    ],
    body: page.body
  });
  fg.make();

  function badge(status){
    const s = (status || '').toLowerCase();
    const map = {green:'#22c55e', amber:'#f59e0b', red:'#ef4444'};
    const color = map[s] || '#64748b';
    return `<span class="saud-status" style="background:${color}20;color:${color}">${frappe.utils.escape_html(status || '-')}</span>`;
  }

  function setKpis(data){
    $kpis.empty();
    const cards = [
      {label:__('Overall Saudization %'), value: (data.overall?.saudization_percent ?? '-') + (data.overall?.saudization_percent != null ? '%' : ''), sub: badge(data.overall?.status)},
      {label:__('Target %'), value: (data.overall?.target_percent ?? '-') + (data.overall?.target_percent != null ? '%' : ''), sub: __('Policy Driven (Annual)')},
      {label:__('MoM Change'), value: (data.overall?.mom_change_percent ?? '-') + (data.overall?.mom_change_percent != null ? ' pp' : ''), sub: __('vs previous month')},
      {label:__('Headcount (Total)'), value: data.overall?.total_employees ?? '-', sub: __('Saudi: {0} | Non-Saudi: {1}', [data.overall?.saudi_employees ?? '-', data.overall?.non_saudi_employees ?? '-'])},
      {label:__('Highest Risk Entity'), value: data.risk?.highest_risk ?? '-', sub: badge(data.risk?.highest_risk_status)},
      {label:__('Variance (Actual - Target)'), value: (data.overall?.variance_percent ?? '-') + (data.overall?.variance_percent != null ? ' pp' : ''), sub: __('Gap to target')}
    ];

    cards.forEach(c => {
      const $card = $(
        `<div class="saud-kpi">
          <div class="label">${frappe.utils.escape_html(c.label)}</div>
          <div class="value">${frappe.utils.escape_html(String(c.value))}</div>
          <div class="sub">${c.sub || ''}</div>
        </div>`
      );
      $kpis.append($card);
    });
  }

  function drawTrend(series){
    const el = document.getElementById('saud-exec-trend');
    if (!el) return;
    $(el).empty();
    if (!series || !series.labels || !series.labels.length){
      $(el).html(`<div class="text-muted">${__('No trend data')}</div>`);
      return;
    }
    trendChart = new frappe.Chart(el, {
      data: {
        labels: series.labels,
        datasets: [
          {name: __('Actual %'), values: series.actual_values},
          {name: __('Target %'), values: series.target_values}
        ]
      },
      type: 'line',
      height: 260,
      colors: undefined
    });
  }

  function drawRiskChart(risk){
    const el = document.getElementById('saud-exec-risk');
    if (!el) return;
    $(el).empty();
    if (!risk || !risk.labels || !risk.labels.length){
      $(el).html(`<div class="text-muted">${__('No holding comparison data')}</div>`);
      return;
    }
    riskChart = new frappe.Chart(el, {
      data: {
        labels: risk.labels,
        datasets: [
          {name: __('Variance (pp)'), values: risk.variance_values}
        ]
      },
      type: 'bar',
      height: 260,
      colors: undefined
    });
  }

  function renderRiskTable(rows, as_on_date){
    const $t = $('#saud-exec-risk-table');
    if (!rows || !rows.length){
      $t.empty();
      return;
    }
    const html = [
      '<table class="saud-hold-table">',
      '<thead><tr>',
      `<th>${__('Company')}</th>`,
      `<th>${__('Actual %')}</th>`,
      `<th>${__('Target %')}</th>`,
      `<th>${__('Variance')}</th>`,
      `<th>${__('Status')}</th>`,
      '</tr></thead><tbody>'
    ];
    rows.forEach(r => {
      const c = r.company || '';
      html.push('<tr>');
      html.push(`<td><a class="saud-link" data-company="${frappe.utils.escape_html(c)}">${frappe.utils.escape_html(c || '-') }</a></td>`);
      html.push(`<td>${(r.saudization_percent ?? 0)}%</td>`);
      html.push(`<td>${(r.target_percent ?? '-')}${r.target_percent!=null ? '%' : ''}</td>`);
      html.push(`<td>${(r.variance_percent ?? '-')}${r.variance_percent!=null ? ' pp' : ''}</td>`);
      html.push(`<td>${badge(r.status)}</td>`);
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    $t.html(html.join(''));

    $t.find('a.saud-link').on('click', function(e){
      e.preventDefault();
      const company = $(this).data('company');
      frappe.route_options = { company, as_on_date };
      frappe.set_route('company-drilldown');
    });
  }

  function renderRiskyPositions(rows){
    const $t = $('#saud-exec-risky-positions');
    if (!rows || !rows.length){
      $t.html(`<div class="text-muted">${__('Select a Company to view risky designations')}</div>`);
      return;
    }
    const html = [
      '<table class="saud-hold-table">',
      '<thead><tr>',
      `<th>${__('Designation')}</th>`,
      `<th>${__('Headcount')}</th>`,
      `<th>${__('Actual %')}</th>`,
      `<th>${__('Variance')}</th>`,
      `<th>${__('Status')}</th>`,
      '</tr></thead><tbody>'
    ];
    rows.forEach(r => {
      const des = r.designation || '';
      html.push('<tr>');
      html.push(`<td><a class="saud-link-riskpos" data-des="${frappe.utils.escape_html(des)}">${frappe.utils.escape_html(des || '-') }</a></td>`);
      html.push(`<td>${r.total_employees ?? 0}</td>`);
      html.push(`<td>${(r.saudization_percent ?? 0)}%</td>`);
      html.push(`<td>${(r.variance_percent ?? '-')}${r.variance_percent!=null ? ' pp' : ''}</td>`);
      html.push(`<td>${badge(r.status)}</td>`);
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    $t.html(html.join(''));

    // Drill: risky designation -> employee list
    $t.find('a.saud-link-riskpos').on('click', function(e){
      e.preventDefault();
      const v = fg.get_values();
      const designation = $(this).data('des');
      // If CEO is viewing holding-level, we still need a company context.
      // In refresh(), we compute company_for_positions; store it on wrapper for click.
      const company = (page.__risk_company_for_positions || v.company || null);
      frappe.route_options = {
        company: company,
        as_on_date: v.as_on_date,
        branch: v.branch,
        designation: designation
      };
      frappe.set_route('employee-drilldown');
    });
  }

  function refresh(){
    const v = fg.get_values();
    frappe.call({
      method: 'saudization_dashboard.api.get_executive_scorecard',
      args: v,
      callback: (r) => {
        const data = r.message || {};
        setKpis(data);
        drawTrend(data.trend);
        drawRiskChart(data.holding);
        renderRiskTable(data.holding?.rows, (fg.get_values()||{}).as_on_date);

        // Risky designations list: prioritize explicit Company filter, fallback to highest risk entity
        const company_for_positions = v.company || data.risk?.highest_risk || null;
        page.__risk_company_for_positions = company_for_positions;
        if (company_for_positions) {
          frappe.call({
            method: 'saudization_dashboard.api.get_top_risky_positions',
            args: {
              company: company_for_positions,
              as_on_date: v.as_on_date,
              branch: v.branch,
              top_n: 10,
              min_headcount: 3
            },
            callback: (rr) => renderRiskyPositions(rr.message?.items || [])
          });
        } else {
          renderRiskyPositions([]);
        }
      }
    });
  }

  page.set_primary_action(__('Refresh'), refresh);

  fg.on('change', () => {
    // soft refresh
    refresh();
  });

  refresh();
};
