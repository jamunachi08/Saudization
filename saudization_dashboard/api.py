import frappe
from frappe import _

import csv
import io
from frappe.utils.file_manager import save_file


def _get_theme_doc():
    """Return Saudization Dashboard Theme singleton as dict (with safe defaults)."""
    defaults = {
        "enable_custom_theme": 0,
        "page_background": "#5b0d55",
        "panel_background": "#7a1b73",
        "card_background": "#6a1665",
        "border_color": "rgba(255,255,255,0.25)",
        "text_color": "#ffffff",
        "muted_text_color": "rgba(255,255,255,0.70)",
        "kpi_value_color": "#ffffff",
        "chart_palette": "#1E90FF,#22C55E,#F59E0B,#EF4444,#A855F7,#06B6D4,#F97316,#84CC16",
        "chart_height": 260,
        "tab_bg_color": "#6a1665",
        "tab_text_color": "rgba(255,255,255,0.85)",
        "tab_active_bg_color": "#1E90FF",
        "tab_active_text_color": "#ffffff",
    }

    try:
        doc = frappe.get_single("Saudization Dashboard Theme")
        out = defaults.copy()
        for k in out.keys():
            if hasattr(doc, k):
                out[k] = getattr(doc, k)
        return out
    except Exception:
        return defaults


@frappe.whitelist()
def get_theme():
    """Theme configuration for the dashboard page (v14+ compatible)."""
    return _get_theme_doc()


def _get_navigation_doc():
    """Return Saudization Dashboard Navigation singleton as dict (with safe defaults)."""
    defaults = {
        "enable_tabs": 1,
        "default_tab": "",
        "tabs": [
            {"tab_label": "Human Resources", "tab_type": "Filter Dashboard", "department": "", "company": "", "designation": "", "nationality_group": "", "route": "", "report_name": "", "open_in_new_window": 0, "order": 10},
            {"tab_label": "Research & Development", "tab_type": "Filter Dashboard", "department": "", "company": "", "designation": "", "nationality_group": "", "route": "", "report_name": "", "open_in_new_window": 0, "order": 20},
            {"tab_label": "Sales", "tab_type": "Filter Dashboard", "department": "", "company": "", "designation": "", "nationality_group": "", "route": "", "report_name": "", "open_in_new_window": 0, "order": 30},
        ],
    }

    try:
        doc = frappe.get_single("Saudization Dashboard Navigation")
        out = {"enable_tabs": int(getattr(doc, "enable_tabs", 1) or 0), "default_tab": getattr(doc, "default_tab", "") or "", "tabs": []}
        for row in (getattr(doc, "tabs", []) or []):
            out["tabs"].append({
                "tab_label": getattr(row, "tab_label", ""),
                "tab_type": getattr(row, "tab_type", "Filter Dashboard"),
                "route": getattr(row, "route", ""),
                "report_name": getattr(row, "report_name", ""),
                "company": getattr(row, "company", ""),
                "department": getattr(row, "department", ""),
                "designation": getattr(row, "designation", ""),
                "nationality_group": getattr(row, "nationality_group", ""),
                "open_in_new_window": int(getattr(row, "open_in_new_window", 0) or 0),
                "order": int(getattr(row, "order", 0) or 0),
            })
        out["tabs"].sort(key=lambda x: x.get("order", 0))
        return out
    except Exception:
        return defaults


@frappe.whitelist()
def get_navigation():
    """Navigation tabs configuration for the dashboard page (v14+ compatible)."""
    return _get_navigation_doc()


def _filters_to_where(filters):
    clauses = ["e.status='Active'"]
    params = {}

    company = filters.get('company')
    if not company:
        raise frappe.ValidationError(_("Company is required"))
    clauses.append("e.company=%(company)s")
    params['company'] = company

    for key, field in [
        ('department', 'department'),
        ('designation', 'designation'),
        ('nationality_group', 'saudization_nationality_group'),
    ]:
        val = filters.get(key)
        if val:
            clauses.append(f"e.{field}=%({key})s")
            params[key] = val

    return " AND ".join(clauses), params


def _latest_salary_cte():
    return """
    WITH latest_salary AS (
      SELECT ssa.employee, ssa.base
      FROM `tabSalary Structure Assignment` ssa
      INNER JOIN (
        SELECT employee, MAX(from_date) AS max_from_date
        FROM `tabSalary Structure Assignment`
        WHERE docstatus = 1
        GROUP BY employee
      ) x ON x.employee = ssa.employee AND x.max_from_date = ssa.from_date
      WHERE ssa.docstatus = 1
    )
    """


def _get_active_policy(company):
    # Returns dict with name and default_target_percent or None
    row = frappe.db.sql(
        """
        SELECT name, default_target_percent
        FROM `tabSaudization Policy`
        WHERE company=%s
          AND effective_from <= CURDATE()
          AND (effective_to IS NULL OR effective_to >= CURDATE())
        ORDER BY effective_from DESC
        LIMIT 1
        """,
        (company,),
        as_dict=True,
    )
    return row[0] if row else None


def _get_policy_lines(policy_name, dimension_type=None):
    if not policy_name:
        return []
    q = """
        SELECT dimension_type, department, designation, nationality_group, target_percent, IFNULL(min_headcount, 0) AS min_headcount
        FROM `tabSaudization Policy Line`
        WHERE parent=%s
    """
    params = [policy_name]
    if dimension_type:
        q += " AND dimension_type=%s"
        params.append(dimension_type)
    return frappe.db.sql(q, tuple(params), as_dict=True)


@frappe.whitelist()
def get_kpis(company, department=None, designation=None, nationality_group=None):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': nationality_group,
    })

    sql = _latest_salary_cte() + f"""
    SELECT
      COUNT(*) AS total_employees,
      SUM(CASE WHEN e.is_saudi = 1 THEN 1 ELSE 0 END) AS saudi_employees,
      SUM(CASE WHEN e.is_saudi = 0 THEN 1 ELSE 0 END) AS non_saudi_employees,
      ROUND(100 * SUM(CASE WHEN e.is_saudi = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) AS saudization_percent,

      ROUND(AVG(CASE WHEN e.is_saudi = 1 THEN ls.base END), 0) AS avg_salary_saudi,
      ROUND(AVG(CASE WHEN e.is_saudi = 0 THEN ls.base END), 0) AS avg_salary_non_saudi,

      ROUND(AVG(CASE WHEN e.is_saudi = 1 THEN TIMESTAMPDIFF(MONTH, e.date_of_joining, CURDATE()) END)/12, 1) AS avg_tenure_years_saudi,
      ROUND(AVG(CASE WHEN e.is_saudi = 0 THEN TIMESTAMPDIFF(MONTH, e.date_of_joining, CURDATE()) END)/12, 1) AS avg_tenure_years_non_saudi
    FROM `tabEmployee` e
    LEFT JOIN latest_salary ls ON ls.employee = e.name
    WHERE {where}
    """

    row = frappe.db.sql(sql, params, as_dict=True)[0]

    policy = _get_active_policy(company)
    row['target_percent'] = policy.get('default_target_percent') if policy else None
    row['variance_percent'] = (row['saudization_percent'] - row['target_percent']) if row.get('target_percent') is not None else None
    return row


@frappe.whitelist()
def get_nationality_group_breakdown(company, department=None, designation=None):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': None,
    })
    sql = f"""
    SELECT
      e.saudization_nationality_group AS label,
      COUNT(*) AS value
    FROM `tabEmployee` e
    WHERE {where}
    GROUP BY e.saudization_nationality_group
    ORDER BY value DESC
    """
    rows = frappe.db.sql(sql, params, as_dict=True)
    return rows


@frappe.whitelist()
def get_designation_saudization(company, department=None, min_headcount=3):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': None,
        'nationality_group': None,
    })
    params['min_headcount'] = int(min_headcount or 0)
    sql = f"""
    SELECT
      e.designation AS label,
      ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS value,
      COUNT(*) AS headcount
    FROM `tabEmployee` e
    WHERE {where}
    GROUP BY e.designation
    HAVING COUNT(*) >= %(min_headcount)s
    ORDER BY value ASC, headcount DESC
    LIMIT 15
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_department_saudization(company, designation=None):
    where, params = _filters_to_where({
        'company': company,
        'department': None,
        'designation': designation,
        'nationality_group': None,
    })
    sql = f"""
    SELECT
      e.department AS label,
      SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END) AS saudi_count,
      SUM(CASE WHEN e.is_saudi=0 THEN 1 ELSE 0 END) AS non_saudi_count,
      ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS saudization_percent,
      COUNT(*) AS headcount
    FROM `tabEmployee` e
    WHERE {where}
    GROUP BY e.department
    ORDER BY saudization_percent ASC, headcount DESC
    LIMIT 20
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_salary_band_saudization(company, department=None, designation=None):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': None,
    })
    sql = _latest_salary_cte() + f"""
    WITH emp AS (
      SELECT e.name, e.is_saudi, IFNULL(ls.base,0) AS base
      FROM `tabEmployee` e
      LEFT JOIN latest_salary ls ON ls.employee = e.name
      WHERE {where}
    )
    SELECT
      CASE
        WHEN base <= 5000 THEN 'Up to 5k'
        WHEN base <= 10000 THEN '5k-10k'
        WHEN base <= 15000 THEN '10k-15k'
        ELSE '15k+'
      END AS label,
      ROUND(100 * SUM(CASE WHEN is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS value,
      COUNT(*) AS headcount
    FROM emp
    GROUP BY label
    ORDER BY FIELD(label,'Up to 5k','5k-10k','10k-15k','15k+')
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_trend(company, department=None, designation=None, months_back=24):
    where, params = _filters_to_where({
        'company': company,
        'department': department,
        'designation': designation,
        'nationality_group': None,
    })
    params['months_back'] = int(months_back or 24)
    sql = f"""
    SELECT
      DATE_FORMAT(e.date_of_joining, '%Y-%m-01') AS label,
      ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS value,
      COUNT(*) AS hires_count
    FROM `tabEmployee` e
    WHERE {where}
      AND e.date_of_joining IS NOT NULL
      AND e.date_of_joining >= DATE_SUB(CURDATE(), INTERVAL %(months_back)s MONTH)
    GROUP BY label
    ORDER BY label
    """
    return frappe.db.sql(sql, params, as_dict=True)


@frappe.whitelist()
def get_department_compliance(company, min_headcount=3):
    # Actual vs targets by department (policy line overrides default target)
    min_headcount = int(min_headcount or 0)

    policy = _get_active_policy(company)
    default_target = policy.get('default_target_percent') if policy else None
    policy_name = policy.get('name') if policy else None
    line_targets = _get_policy_lines(policy_name, dimension_type='Department')
    target_by_dept = {l.get('department'): l.get('target_percent') for l in line_targets if l.get('department')}
    min_by_dept = {l.get('department'): int(l.get('min_headcount') or 0) for l in line_targets if l.get('department')}

    rows = frappe.db.sql(
        """
        SELECT
          e.department AS department,
          COUNT(*) AS headcount,
          ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS actual_percent
        FROM `tabEmployee` e
        WHERE e.status='Active' AND e.company=%s
        GROUP BY e.department
        ORDER BY actual_percent ASC, headcount DESC
        """,
        (company,),
        as_dict=True,
    )

    out = []
    for r in rows:
        dept = r.get('department')
        hc = int(r.get('headcount') or 0)
        effective_min = max(min_headcount, min_by_dept.get(dept, 0))
        if hc < effective_min:
            continue
        target = target_by_dept.get(dept, default_target)
        variance = (r['actual_percent'] - target) if target is not None else None
        status = None
        if target is not None:
            if r['actual_percent'] >= target:
                status = 'Compliant'
            elif r['actual_percent'] >= target - 10:
                status = 'Near'
            else:
                status = 'Below'
        out.append({
            'department': dept,
            'headcount': hc,
            'actual_percent': r['actual_percent'],
            'target_percent': target,
            'variance_percent': variance,
            'status': status,
        })

    return out


@frappe.whitelist()
def get_matrix(company, min_headcount=3):
    min_headcount = int(min_headcount or 0)
    rows = frappe.db.sql(
        """
        SELECT
          e.department AS department,
          e.designation AS designation,
          COUNT(*) AS headcount,
          ROUND(100 * SUM(CASE WHEN e.is_saudi=1 THEN 1 ELSE 0 END)/NULLIF(COUNT(*),0), 1) AS saudization_percent
        FROM `tabEmployee` e
        WHERE e.status='Active' AND e.company=%s
        GROUP BY e.department, e.designation
        HAVING COUNT(*) >= %s
        ORDER BY e.department, saudization_percent ASC
        """,
        (company, min_headcount),
        as_dict=True,
    )
    return rows


# --------------------------
# Dashboard-friendly wrappers
# (Keeps JS stable across versions)
# --------------------------


def _rows_to_chart(rows, series_name="Value", value_key="value", label_key="label"):
    labels = [r.get(label_key) for r in rows]
    values = [r.get(value_key) for r in rows]
    return {
        "labels": labels,
        "datasets": [{"name": series_name, "values": values}],
    }


@frappe.whitelist()
def get_actual_vs_target_overall(company, department=None, designation=None, nationality_group=None):
    # Reuse KPI function to compute actual; compare with active policy
    k = get_kpis(company, department=department, designation=designation, nationality_group=nationality_group)
    labels = ["Saudization %"]
    datasets = [
        {"name": "Actual", "values": [k.get("saudization_percent") or 0]},
        {"name": "Target", "values": [k.get("target_percent") or 0]},
    ]
    return {"labels": labels, "datasets": datasets, "variance_percent": k.get("variance_percent")}


@frappe.whitelist()
def get_saudization_by_designation(company, department=None, min_headcount=3):
    rows = get_designation_saudization(company, department=department, min_headcount=min_headcount)
    return _rows_to_chart(rows, series_name="Saudization %")


@frappe.whitelist()
def get_saudization_by_department(company, designation=None):
    rows = get_department_saudization(company, designation=designation)
    # stacked bar: saudi and non-saudi counts
    labels = [r.get("label") for r in rows]
    saudi = [r.get("saudi_count") for r in rows]
    non_saudi = [r.get("non_saudi_count") for r in rows]
    return {
        "labels": labels,
        "datasets": [
            {"name": "Saudi", "values": saudi},
            {"name": "Non-Saudi", "values": non_saudi},
        ],
    }


@frappe.whitelist()
def get_saudization_by_salary_band(company, department=None, designation=None):
    rows = get_salary_band_saudization(company, department=department, designation=designation)
    return _rows_to_chart(rows, series_name="Saudization %")


@frappe.whitelist()
def get_saudization_trend(company, department=None, designation=None, months_back=24):
    rows = get_trend(company, department=department, designation=designation, months_back=months_back)
    return _rows_to_chart(rows, series_name="Saudization %")


@frappe.whitelist()
def get_matrix_with_targets(company, min_headcount=3):
    # Returns rows with target and variance (Department+Designation overrides)
    base_rows = get_matrix(company, min_headcount=min_headcount)
    policy = _get_active_policy(company)
    default_target = policy.get("default_target_percent") if policy else None

    lines = _get_policy_lines(policy.get("name") if policy else None)
    # Build lookup precedence: Dept+Designation > Designation > Department > Overall(default)
    dept_desig = {}
    desig = {}
    dept = {}
    for l in lines:
        dt = l.get("dimension_type")
        if dt == "Department+Designation" and l.get("department") and l.get("designation"):
            dept_desig[(l["department"], l["designation"])] = l.get("target_percent")
        elif dt == "Designation" and l.get("designation"):
            desig[l["designation"]] = l.get("target_percent")
        elif dt == "Department" and l.get("department"):
            dept[l["department"]] = l.get("target_percent")

    out = []
    for r in base_rows:
        d = r.get("department")
        g = r.get("designation")
        t = None
        if d and g and (d, g) in dept_desig:
            t = dept_desig[(d, g)]
        elif g and g in desig:
            t = desig[g]
        elif d and d in dept:
            t = dept[d]
        else:
            t = default_target
        v = (r.get("saudization_percent") - t) if (t is not None and r.get("saudization_percent") is not None) else None
        out.append({
            **r,
            "target_percent": t,
            "variance_percent": v,
        })
    return out

# ------------------------------
# Executive Layer (CEO View)
# ------------------------------

def _getdate(d):
    from frappe.utils import getdate
    return getdate(d) if d else getdate()


def _last_day_of_month(dt):
    import calendar
    from datetime import date
    return date(dt.year, dt.month, calendar.monthrange(dt.year, dt.month)[1])


def _month_add(dt, months):
    import calendar
    from datetime import date
    y = dt.year + (dt.month - 1 + months)//12
    m = (dt.month - 1 + months)%12 + 1
    d = min(dt.day, calendar.monthrange(y, m)[1])
    return date(y, m, d)


def _month_labels(end_dt, months_back):
    # returns list of first-of-month dates (as date objects) from oldest to newest
    from datetime import date
    end_month = date(end_dt.year, end_dt.month, 1)
    start_month = _month_add(end_month, -max(int(months_back or 12)-1, 0))
    cur = start_month
    out = []
    while cur <= end_month:
        out.append(cur)
        cur = _month_add(cur, 1)
    return out


def _employee_snapshot(company=None, branch=None, as_on=None):
    """Return headcount snapshot as of a date, using DOJ + relieving_date where available.

    Note: historical status changes may affect precision; this is the safest Cloud-ready approach
    without requiring a separate snapshot table.
    """
    as_on = _getdate(as_on)
    where = ["(e.date_of_joining IS NULL OR e.date_of_joining <= %(as_on)s)",
             "(e.relieving_date IS NULL OR e.relieving_date > %(as_on)s)"]
    params = {"as_on": as_on}

    if company:
        where.append("e.company = %(company)s")
        params["company"] = company

    if branch:
        where.append("e.branch = %(branch)s")
        params["branch"] = branch

    sql = f"""
        SELECT
            COUNT(*) AS total_employees,
            SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) AS saudi_employees,
            SUM(CASE WHEN IFNULL(e.is_saudi,0)=0 THEN 1 ELSE 0 END) AS non_saudi_employees,
            ROUND(100 * SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) AS saudization_percent
        FROM `tabEmployee` e
        WHERE {' AND '.join(where)}
    """
    return frappe.db.sql(sql, params, as_dict=True)[0]


def _policy_target_percent(company, as_on=None):
    as_on = _getdate(as_on)
    row = frappe.db.sql(
        """
        SELECT default_target_percent
        FROM `tabSaudization Policy`
        WHERE company=%s
          AND effective_from <= %s
          AND (effective_to IS NULL OR effective_to >= %s)
        ORDER BY effective_from DESC
        LIMIT 1
        """,
        (company, as_on, as_on),
        as_dict=True,
    )
    return (row[0].get('default_target_percent') if row else None)


def _status_from_variance(variance_pp):
    if variance_pp is None:
        return "-"
    if variance_pp >= 0:
        return "Green"
    if variance_pp >= -2:
        return "Amber"
    return "Red"


def _companies_under_holding(holding_company):
    # ERPNext Company typically has parent_company.
    if not holding_company:
        return []
    if not frappe.db.table_exists('tabCompany'):
        return []
    rows = frappe.get_all('Company', filters={'parent_company': holding_company}, pluck='name')
    return rows


@frappe.whitelist()
def get_executive_scorecard(holding_company=None, company=None, branch=None, as_on_date=None, months_back=12):
    """CEO scorecard payload (filters allowed)."""
    as_on = _getdate(as_on_date)
    months_back = int(months_back or 12)

    # Determine scope
    scope_companies = []
    if company:
        scope_companies = [company]
    elif holding_company:
        scope_companies = _companies_under_holding(holding_company)
    else:
        # all companies
        scope_companies = frappe.get_all('Company', pluck='name') if frappe.db.table_exists('tabCompany') else []

    # Overall snapshot (weighted across companies if multiple)
    overall_total = overall_saudi = overall_non = 0
    weighted_target = 0.0
    weighted_target_base = 0

    company_rows = []
    for c in scope_companies:
        snap = _employee_snapshot(company=c, branch=branch, as_on=as_on)
        tgt = _policy_target_percent(c, as_on=as_on)
        variance = (snap['saudization_percent'] - tgt) if tgt is not None else None
        status = _status_from_variance(variance)
        snap.update({
            'company': c,
            'target_percent': tgt,
            'variance_percent': variance,
            'status': status,
        })
        company_rows.append(snap)

        overall_total += int(snap.get('total_employees') or 0)
        overall_saudi += int(snap.get('saudi_employees') or 0)
        overall_non += int(snap.get('non_saudi_employees') or 0)

        if tgt is not None and (snap.get('total_employees') or 0) > 0:
            weighted_target += float(tgt) * int(snap['total_employees'])
            weighted_target_base += int(snap['total_employees'])

    overall_percent = round((100 * overall_saudi / overall_total), 1) if overall_total else 0.0
    overall_target = round((weighted_target / weighted_target_base), 1) if weighted_target_base else None
    overall_variance = (overall_percent - overall_target) if overall_target is not None else None

    overall = {
        'total_employees': overall_total,
        'saudi_employees': overall_saudi,
        'non_saudi_employees': overall_non,
        'saudization_percent': overall_percent,
        'target_percent': overall_target,
        'variance_percent': overall_variance,
        'status': _status_from_variance(overall_variance),
        'mom_change': None,
    }

    # MoM change using previous month end
    prev_month_end = _last_day_of_month(_month_add(as_on, -1))
    prev = _employee_snapshot(company=company if company else None, branch=branch, as_on=prev_month_end)
    prev_percent = prev.get('saudization_percent')
    if prev_percent is not None:
        overall['mom_change'] = round(overall_percent - float(prev_percent), 1)

    # Trend series
    labels = []
    actual_values = []
    target_values = []
    for m_start in _month_labels(as_on, months_back):
        m_end = _last_day_of_month(m_start)
        snap = _employee_snapshot(company=company if company else None, branch=branch, as_on=m_end)
        labels.append(m_start.strftime('%Y-%m'))
        actual_values.append(snap.get('saudization_percent') or 0)
        # Use current target policy as of month end (weighted if multiple companies)
        if company:
            t = _policy_target_percent(company, as_on=m_end)
        else:
            # weighted across companies
            t_sum = 0.0
            t_base = 0
            for c in scope_companies:
                s = _employee_snapshot(company=c, branch=branch, as_on=m_end)
                t_c = _policy_target_percent(c, as_on=m_end)
                if t_c is not None and (s.get('total_employees') or 0) > 0:
                    t_sum += float(t_c) * int(s['total_employees'])
                    t_base += int(s['total_employees'])
            t = round((t_sum / t_base), 1) if t_base else None
        target_values.append(t if t is not None else 0)

    trend = {
        'labels': labels,
        'actual_values': actual_values,
        'target_values': target_values,
    }

    # Holding risk chart payload (variance per company)
    company_rows_sorted = sorted(company_rows, key=lambda x: (x.get('variance_percent') if x.get('variance_percent') is not None else 9999))
    risk_labels = [r['company'] for r in company_rows_sorted]
    variance_values = [round(r.get('variance_percent') or 0, 1) for r in company_rows_sorted]
    holding_payload = {
        'labels': risk_labels,
        'variance_values': variance_values,
        'rows': company_rows_sorted,
    }

    return {
        'overall': overall,
        'trend': trend,
        'holding': holding_payload,
    }


@frappe.whitelist()
def get_trend_data(holding_company=None, company=None, branch=None, months_back=24, as_on_date=None):
    """Month-wise trend charts payload (overall + branch-level)."""
    as_on = _getdate(as_on_date)
    months_back = int(months_back or 24)

    # Overall (company scope)
    labels = []
    actual = []
    target = []
    saudi_counts = []
    non_counts = []

    scope_companies = []
    if company:
        scope_companies = [company]
    elif holding_company:
        scope_companies = _companies_under_holding(holding_company)
    else:
        scope_companies = frappe.get_all('Company', pluck='name') if frappe.db.table_exists('tabCompany') else []

    for m_start in _month_labels(as_on, months_back):
        m_end = _last_day_of_month(m_start)
        snap_total = snap_saudi = snap_non = 0
        for c in scope_companies:
            s = _employee_snapshot(company=c, branch=branch, as_on=m_end)
            snap_total += int(s.get('total_employees') or 0)
            snap_saudi += int(s.get('saudi_employees') or 0)
            snap_non += int(s.get('non_saudi_employees') or 0)
        percent = round((100 * snap_saudi / snap_total), 1) if snap_total else 0.0

        # weighted target
        t_sum = 0.0
        t_base = 0
        for c in scope_companies:
            s = _employee_snapshot(company=c, branch=branch, as_on=m_end)
            t_c = _policy_target_percent(c, as_on=m_end)
            if t_c is not None and (s.get('total_employees') or 0) > 0:
                t_sum += float(t_c) * int(s['total_employees'])
                t_base += int(s['total_employees'])
        t = round((t_sum / t_base), 1) if t_base else None

        labels.append(m_start.strftime('%Y-%m'))
        actual.append(percent)
        target.append(t if t is not None else 0)
        saudi_counts.append(snap_saudi)
        non_counts.append(snap_non)

    overall = {
        'labels': labels,
        'actual_values': actual,
        'target_values': target,
        'saudi_counts': saudi_counts,
        'non_saudi_counts': non_counts,
    }

    # Branch-level trend: top 6 branches by headcount in last month within single company scope
    branch_level = {'labels': labels, 'datasets': []}
    if company and frappe.db.table_exists('tabEmployee'):
        # get top branches
        last_month_end = _last_day_of_month(_getdate(as_on))
        top = frappe.db.sql(
            """
            SELECT e.branch, COUNT(*) as headcount
            FROM `tabEmployee` e
            WHERE e.company=%s
              AND e.branch IS NOT NULL AND e.branch != ''
              AND (e.date_of_joining IS NULL OR e.date_of_joining <= %s)
              AND (e.relieving_date IS NULL OR e.relieving_date > %s)
            GROUP BY e.branch
            ORDER BY headcount DESC
            LIMIT 6
            """,
            (company, last_month_end, last_month_end),
            as_dict=True,
        )
        branches = [r['branch'] for r in top if r.get('branch')]
        for b in branches:
            series = []
            for m_start in _month_labels(as_on, months_back):
                m_end = _last_day_of_month(m_start)
                s = _employee_snapshot(company=company, branch=b, as_on=m_end)
                series.append(s.get('saudization_percent') or 0)
            branch_level['datasets'].append({'name': b, 'values': series})

    return {'overall': overall, 'branch_level': branch_level}


@frappe.whitelist()
def get_holding_comparison(holding_company, as_on_date=None):
    """Holding vs subsidiaries comparison (table + chart)."""
    as_on = _getdate(as_on_date)
    companies = _companies_under_holding(holding_company)

    rows = []
    labels = []
    actual_values = []
    target_values = []

    for c in companies:
        snap = _employee_snapshot(company=c, as_on=as_on)
        tgt = _policy_target_percent(c, as_on=as_on)
        variance = (snap['saudization_percent'] - tgt) if tgt is not None else None
        status = _status_from_variance(variance)
        row = {
            'company': c,
            'total_employees': snap.get('total_employees') or 0,
            'saudi_employees': snap.get('saudi_employees') or 0,
            'saudization_percent': snap.get('saudization_percent') or 0,
            'target_percent': tgt,
            'variance_percent': variance,
            'status': status,
        }
        rows.append(row)

        labels.append(c)
        actual_values.append(row['saudization_percent'] or 0)
        target_values.append(tgt if tgt is not None else 0)

    # sort by variance ascending (most risk first)
    rows.sort(key=lambda x: (x.get('variance_percent') if x.get('variance_percent') is not None else 9999))

    return {
        'rows': rows,
        'chart': {
            'labels': labels,
            'actual_values': actual_values,
            'target_values': target_values,
        }
    }


@frappe.whitelist()
def get_company_drilldown(company, as_on_date=None, branch=None):
    """Drill-down payload for a single company.

    Returns:
      - branches: breakdown rows by Branch
      - departments: breakdown rows by Department (optionally within a Branch)

    Notes:
      - Uses the same policy-driven annual target % as the company policy.
      - Snapshot logic uses DOJ + relieving_date relative to as_on_date.
    """
    as_on = _getdate(as_on_date)
    company = (company or '').strip()
    branch = (branch or '').strip() or None
    if not company:
        raise frappe.ValidationError(_("Company is required"))

    tgt = _policy_target_percent(company, as_on=as_on)

    # --- Branch breakdown
    b_rows = frappe.db.sql(
        """
        SELECT
          e.branch AS branch,
          COUNT(*) AS total_employees,
          SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) AS saudi_employees,
          SUM(CASE WHEN IFNULL(e.is_saudi,0)=0 THEN 1 ELSE 0 END) AS non_saudi_employees,
          ROUND(100 * SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) AS saudization_percent
        FROM `tabEmployee` e
        WHERE e.company=%(company)s
          AND (e.date_of_joining IS NULL OR e.date_of_joining <= %(as_on)s)
          AND (e.relieving_date IS NULL OR e.relieving_date > %(as_on)s)
          AND e.branch IS NOT NULL AND e.branch != ''
        GROUP BY e.branch
        ORDER BY total_employees DESC
        """,
        {"company": company, "as_on": as_on},
        as_dict=True,
    )

    branches = []
    for r in (b_rows or []):
        variance = (float(r.get('saudization_percent') or 0) - float(tgt)) if tgt is not None else None
        branches.append({
            **r,
            'target_percent': tgt,
            'variance_percent': round(variance, 1) if variance is not None else None,
            'status': _status_from_variance(variance),
        })

    # Risk-first ordering (lowest variance first), then headcount desc
    branches.sort(key=lambda x: (
        x.get('variance_percent') if x.get('variance_percent') is not None else 9999,
        -(x.get('total_employees') or 0)
    ))

    # --- Department breakdown (optionally filtered by Branch)
    dep_where = [
        "e.company=%(company)s",
        "(e.date_of_joining IS NULL OR e.date_of_joining <= %(as_on)s)",
        "(e.relieving_date IS NULL OR e.relieving_date > %(as_on)s)",
        "e.department IS NOT NULL AND e.department != ''",
    ]
    params = {"company": company, "as_on": as_on}
    if branch:
        dep_where.append("e.branch=%(branch)s")
        params["branch"] = branch

    d_rows = frappe.db.sql(
        f"""
        SELECT
          e.department AS department,
          COUNT(*) AS total_employees,
          SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) AS saudi_employees,
          SUM(CASE WHEN IFNULL(e.is_saudi,0)=0 THEN 1 ELSE 0 END) AS non_saudi_employees,
          ROUND(100 * SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) AS saudization_percent
        FROM `tabEmployee` e
        WHERE {' AND '.join(dep_where)}
        GROUP BY e.department
        ORDER BY total_employees DESC
        LIMIT 30
        """,
        params,
        as_dict=True,
    )

    departments = []
    for r in (d_rows or []):
        variance = (float(r.get('saudization_percent') or 0) - float(tgt)) if tgt is not None else None
        departments.append({
            **r,
            'target_percent': tgt,
            'variance_percent': round(variance, 1) if variance is not None else None,
            'status': _status_from_variance(variance),
        })

    departments.sort(key=lambda x: (
        x.get('variance_percent') if x.get('variance_percent') is not None else 9999,
        -(x.get('total_employees') or 0)
    ))

    return {
        'company': company,
        'as_on_date': as_on.strftime('%Y-%m-%d'),
        'branch': branch,
        'target_percent': tgt,
        'branches': branches,
        'departments': departments,
    }


@frappe.whitelist()
def get_designation_breakdown(company, department, as_on_date=None, branch=None, min_headcount=3):
    """Designation breakdown within a department (optionally within a branch).

    Used for drill-down: Department -> Designation.
    """
    as_on = _getdate(as_on_date)
    company = (company or '').strip()
    department = (department or '').strip()
    branch = (branch or '').strip() or None

    if not company:
        raise frappe.ValidationError(_("Company is required"))
    if not department:
        raise frappe.ValidationError(_("Department is required"))

    tgt = _policy_target_percent(company, as_on=as_on)
    params = {
        "company": company,
        "department": department,
        "as_on": as_on,
        "min_headcount": int(min_headcount or 0),
    }

    where = [
        "e.company=%(company)s",
        "e.department=%(department)s",
        "(e.date_of_joining IS NULL OR e.date_of_joining <= %(as_on)s)",
        "(e.relieving_date IS NULL OR e.relieving_date > %(as_on)s)",
        "e.designation IS NOT NULL AND e.designation != ''",
    ]
    if branch:
        where.append("e.branch=%(branch)s")
        params["branch"] = branch

    rows = frappe.db.sql(
        f"""
        SELECT
          e.designation AS designation,
          COUNT(*) AS total_employees,
          SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) AS saudi_employees,
          SUM(CASE WHEN IFNULL(e.is_saudi,0)=0 THEN 1 ELSE 0 END) AS non_saudi_employees,
          ROUND(100 * SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) AS saudization_percent
        FROM `tabEmployee` e
        WHERE {' AND '.join(where)}
        GROUP BY e.designation
        HAVING COUNT(*) >= %(min_headcount)s
        ORDER BY total_employees DESC
        LIMIT 50
        """,
        params,
        as_dict=True,
    )

    designations = []
    for r in (rows or []):
        variance = (float(r.get('saudization_percent') or 0) - float(tgt)) if tgt is not None else None
        designations.append({
            **r,
            'target_percent': tgt,
            'variance_percent': round(variance, 1) if variance is not None else None,
            'status': _status_from_variance(variance),
        })

    designations.sort(key=lambda x: (
        x.get('variance_percent') if x.get('variance_percent') is not None else 9999,
        -(x.get('total_employees') or 0)
    ))

    return {
        'company': company,
        'department': department,
        'branch': branch,
        'as_on_date': as_on.strftime('%Y-%m-%d'),
        'target_percent': tgt,
        'designations': designations,
    }


@frappe.whitelist()
def get_top_risky_positions(company, as_on_date=None, branch=None, top_n=10, min_headcount=3):
    """Return the most risky designations (lowest variance vs target).

    Intended for CEO/HR quick list: "Top risky positions".
    """
    as_on = _getdate(as_on_date)
    company = (company or '').strip()
    branch = (branch or '').strip() or None

    if not company:
        raise frappe.ValidationError(_("Company is required"))

    tgt = _policy_target_percent(company, as_on=as_on)
    params = {
        "company": company,
        "as_on": as_on,
        "min_headcount": int(min_headcount or 0),
        "limit": int(top_n or 10),
    }
    where = [
        "e.company=%(company)s",
        "(e.date_of_joining IS NULL OR e.date_of_joining <= %(as_on)s)",
        "(e.relieving_date IS NULL OR e.relieving_date > %(as_on)s)",
        "e.designation IS NOT NULL AND e.designation != ''",
    ]
    if branch:
        where.append("e.branch=%(branch)s")
        params["branch"] = branch

    rows = frappe.db.sql(
        f"""
        SELECT
          e.designation AS designation,
          COUNT(*) AS total_employees,
          SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) AS saudi_employees,
          ROUND(100 * SUM(CASE WHEN IFNULL(e.is_saudi,0)=1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0), 1) AS saudization_percent
        FROM `tabEmployee` e
        WHERE {' AND '.join(where)}
        GROUP BY e.designation
        HAVING COUNT(*) >= %(min_headcount)s
        """,
        params,
        as_dict=True,
    )

    items = []
    for r in (rows or []):
        variance = (float(r.get('saudization_percent') or 0) - float(tgt)) if tgt is not None else None
        items.append({
            **r,
            'target_percent': tgt,
            'variance_percent': round(variance, 1) if variance is not None else None,
            'status': _status_from_variance(variance),
        })

    items.sort(key=lambda x: (
        x.get('variance_percent') if x.get('variance_percent') is not None else 9999,
        -(x.get('total_employees') or 0)
    ))

    return {
        'company': company,
        'branch': branch,
        'as_on_date': as_on.strftime('%Y-%m-%d'),
        'target_percent': tgt,
        'items': items[: int(top_n or 10)],
    }


def _employee_as_on_where(params, company, as_on, branch=None, department=None, designation=None, nationality_group=None, is_saudi=None, search=None):
    where = [
        "e.company=%(company)s",
        "(e.date_of_joining IS NULL OR e.date_of_joining <= %(as_on)s)",
        "(e.relieving_date IS NULL OR e.relieving_date > %(as_on)s)",
    ]
    params.update({"company": company, "as_on": as_on})

    if branch:
        where.append("e.branch=%(branch)s")
        params["branch"] = branch
    if department:
        where.append("e.department=%(department)s")
        params["department"] = department
    if designation:
        where.append("e.designation=%(designation)s")
        params["designation"] = designation
    if nationality_group:
        where.append("e.saudization_nationality_group=%(nationality_group)s")
        params["nationality_group"] = nationality_group
    if is_saudi in (0, 1, "0", "1"):
        where.append("IFNULL(e.is_saudi,0)=%(is_saudi)s")
        params["is_saudi"] = int(is_saudi)
    if search:
        where.append("(e.name LIKE %(q)s OR e.employee_name LIKE %(q)s OR e.employee_number LIKE %(q)s)")
        params["q"] = f"%{search.strip()}%"

    return " AND ".join(where)


@frappe.whitelist()
def get_employee_list(company, as_on_date=None, branch=None, department=None, designation=None, nationality_group=None, is_saudi=None, search=None, limit=50, offset=0):
    """Paginated employee list used by Employee Drilldown page."""
    as_on = _getdate(as_on_date)
    company = (company or '').strip()
    if not company:
        raise frappe.ValidationError(_("Company is required"))

    params = {}
    where = _employee_as_on_where(
        params,
        company=company,
        as_on=as_on,
        branch=(branch or '').strip() or None,
        department=(department or '').strip() or None,
        designation=(designation or '').strip() or None,
        nationality_group=(nationality_group or '').strip() or None,
        is_saudi=is_saudi,
        search=search,
    )

    limit = int(limit or 50)
    offset = int(offset or 0)
    params.update({"limit": limit, "offset": offset})

    total = frappe.db.sql(f"SELECT COUNT(*) AS c FROM `tabEmployee` e WHERE {where}", params)[0][0]

    rows = frappe.db.sql(
        f"""
        SELECT
          e.name AS employee,
          e.employee_name AS employee_name,
          e.employee_number AS employee_number,
          e.branch AS branch,
          e.department AS department,
          e.designation AS designation,
          IFNULL(e.is_saudi,0) AS is_saudi,
          e.nationality AS nationality,
          e.saudization_nationality_group AS nationality_group,
          DATE_FORMAT(e.date_of_joining, '%Y-%m-%d') AS date_of_joining
        FROM `tabEmployee` e
        WHERE {where}
        ORDER BY e.employee_name ASC, e.name ASC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
        as_dict=True,
    )

    return {"total": int(total or 0), "rows": rows}


@frappe.whitelist()
def export_employee_list_csv(company, as_on_date=None, branch=None, department=None, designation=None, nationality_group=None, is_saudi=None, search=None):
    """Export employee list as CSV and return file_url."""
    as_on = _getdate(as_on_date)
    company = (company or '').strip()
    if not company:
        raise frappe.ValidationError(_("Company is required"))

    params = {}
    where = _employee_as_on_where(
        params,
        company=company,
        as_on=as_on,
        branch=(branch or '').strip() or None,
        department=(department or '').strip() or None,
        designation=(designation or '').strip() or None,
        nationality_group=(nationality_group or '').strip() or None,
        is_saudi=is_saudi,
        search=search,
    )

    rows = frappe.db.sql(
        f"""
        SELECT
          e.name AS employee,
          e.employee_number AS employee_number,
          e.employee_name AS employee_name,
          e.branch AS branch,
          e.department AS department,
          e.designation AS designation,
          IFNULL(e.is_saudi,0) AS is_saudi,
          e.nationality AS nationality,
          e.saudization_nationality_group AS nationality_group,
          DATE_FORMAT(e.date_of_joining, '%Y-%m-%d') AS date_of_joining
        FROM `tabEmployee` e
        WHERE {where}
        ORDER BY e.employee_name ASC, e.name ASC
        """,
        params,
        as_dict=True,
    )

    output = io.StringIO()
    # Excel-friendly UTF-8 with BOM
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([
        'Employee', 'Employee Number', 'Employee Name', 'Branch', 'Department', 'Designation',
        'Type', 'Nationality', 'Nationality Group', 'Date of Joining'
    ])
    for r in (rows or []):
        writer.writerow([
            r.get('employee') or '',
            r.get('employee_number') or '',
            r.get('employee_name') or '',
            r.get('branch') or '',
            r.get('department') or '',
            r.get('designation') or '',
            'Saudi' if int(r.get('is_saudi') or 0) == 1 else 'Non-Saudi',
            r.get('nationality') or '',
            r.get('nationality_group') or '',
            r.get('date_of_joining') or '',
        ])

    content = output.getvalue().encode('utf-8')
    fname = f"AlphaX_Employees_{company}_{as_on.strftime('%Y%m%d')}.csv"
    f = save_file(fname, content, dt=None, dn=None, is_private=0)
    return {"file_url": f.file_url}
