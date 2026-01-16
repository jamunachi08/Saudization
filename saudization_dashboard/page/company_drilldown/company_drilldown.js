frappe.pages['company-drilldown'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Company Drilldown'),
    single_column: true
  });

  $(wrapper).find('.layout-main-section').addClass('saud-drill-wrap');

  const $root = $('<div class="saud-drill-grid"></div>').appendTo(page.body);
  const $summary = $('<div class="saud-drill-card"><h4>'+__('Snapshot')+'</h4><div class="saud-kpi-row" id="saud-drill-kpis"></div></div>').appendTo($root);
  const $branches = $('<div class="saud-drill-card"><h4>'+__('Branch Breakdown')+'</h4><div id="saud-drill-branches"></div></div>').appendTo($root);
  const $depts = $('<div class="saud-drill-card"><h4>'+__('Department Breakdown')+'</h4><div id="saud-drill-depts"></div></div>').appendTo($root);
  const $designations = $('<div class="saud-drill-card"><h4>'+__('Designation Breakdown')+'</h4><div id="saud-drill-designations"></div></div>').appendTo($root);
  const $risky = $('<div class="saud-drill-card"><h4>'+__('Top Risky Positions')+'</h4><div id="saud-drill-risky"></div></div>').appendTo($root);

  const fg = new frappe.ui.FieldGroup({
    fields: [
      {fieldname:'company', label:__('Company'), fieldtype:'Link', options:'Company', reqd:1},
      {fieldname:'as_on_date', label:__('As On Date'), fieldtype:'Date', default: frappe.datetime.get_today()},
      {fieldname:'branch', label:__('Branch (optional)'), fieldtype:'Link', options:'Branch'}
    ],
    body: page.body
  });
  fg.make();

  // pick up route options from click actions
  if (frappe.route_options) {
    fg.set_values(frappe.route_options);
    frappe.route_options = null;
  }

  function pill(status){
    const s = (status || '').toLowerCase();
    const map = {green:'#22c55e', amber:'#f59e0b', red:'#ef4444'};
    const color = map[s] || '#64748b';
    return `<span class="saud-pill" style="background:${color}20;color:${color}">${frappe.utils.escape_html(status || '-') }</span>`;
  }

  function setKpis(data){
    const $k = $('#saud-drill-kpis');
    $k.empty();
    const percent = (data?.overall?.saudization_percent ?? null);
    const tgt = (data?.target_percent ?? null);
    const variance = (data?.overall?.variance_percent ?? null);
    const cards = [
      {label: __('Company'), value: data.company || '-'},
      {label: __('As On Date'), value: data.as_on_date || '-'},
      {label: __('Saudization %'), value: (percent!=null ? percent+'%' : '-')},
      {label: __('Target % (Annual)'), value: (tgt!=null ? tgt+'%' : '-')},
      {label: __('Variance (pp)'), value: (variance!=null ? variance+' pp' : '-')},
      {label: __('Headcount'), value: (data?.overall?.total_employees ?? '-')}
    ];
    cards.forEach(c => {
      $k.append(`<div class="saud-kpi"><div class="label">${frappe.utils.escape_html(c.label)}</div><div class="value">${frappe.utils.escape_html(String(c.value))}</div></div>`);
    });
  }

  function renderBranches(rows){
    const $t = $('#saud-drill-branches');
    if (!rows || !rows.length){
      $t.html(`<div class="text-muted">${__('No branch data')}</div>`);
      return;
    }
    const html = [
      '<table class="saud-drill-table">',
      '<thead><tr>',
      `<th>${__('Branch')}</th>`,
      `<th>${__('Headcount')}</th>`,
      `<th>${__('Saudi')}</th>`,
      `<th>${__('Actual %')}</th>`,
      `<th>${__('Variance')}</th>`,
      `<th>${__('Status')}</th>`,
      '</tr></thead><tbody>'
    ];
    rows.forEach(r => {
      const b = r.branch || '';
      html.push('<tr>');
      html.push(`<td><a class="saud-link" data-branch="${frappe.utils.escape_html(b)}">${frappe.utils.escape_html(b || '-') }</a></td>`);
      html.push(`<td>${r.total_employees ?? 0}</td>`);
      html.push(`<td>${r.saudi_employees ?? 0}</td>`);
      html.push(`<td>${(r.saudization_percent ?? 0)}%</td>`);
      html.push(`<td>${(r.variance_percent ?? '-')}${r.variance_percent!=null ? ' pp' : ''}</td>`);
      html.push(`<td>${pill(r.status)}</td>`);
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    $t.html(html.join(''));

    // Drill: branch -> reload with branch filter to show department within that branch
    $t.find('a.saud-link').on('click', function(e){
      e.preventDefault();
      const branch = $(this).data('branch');
      fg.set_value('branch', branch);
      refresh();
    });
  }

  function renderDepartments(rows, branch){
    const $t = $('#saud-drill-depts');
    const title = branch ? __('Department Breakdown (Branch: {0})', [branch]) : __('Department Breakdown');
    $depts.find('h4').text(title);

    if (!rows || !rows.length){
      $t.html(`<div class="text-muted">${__('No department data')}</div>`);
      return;
    }
    const html = [
      '<table class="saud-drill-table">',
      '<thead><tr>',
      `<th>${__('Department')}</th>`,
      `<th>${__('Headcount')}</th>`,
      `<th>${__('Saudi')}</th>`,
      `<th>${__('Actual %')}</th>`,
      `<th>${__('Variance')}</th>`,
      `<th>${__('Status')}</th>`,
      '</tr></thead><tbody>'
    ];
    rows.forEach(r => {
      const dep = r.department || '';
      html.push('<tr>');
      html.push(`<td><a class="saud-link-dept" data-dept="${frappe.utils.escape_html(dep)}">${frappe.utils.escape_html(dep || '-') }</a></td>`);
      html.push(`<td>${r.total_employees ?? 0}</td>`);
      html.push(`<td>${r.saudi_employees ?? 0}</td>`);
      html.push(`<td>${(r.saudization_percent ?? 0)}%</td>`);
      html.push(`<td>${(r.variance_percent ?? '-')}${r.variance_percent!=null ? ' pp' : ''}</td>`);
      html.push(`<td>${pill(r.status)}</td>`);
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    $t.html(html.join(''));

    // Drill: department -> designation breakdown
    $t.find('a.saud-link-dept').on('click', function(e){
      e.preventDefault();
      const dept = $(this).data('dept');
      loadDesignations(dept);
    });
  }

  function renderDesignations(data){
    const $t = $('#saud-drill-designations');
    const dept = data?.department;
    const title = dept ? __('Designation Breakdown (Dept: {0})', [dept]) : __('Designation Breakdown');
    $designations.find('h4').text(title);

    const rows = data?.designations || [];
    if (!rows.length){
      $t.html(`<div class="text-muted">${__('Click a Department to see designations')}</div>`);
      return;
    }
    const html = [
      '<table class="saud-drill-table">',
      '<thead><tr>',
      `<th>${__('Designation')}</th>`,
      `<th>${__('Headcount')}</th>`,
      `<th>${__('Saudi')}</th>`,
      `<th>${__('Actual %')}</th>`,
      `<th>${__('Variance')}</th>`,
      `<th>${__('Status')}</th>`,
      '</tr></thead><tbody>'
    ];
    rows.forEach(r => {
      const des = r.designation || '';
      html.push('<tr>');
      html.push(`<td><a class="saud-link-des" data-des="${frappe.utils.escape_html(des)}">${frappe.utils.escape_html(des || '-') }</a></td>`);
      html.push(`<td>${r.total_employees ?? 0}</td>`);
      html.push(`<td>${r.saudi_employees ?? 0}</td>`);
      html.push(`<td>${(r.saudization_percent ?? 0)}%</td>`);
      html.push(`<td>${(r.variance_percent ?? '-')}${r.variance_percent!=null ? ' pp' : ''}</td>`);
      html.push(`<td>${pill(r.status)}</td>`);
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    $t.html(html.join(''));

    // Drill: designation -> employee list
    $t.find('a.saud-link-des').on('click', function(e){
      e.preventDefault();
      const v = fg.get_values();
      const designation = $(this).data('des');
      frappe.route_options = {
        company: v.company,
        as_on_date: v.as_on_date,
        branch: v.branch,
        department: data?.department,
        designation: designation
      };
      frappe.set_route('employee-drilldown');
    });
  }

  function renderRisky(data){
    const $t = $('#saud-drill-risky');
    const rows = data?.items || [];
    if (!rows.length){
      $t.html(`<div class="text-muted">${__('No risky positions found')}</div>`);
      return;
    }
    const html = [
      '<table class="saud-drill-table">',
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
      html.push(`<td><a class="saud-link-risk" data-des="${frappe.utils.escape_html(des)}">${frappe.utils.escape_html(des || '-') }</a></td>`);
      html.push(`<td>${r.total_employees ?? 0}</td>`);
      html.push(`<td>${(r.saudization_percent ?? 0)}%</td>`);
      html.push(`<td>${(r.variance_percent ?? '-')}${r.variance_percent!=null ? ' pp' : ''}</td>`);
      html.push(`<td>${pill(r.status)}</td>`);
      html.push('</tr>');
    });
    html.push('</tbody></table>');
    $t.html(html.join(''));

    // Drill: risky designation -> employee list
    $t.find('a.saud-link-risk').on('click', function(e){
      e.preventDefault();
      const v = fg.get_values();
      const designation = $(this).data('des');
      frappe.route_options = {
        company: v.company,
        as_on_date: v.as_on_date,
        branch: v.branch,
        designation: designation
      };
      frappe.set_route('employee-drilldown');
    });
  }

  function loadDesignations(department){
    const v = fg.get_values();
    if (!v.company || !department) return;
    frappe.call({
      method: 'saudization_dashboard.api.get_designation_breakdown',
      args: {
        company: v.company,
        as_on_date: v.as_on_date,
        branch: v.branch,
        department: department
      },
      callback: (r) => renderDesignations(r.message || {})
    });
  }

  function loadRisky(){
    const v = fg.get_values();
    if (!v.company) return;
    frappe.call({
      method: 'saudization_dashboard.api.get_top_risky_positions',
      args: {
        company: v.company,
        as_on_date: v.as_on_date,
        branch: v.branch,
        top_n: 10,
        min_headcount: 3
      },
      callback: (r) => renderRisky(r.message || {})
    });
  }

  function refresh(){
    const v = fg.get_values();
    if (!v.company) return;
    frappe.call({
      method: 'saudization_dashboard.api.get_company_drilldown',
      args: v,
      callback: (r) => {
        const data = r.message || {};
        setKpis(data);
        renderBranches(data.branches, data.branch);
        renderDepartments(data.departments, data.branch);
        renderDesignations({});
        loadRisky();
      }
    });
  }

  page.set_primary_action(__('Refresh'), refresh);
  fg.on('change', refresh);
  refresh();
};
