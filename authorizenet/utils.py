from __future__ import unicode_literals
from frappe import _, session

def get_authorizenet_user():
    contact = frappe.get_doc("Contact", filter={"user": session.user})

    authnet_user = frappe.get_doc(
        "AuthorizeNet Users", filter={"contact": contact.name})

    return authnet_user
