import frappe


def _ensure_workspace():
    """Create/update a Workspace with shortcuts (Frappe v15+). Safe no-op if Workspace doctype not found."""
    if not frappe.db.exists("DocType", "Workspace"):
        return

    name = "AlphaX Saudization"

    # Create or load
    if frappe.db.exists("Workspace", name):
        ws = frappe.get_doc("Workspace", name)
    else:
        ws = frappe.get_doc({
            "doctype": "Workspace",
            "name": name,
            "title": name,
            "module": "Saudization Dashboard",
            "icon": "octicon octicon-graph",
            "is_standard": 1,
            "public": 0,
            "sequence_id": 25,
        })

    # Roles (restrict visibility)
    try:
        ws.set("roles", [])
        for role in ("System Manager", "HR Manager"):
            ws.append("roles", {"role": role})
    except Exception:
        # Some versions handle roles differently; keep workspace public=0 as a fallback.
        pass

    # Shortcuts
    try:
        ws.set("shortcuts", [])
        ws.append("shortcuts", {"type": "Page", "link_to": "saudization-hr-analytics", "label": "Saudization HR Analytics"})
        ws.append("shortcuts", {"type": "Page", "link_to": "saudization-dashboard-help", "label": "Help / Guide"})
        ws.append("shortcuts", {"type": "DocType", "link_to": "Saudization Settings", "label": "Saudization Settings"})
        ws.append("shortcuts", {"type": "DocType", "link_to": "Saudization Policy", "label": "Saudization Policy"})
        ws.append("shortcuts", {"type": "Report", "link_to": "Saudization KPI Summary", "label": "KPI Summary"})
    except Exception:
        pass

    ws.save(ignore_permissions=True)


def after_install():
    """Post-install setup for Saudization Dashboard."""
    try:
        from saudization_dashboard.patches.backfill_employee_saudization import execute
        execute()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Saudization Dashboard after_install failed")

    try:
        _ensure_workspace()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Saudization Dashboard workspace setup failed")
