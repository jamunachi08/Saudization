frappe.pages['saudization-trends'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Saudization Trends'),
    single_column: true
  });

  $(wrapper).find('.layout-main-section').addClass('saud-trends-wrap');

  const $grid = $('<div class="saud-trends-grid"></div>').appendTo(page.body);
  const $card1 = $(`<div class="saud-trend-card"><h4>${__('Saudization % (Actual vs Target)')}</h4><div id="saud-trend-line"></div></div>`).appendTo($grid);
  const $card2 = $(`<div class="saud-trend-card"><h4>${__('Headcount (Saudi vs Non-Saudi)')}</h4><div id="saud-trend-headcount"></div></div>`).appendTo($grid);
  const $card3 = $(`<div class="saud-trend-card"><h4>${__('Branch-level Trend')}</h4><div id="saud-trend-branch"></div></div>`).appendTo($grid);

  let lineChart = null;
  let headChart = null;
  let branchChart = null;

  const fg = new frappe.ui.FieldGroup({
    fields: [
      {fieldname:'holding_company', label:__('Holding Company'), fieldtype:'Link', options:'Company'},
      {fieldname:'company', label:__('Company'), fieldtype:'Link', options:'Company'},
      {fieldname:'branch', label:__('Branch'), fieldtype:'Link', options:'Branch'},
      {fieldname:'months_back', label:__('Months Back'), fieldtype:'Int', default: 24},
      {fieldname:'as_on_date', label:__('As On Date'), fieldtype:'Date', default: frappe.datetime.get_today()}
    ],
    body: page.body
  });
  fg.make();

  function drawLine(d){
    const el = document.getElementById('saud-trend-line');
    if (!d || !d.labels || !d.labels.length){
      $(el).html(`<div class="text-muted">${__('No data')}</div>`);
      return;
    }
    lineChart = new frappe.Chart(el, {
      data: { labels: d.labels, datasets: [
        {name: __('Actual %'), values: d.actual_percent_values},
        {name: __('Target %'), values: d.target_percent_values}
      ]},
      type: 'line',
      height: 260
    });
  }

  function drawHead(d){
    const el = document.getElementById('saud-trend-headcount');
    if (!d || !d.labels || !d.labels.length){
      $(el).html(`<div class="text-muted">${__('No data')}</div>`);
      return;
    }
    headChart = new frappe.Chart(el, {
      data: { labels: d.labels, datasets: [
        {name: __('Saudi'), values: d.saudi_counts},
        {name: __('Non-Saudi'), values: d.non_saudi_counts}
      ]},
      type: 'bar',
      height: 260,
      barOptions: { stacked: true }
    });
  }

  function drawBranch(d){
    const el = document.getElementById('saud-trend-branch');
    if (!d || !d.labels || !d.labels.length || !d.datasets || !d.datasets.length){
      $(el).html(`<div class="text-muted">${__('Select a company to view top branches')}</div>`);
      return;
    }
    branchChart = new frappe.Chart(el, {
      data: { labels: d.labels, datasets: d.datasets },
      type: 'line',
      height: 260
    });
  }

  function refresh(){
    const v = fg.get_values();
    frappe.call({
      method: 'saudization_dashboard.api.get_trend_data',
      args: v,
      callback: (r) => {
        const data = r.message || {};
        drawLine(data.overall);
        drawHead(data.overall);
        drawBranch(data.branch_level);
      }
    });
  }

  page.set_primary_action(__('Refresh'), refresh);
  fg.on('change', refresh);
  refresh();
};
