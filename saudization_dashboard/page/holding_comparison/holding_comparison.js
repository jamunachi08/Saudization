frappe.pages['holding-comparison'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Holding vs Subsidiary Comparison'),
    single_column: true
  });

  $(wrapper).find('.layout-main-section').addClass('saud-hold-wrap');

  const $card = $('<div class="saud-hold-card"></div>').appendTo(page.body);
  const $chart = $('<div id="saud-hold-chart"></div>').appendTo($card);
  const $table = $('<div id="saud-hold-table"></div>').appendTo($card);

  let chart = null;

  const fg = new frappe.ui.FieldGroup({
    fields: [
      {fieldname:'holding_company', label:__('Holding Company'), fieldtype:'Link', options:'Company', reqd:1},
      {fieldname:'as_on_date', label:__('As On Date'), fieldtype:'Date', default: frappe.datetime.get_today()}
    ],
    body: page.body
  });
  fg.make();

  function pill(status){
    const s = (status || '').toLowerCase();
    const map = {green:'#22c55e', amber:'#f59e0b', red:'#ef4444'};
    const color = map[s] || '#64748b';
    return `<span class="saud-pill" style="background:${color}20;color:${color}">${frappe.utils.escape_html(status || '-') }</span>`;
  }

  function renderTable(rows){
    if (!rows || !rows.length){
      $table.html(`<div class="text-muted">${__('No subsidiaries found')}</div>`);
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
      html.push('<tr>');
      const c = r.company || '';
      html.push(`<td><a class="saud-link" data-company="${frappe.utils.escape_html(c)}">${frappe.utils.escape_html(c || '-') }</a></td>`);
      html.push(`<td>${(r.actual_percent ?? '-')}${r.actual_percent!=null ? '%' : ''}</td>`);
      html.push(`<td>${(r.target_percent ?? '-')}${r.target_percent!=null ? '%' : ''}</td>`);
      html.push(`<td>${(r.variance_percent ?? '-')}</td>`);
      html.push(`<td>${pill(r.status)}</td>`);
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    $table.html(html.join(''));

    // Drill: Company -> Company Drilldown page
    $table.find('a.saud-link').on('click', function(e){
      e.preventDefault();
      const company = $(this).data('company');
      const v = fg.get_values();
      frappe.route_options = {
        company: company,
        as_on_date: v.as_on_date
      };
      frappe.set_route('company-drilldown');
    });
  }

  function renderChart(payload){
    const el = document.getElementById('saud-hold-chart');
    $(el).empty();
    if (!payload || !payload.labels || !payload.labels.length){
      $(el).html(`<div class="text-muted">${__('No comparison data')}</div>`);
      return;
    }
    chart = new frappe.Chart(el, {
      data: {
        labels: payload.labels,
        datasets: [
          {name: __('Actual %'), values: payload.actual_values},
          {name: __('Target %'), values: payload.target_values}
        ]
      },
      type: 'bar',
      height: 260,
      barOptions: { stacked: false }
    });
  }

  function refresh(){
    const v = fg.get_values();
    frappe.call({
      method: 'saudization_dashboard.api.get_holding_comparison',
      args: v,
      callback: (r) => {
        const data = r.message || {};
        renderChart(data.chart);
        renderTable(data.rows);
      }
    });
  }

  page.set_primary_action(__('Refresh'), refresh);
  fg.on('change', refresh);
  refresh();
};
