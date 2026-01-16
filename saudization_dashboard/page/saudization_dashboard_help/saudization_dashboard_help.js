frappe.pages['saudization-dashboard-help'] = {
  on_page_load: function(wrapper) {
    const page = frappe.ui.make_app_page({
      parent: wrapper,
      title: __('دليل لوحة السعودة - AlphaX'),
      single_column: true
    });

    page.set_indicator(__('Help / المساعدة'), 'blue');

    const docx_url = '/assets/saudization_dashboard/docs/AlphaX_Saudization_Dashboard_Guide.docx';
    const pdf_url  = '/assets/saudization_dashboard/docs/AlphaX_Saudization_Dashboard_Guide.pdf';
    const logo_url = '/assets/saudization_dashboard/images/alphax_logo_placeholder.svg';
    const guide_img = '/assets/saudization_dashboard/images/guide_page_1.png';

    const $container = $(
      `<div class="sd-help" dir="rtl">
        <div class="sd-help-card">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
            <div>
              <h2 style="margin:0;">لوحة السعودة - AlphaX</h2>
              <p style="margin:6px 0 0 0;opacity:.9;">هذه الصفحة تشرح الإعدادات الأساسية وطريقة استخدام التقارير ومؤشرات الأداء.</p>
            </div>
            <img src="${logo_url}" alt="AlphaX" style="height:54px;max-width:220px;" />
          </div>

          <hr style="margin:14px 0;opacity:.2;" />

          <h3>تحميل الدليل</h3>
          <ul>
            <li><a href="${docx_url}" target="_blank" rel="noopener">دليل التنصيب والاستخدام (DOCX)</a></li>
            <li><a href="${pdf_url}" target="_blank" rel="noopener">دليل التنصيب والاستخدام (PDF)</a></li>
          </ul>


          <h3>لقطة من الدليل</h3>
          <p class="sd-muted">مثال على تنسيق الدليل داخل النظام.</p>
          <img src="${guide_img}" alt="Guide" style="width:100%;max-width:980px;border-radius:12px;border:1px solid rgba(0,0,0,0.08);" />

          <h3>أهم المؤشرات</h3>
          <ul>
            <li><b>إجمالي الموظفين</b>: الموظفون النشطون فقط (الحالة = Active).</li>
            <li><b>عدد السعوديين</b>: جنسية الموظف = Saudi Arabia (Country).</li>
            <li><b>نسبة السعودة</b>: (السعوديون ÷ الإجمالي) × 100.</li>
            <li><b>النسبة المستهدفة</b>: من Saudization Policy حسب تاريخ السريان.</li>
            <li><b>الفرق</b>: النسبة الفعلية − المستهدفة.</li>
          </ul>

          <h3>خطوات إعداد سريعة</h3>
          <ol>
            <li>افتح <b>Saudization Settings</b> وحدد السعودية + دول مجلس التعاون.</li>
            <li>أنشئ <b>Saudization Policy</b> لكل شركة وحدد Target % والتواريخ.</li>
            <li>شغّل التقارير (ابحث عن <b>Saudization</b>).</li>
          </ol>

          <h3>مشاكل شائعة</h3>
          <ul>
            <li><b>0 موظفين سعوديين</b>: تأكد أن الجنسية مرتبطة بالبلد “Saudi Arabia”.</li>
            <li><b>لا تظهر الصفحة</b>: هذه الصفحة مقيدة بدور HR Manager أو System Manager.</li>
          </ul>

          <hr style="margin:14px 0;opacity:.2;" />

          <div dir="ltr" style="opacity:.9;">
            <h3 style="margin-top:0;">English (Quick)
            </h3>
            <p>This page is restricted to <b>HR Manager</b> or <b>System Manager</b>. Download the DOCX/PDF user guide above for full setup and usage.</p>
          </div>

        </div>
      </div>`
    ).appendTo(page.body);

    $container.find('.sd-help-card').css({
      'background': 'var(--card-bg, #fff)',
      'padding': '16px',
      'border-radius': '16px',
      'box-shadow': '0 1px 3px rgba(0,0,0,0.06)'
    });
  }
};
