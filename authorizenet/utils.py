from __future__ import unicode_literals
import frappe
from frappe import _, session

import authorize

def _range(a,b):
	return [x for x in range(a,b)]

CARDS = {
	'AMEX':         [34, 37],
	'CHINAUP':      [62, 88],
	'DinersClub':   _range(300, 305)+[309, 36, 54, 55]+_range(38, 39),
	'DISCOVER':     [6011, 65] + _range(622126, 622925) + _range(644, 649),
	'JCB':          _range(3528, 3589),
	'LASER':        [6304, 6706, 6771, 6709],
	'MAESTRO':      [5018, 5020, 5038, 5612, 5893, 6304, 6759, 6761, 6762, 6763, "0604", 6390],
	'DANKORT':      [5019],
	'MASTERCARD':   _range(50, 55),
	'VISA':         [4],
	'VISAELECTRON': [4026, 417500, 4405, 4508, 4844, 4913, 4917]
}

def get_contact(contact_name = None):
	user = session.user
	contact = None
	if isinstance(user, unicode):
		user = frappe.get_doc("User", user)

	if not contact_name:
		contact_names = frappe.get_all("Contact", fields=["name"], filters={
			"user": user.name
		})

		if not contact_names or len(contact_names) == 0:
			contact_names = frappe.get_all("Contact", fields=["name"], filters={
				"email_id": user.email
			})

		if contact_names and len(contact_names) > 0:
			contact_name = contact_names[0].get("name")

	if contact_name:
		contact = frappe.get_doc("Contact", contact_name)

	return contact

def get_authorizenet_user():

	authnet_user = None
	try:
		contact = get_contact();
		if contact:
			authnet_user_name = frappe.get_list("AuthorizeNet Users", fields=["name"], filters={"contact": contact.name}, as_list=1)
			if len(authorize_user_name) > 0:
				authnet_user_name = authnet_user_name[0][0]

				#authnet_user_name = frappe.get_value("AuthorizeNet Users",
				#    filters={"contact": contact.name},
				#    fieldname="name")
				authnet_user = frappe.get_doc("AuthorizeNet Users", authnet_user_name)
	except:
		authnet_user = None

	return authnet_user

def get_card_accronym(number):
	card_name = ''
	card_match_size = 0
	for name, values in CARDS.items():
		for digits in values:
			digits = str(digits)
			if number.startswith(digits):
				if len(digits) > card_match_size:
					card_match_size = len(digits)
					card_name = name

	return card_name

def authnet_address(fields):
	address = {}

	if fields is None:
		return address

	if fields.get("first_name"):
		address["first_name"] = fields.get("first_name")[:50]
	if fields.get("last_name"):
		address["last_name"] = fields.get("last_name")[:50]
	if fields.get("company"):
		address["company"] = fields.get("company")[:50]
	if fields.get("address_1"):
		address["address"] = "%s %s" % (fields.get("address_1"), fields.get("address_2", ""))
		address["address"] = address["address"][:60]
	if fields.get("city"):
		address["city"] = fields.get("city", "")[:40]
	if fields.get("state"):
		address["state"] = fields.get("state", "")[:40]
	if fields.get("pincode"):
		address["zip"] = fields.get("pincode")[:20]
	if fields.get("country"):
		address["country"] = fields.get("country", "")[:60]
	if fields.get("phone_number"):
		address["phone_number"] = fields.get("phone_number")[:25]

	return address
