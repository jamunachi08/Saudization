app_name = "saudization_dashboard"
app_title = "Saudization Dashboard"
app_publisher = "Jamuna"
app_description = "Saudization HR analytics dashboard with theme + configurable tabs + reports."
app_email = "info@example.com"
app_license = "MIT"

# Exported fixtures shipped with this app (Custom Fields + Reports + Server Script)
fixtures = [
    {"dt": "Custom Field", "filters": [["name", "in", ["Employee-is_saudi", "Employee-saudization_nationality_group"]]]},
    {"dt": "Report", "filters": [["name", "like", "Saudization%"]]},
    {"dt": "Server Script", "filters": [["name", "like", "Derive Saudization%"]]},
]

after_install = "saudization_dashboard.install.after_install"
