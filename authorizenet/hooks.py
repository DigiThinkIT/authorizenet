# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "authorizenet"
app_title = "AuthorizeNet"
app_publisher = "DigiThinkIT, Inc."
app_description = "Authorize.Net gateway integration"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "forellana@digithinkit.com"
app_license = "MIT"


integration_services = ["AuthorizeNet"]
app_include_js = "/assets/js/authorizenet_settings.js"
# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/authorizenet/css/authorizenet.css"
# app_include_js = "/assets/authorizenet/js/authorizenet.js"

# include js, css files in header of web template
# web_include_css = "/assets/authorizenet/css/authorizenet.css"
# web_include_js = "/assets/authorizenet/js/authorizenet.js"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "authorizenet.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "authorizenet.install.before_install"
# after_install = "authorizenet.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "authorizenet.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"authorizenet.tasks.all"
# 	],
# 	"daily": [
# 		"authorizenet.tasks.daily"
# 	],
# 	"hourly": [
# 		"authorizenet.tasks.hourly"
# 	],
# 	"weekly": [
# 		"authorizenet.tasks.weekly"
# 	]
# 	"monthly": [
# 		"authorizenet.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "authorizenet.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "authorizenet.event.get_events"
# }
