from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.utils.formatters import format_value

import json
from datetime import datetime

from authorizenet.utils import get_authorizenet_user

no_cache = 1
no_sitemap = 1
expected_keys = ('amount', 'title', 'description', 'reference_doctype', 'reference_docname',
    'payer_name', 'payer_email', 'order_id')

def get_context(context):
    context.no_cache = 1

    # get request name from query string
    request_name = frappe.form_dict.get("req")
    # or from pathname, this works better for redirection on auth errors
    if not request_name:
        path_parts = context.get("pathname", "").split('/')
        request_name = path_parts[-1]

    # attempt to fetch AuthorizeNet Request record
    try:
        request = frappe.get_doc("AuthorizeNet Request", request_name)
    except Exception as ex:
        request = None

    # Captured/Authorized transaction redirected to home page
    # TODO: Should we redirec to a "Payment already received" Page?
    if not request or (request and request.get('status') in ("Captured", "Authorized")):
        frappe.local.flags.redirect_location = '/'
        raise frappe.Redirect

    # list countries for billing address form
    context["authorizenet_countries"] = frappe.get_list("Country", fields=["country_name", "name"])

    if request_name and request:
        for key in expected_keys:
            context[key] = request.get(key)

        context["reference_doc"] = frappe.get_doc(
            request.get("reference_doctype"), request.get("reference_docname"))

        context["request_name"] = request_name
        context["year"] = datetime.today().year

        # get the authorizenet user record
        authnet_user = get_authorizenet_user()
        print(authnet_user)

        if authnet_user:
            context["stored_payments"] = authnet_user.get("stored_payments", [])


    else:
        frappe.redirect_to_message(_('Some information is missing'), _(
            'Looks like someone sent you to an incomplete URL. Please ask them to look into it.'))
        frappe.local.flags.redirect_location = frappe.local.response.location
        raise frappe.Redirect

    return context
