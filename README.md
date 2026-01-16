# لوحة السعودة - AlphaX (Frappe / ERPNext v15+)

تقدم هذه الإضافة لوحة تحليلات للامتثال لنظام السعودة، مع مؤشرات KPI وتقارير وإعدادات للأهداف.

## صفحة دليل المستخدم (داخل النظام)
- المسار: **... > Saudization Dashboard > Help**
- متاحة فقط للأدوار: **System Manager**, **HR Manager**
- تنزيل: PDF/DOCX من داخل الصفحة

---

# AlphaX Saudization Dashboard (Frappe / ERPNext v15+)

This app provides a **Saudization compliance analytics dashboard** with KPIs, reports, and configurable targets.

## Features

### Employee derived fields (automatic)
The app adds 2 read-only fields on **Employee**:
- **Is Saudi** (`is_saudi`)
- **Saudization Nationality Group** (`saudization_nationality_group`) = Saudi / GCC / Non-GCC / Unknown

A shipped **Server Script** (Before Save) keeps these fields updated based on `Employee.nationality`.

### Configurable nationalities
- **Saudization Settings** (Singleton)
  - Saudi nationality (Link: Country)
  - GCC nationalities table (Link: Country)

### Targets & policy rules
- **Saudization Policy**
  - Company
  - Effective From / To
  - Default Target % (overall)
  - Policy Lines (child table overrides)

- **Saudization Policy Line** (Child Table)
  - Dimension Type: Department / Designation / Department+Designation / Nationality Group
  - Department / Designation / Nationality Group (as applicable)
  - Target %
  - Minimum Headcount

### Dashboard theme & navigation
- **Saudization Dashboard Theme** (Singleton)
- **Saudization Dashboard Navigation** (Singleton) + Tabs (child table)

### Reports
Installs multiple **Query Reports** starting with `Saudization ...`.

## Install (Frappe Cloud / Bench)

```bash
bench get-app https://github.com/<your_org>/<your_repo>
bench --site <site> install-app saudization_dashboard
```

Then build assets (optional):
```bash
bench build
bench restart
```

## First-time setup checklist
1. Open **Saudization Settings** and set Saudi + GCC nationalities.
2. Create a **Saudization Policy** for each company (set Default Target % and optional Policy Lines).
3. Run the reports (search for `Saudization`).

## Notes
- Nationality is assumed to be a Link to **Country** (ERPNext standard).
- Reports & APIs use MySQL/MariaDB functions (`CURDATE()`, `DATE_FORMAT`, etc.).
