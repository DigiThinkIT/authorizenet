from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, cint
from authorizenet.authorizenet.doctype.authorizenet_settings.authorizenet_settings import get_authnorizenet_credentials

import json
from datetime import datetime

no_cache = 1
no_sitemap = 1
expected_keys = ('amount', 'title', 'description', 'reference_doctype',
    'reference_docname', 'payer_name', 'payer_email', 'order_id')

def get_context(context):
    context.no_cache = 1

    # all these keys should exist in form_dict
    if not (set(expected_keys) - set(frappe.form_dict.keys())):
    	for key in expected_keys:
    		context[key] = frappe.form_dict[key]

    	context['amount'] = flt(context['amount'])
        context['year'] = datetime.today().year

    else:
    	frappe.redirect_to_message(_('Some information is missing'), _('Looks like someone sent you to an incomplete URL. Please ask them to look into it.'))
    	frappe.local.flags.redirect_location = frappe.local.response.location
    	raise frappe.Redirect

@frappe.whitelist(allow_guest=True)
def make_payment(options, reference_doctype, reference_docname):
    data = {}

    if isinstance(options, basestring):
    	data = json.loads(options)

    data.update({
    	"reference_docname": reference_docname,
    	"reference_doctype": reference_doctype
    })

    data =  frappe.get_doc("AuthorizeNet Settings").create_request(data)
    frappe.db.commit()
    return data
