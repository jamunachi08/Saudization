frappe.pages['employee-drilldown'].on_page_load = function(wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Employee Drilldown'),
    single_column: true
  });

  $(wrapper).find('.layout-main-section').addClass('saud-emp-wrap');

  const $card = $('<div class="saud-emp-card"></div>').appendTo(page.body);
  $card.append(`<h4>${__('Employees')}</h4>`);
  const $actions = $('<div class="saud-emp-actions"></div>').appendTo($card);
  const $tableWrap = $('<div id="saud-emp-table"></div>').appendTo($card);
  const $pagination = $('<div class="saud-emp-pagination" id="saud-emp-pagination"></div>').appendTo($card);

  const fg = new frappe.ui.FieldGroup({
    fields: [
      {fieldname:'company', label:__('Company'), fieldtype:'Link', options:'Company', reqd:1},
      {fieldname:'as_on_date', label:__('As On Date'), fieldtype:'Date', default: frappe.datetime.get_today()},
      {fieldname:'branch', label:__('Branch'), fieldtype:'Link', options:'Branch'},
      {fieldname:'department', label:__('Department'), fieldtype:'Link', options:'Department'},
      {fieldname:'designation', label:__('Designation'), fieldtype:'Link', options:'Designation'},
      {fieldname:'nationality_group', label:__('Nationality Group'), fieldtype:'Link', options:'Nationality Group'},
      {fieldname:'is_saudi', label:__('Employee Type'), fieldtype:'Select', options: ['All','Saudi Only','Non-Saudi Only'], default:'All'},
      {fieldname:'search', label:__('Search'), fieldtype:'Data', description: __('Name / ID / Employee Number')}
    ],
    body: page.body
  });
  fg.make();

  if (frappe.route_options) {
    fg.set_values(frappe.route_options);
    frappe.route_options = null;
  }

  let state = {limit: 50, offset: 0, total: 0};

  function pill(is_saudi){
    const status = is_saudi ? __('Saudi') : __('Non-Saudi');
    const color = is_saudi ? '#22c55e' : '#ef4444';
    return `<span class="saud-emp-pill" style="background:${color}20;color:${color}">${frappe.utils.escape_html(status)}</span>`;
  }

  function getArgs(){
    const v = fg.get_values();
    let is_saudi = null;
    if (v.is_saudi === 'Saudi Only') is_saudi = 1;
    if (v.is_saudi === 'Non-Saudi Only') is_saudi = 0;
    return {
      company: v.company,
      as_on_date: v.as_on_date,
      branch: v.branch,
      department: v.department,
      designation: v.designation,
      nationality_group: v.nationality_group,
      search: v.search,
      is_saudi: is_saudi,
      limit: state.limit,
      offset: state.offset
    };
  }

  function render(rows){
    if (!rows || !rows.length){
      $tableWrap.html(`<div class="text-muted">${__('No employees found for the selected filters.')}</div>`);
      $pagination.empty();
      return;
    }

    const html = [
      '<table class="saud-emp-table">',
      '<thead><tr>',
      `<th>${__('Employee')}</th>`,
      `<th>${__('Employee Name')}</th>`,
      `<th>${__('Branch')}</th>`,
      `<th>${__('Department')}</th>`,
      `<th>${__('Designation')}</th>`,
      `<th>${__('Nationality Group')}</th>`,
      `<th>${__('Type')}</th>`,
      `<th>${__('DOJ')}</th>`,
      '</tr></thead><tbody>'
    ];

    rows.forEach(r => {
      html.push('<tr>');
      html.push(`<td><a class="saud-emp-open" data-emp="${frappe.utils.escape_html(r.employee)}">${frappe.utils.escape_html(r.employee)}</a></td>`);
      html.push(`<td>${frappe.utils.escape_html(r.employee_name || '')}</td>`);
      html.push(`<td>${frappe.utils.escape_html(r.branch || '')}</td>`);
      html.push(`<td>${frappe.utils.escape_html(r.department || '')}</td>`);
      html.push(`<td>${frappe.utils.escape_html(r.designation || '')}</td>`);
      html.push(`<td>${frappe.utils.escape_html(r.nationality_group || '')}</td>`);
      html.push(`<td>${pill(r.is_saudi)}</td>`);
      html.push(`<td>${frappe.utils.escape_html(r.date_of_joining || '')}</td>`);
      html.push('</tr>');
    });

    html.push('</tbody></table>');
    $tableWrap.html(html.join(''));

    $tableWrap.find('a.saud-emp-open').on('click', function(e){
      e.preventDefault();
      const emp = $(this).data('emp');
      frappe.set_route('Form', 'Employee', emp);
    });
  }

  function renderPagination(){
    const from = state.total ? (state.offset + 1) : 0;
    const to = Math.min(state.offset + state.limit, state.total);
    const prevDisabled = state.offset <= 0;
    const nextDisabled = (state.offset + state.limit) >= state.total;

    const $p = $pagination;
    $p.empty();
    $p.append(`<span class="text-muted">${__('Showing {0} - {1} of {2}', [from, to, state.total])}</span>`);

    const $prev = $(`<button class="btn btn-default btn-xs" ${prevDisabled ? 'disabled' : ''}>${__('Prev')}</button>`);
    const $next = $(`<button class="btn btn-default btn-xs" ${nextDisabled ? 'disabled' : ''}>${__('Next')}</button>`);

    $prev.on('click', () => { if (!prevDisabled){ state.offset = Math.max(0, state.offset - state.limit); refresh(); } });
    $next.on('click', () => { if (!nextDisabled){ state.offset = state.offset + state.limit; refresh(); } });

    $p.append($prev);
    $p.append($next);
  }

  function refresh(){
    const v = fg.get_values();
    if (!v.company){
      $tableWrap.html(`<div class="text-muted">${__('Select a Company to load employees.')}</div>`);
      return;
    }

    frappe.call({
      method: 'saudization_dashboard.api.get_employee_list',
      args: getArgs(),
      callback: (r) => {
        const data = r.message || {};
        state.total = data.total || 0;
        render(data.rows || []);
        renderPagination();
      }
    });
  }

  function exportCsv(){
    const v = fg.get_values();
    if (!v.company){
      frappe.msgprint(__('Select a Company first.'));
      return;
    }
    const args = getArgs();
    delete args.limit;
    delete args.offset;

    frappe.call({
      method: 'saudization_dashboard.api.export_employee_list_csv',
      args: args,
      freeze: true,
      callback: (r) => {
        const file_url = r.message && r.message.file_url;
        if (file_url) {
          window.open(file_url, '_blank');
        } else {
          frappe.msgprint(__('Could not generate file.'));
        }
      }
    });
  }

  const $btnRefresh = $(`<button class="btn btn-primary btn-xs">${__('Refresh')}</button>`).appendTo($actions);
  const $btnExport = $(`<button class="btn btn-default btn-xs">${__('Export CSV')}</button>`).appendTo($actions);

  $btnRefresh.on('click', () => { state.offset = 0; refresh(); });
  $btnExport.on('click', exportCsv);

  fg.on('change', () => { state.offset = 0; refresh(); });

  refresh();
};
