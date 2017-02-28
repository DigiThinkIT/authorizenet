"""
# Integrating Authorize.Net

### 1. Validate Currency Support

Example:

	from frappe.integration_broker.doctype.integration_service.integration_service import get_integration_controller

	controller = get_integration_controller("AuthorizeNet")
	controller().validate_transaction_currency(currency)

### 2. Redirect for payment

Example:

	payment_details = {
		"amount": 600,
		"title": "Payment for bill : 111",
		"description": "payment via cart",
		"reference_doctype": "Payment Request",
		"reference_docname": "PR0001",
		"payer_email": "NuranVerkleij@example.com",
		"payer_name": "Nuran Verkleij",
		"order_id": "111",
		"currency": "USD"
	}

	# redirect the user to this url
	url = controller().get_payment_url(**payment_details)


### 3. On Completion of Payment

Write a method for `on_payment_authorized` in the reference doctype

Example:

	def on_payment_authorized(payment_status):
		# your code to handle callback

##### Note:

payment_status - payment gateway will put payment status on callback.
For paypal payment status parameter is one from: [Completed, Cancelled, Failed]


More Details:
<div class="small">For details on how to get your API credentials, follow this link: <a href="https://support.authorize.net/authkb/index?page=content&id=A405" target="_blank">https://support.authorize.net/authkb/index?page=content&id=A405</a></div>

"""

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import get_url, call_hook_method, cint
from urllib import urlencode
from frappe.integration_broker.doctype.integration_service.integration_service import IntegrationService
import urllib

class AuthorizeNetSettings(IntegrationService):
	service_name = "AuthorizeNet"
	supported_currencies = ["USD"]

	def validate(self):
		if not self.flags.ignore_mandatory:
			self.validate_authorizenet_credentails()

	def on_update(self):
		pass

	def enable(self):
		call_hook_method('payment_gateway_enabled', gateway=self.service_name)
		if not self.flags.ignore_mandatory:
			self.validate_authorizenet_credentails()

	def validate_authorizenet_credentails(self):
		pass

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. {0} does not support transactions in currency '{1}'").format(self.service_name, currency))

	def get_payment_url(self, **kwargs):
		return get_url("./integrations/authorizenet_checkout?{0}".format(urllib.urlencode(kwargs)))

	def create_request(self, data):
		self.data = frappe._dict(data)

		try:
			self.integration_request = super(AuthorizeNetSettings, self)\
				.create_request(self.data, "Host", self.service_name)
			return self.authorize_payment()

		except Exception:
			frappe.log_error(frappe.get_traceback())
			return{
				"redirect_to": frappe.redirect_to_message(_('Server Error'), _("Seems issue with server's razorpay config. Don't worry, in case of failure amount will get refunded to your account.")),
				"status": 401
			}

def get_authnorizenet_credentials():
	api_login = frappe.db.get_value("AuthorizeNet Settings", None, "api_login")
	api_token = frappe.db.get_value("AuthorizeNet Settings", None, "api_token")
	use_sanbox = frappe.db.get_value("AuthorizeNet Settings", None, "use_sanbox")

	return { "login": api_login, "token": api_token, "use_sanbox": use_sanbox }

@frappe.whitelist()
def get_service_details():
	return """
		<div>
			<p>	To obtain the API Login ID and Transaction Key:
				<a href="https://support.authorize.net/authkb/index?page=content&id=A405" target="_blank">
					https://support.authorize.net/authkb/index?page=content&id=A405
				</a>
			</p>
			<p> Steps to configure Service:</p>
			<ol>
				<li>
					Log into the Merchant Interface at https://account.authorize.net.
				</li>
				<br>
				<li>
					Click <strong>Account</strong> from the main toolbar.
				</li>
				<br>
				<li>
					Click <strong>Settings</strong> in the main left-side menu.
				</li>
				<br>
				<li>
					Click <strong>API Credentials & Keys.</strong>
				</li>
				<br>
				<li>
					Enter your <strong>Secret Answer.</strong>
				</li>
				<br>
				<li>
					Select <strong>New Transaction Key.</strong>
				</li>
				<br>
				<li>
					Input API Credentials in <a href="/desk#Form/AuthorizeNet%20Settings">AuthorizeNet Settings</a>
				</li>
				<br>
			</ol>
			<p>
				<strong>Note:</strong> When obtaining a new Transaction Key, you may choose to disable the old Transaction Key by clicking the box titled, <strong>Disable Old Transaction Key Immediately</strong>. You may want to do this if you suspect your previous Transaction Key is being used fraudulently.
				Click Submit to continue. Your new Transaction Key is displayed.
				If the <strong>Disable Old Transaction Key Immediately</strong> box is not checked, the old Transaction Key will automatically expire in 24 hours. When the box is checked, the Transaction Key expires immediately.
			</p>
			<p>
				Be sure to store the Transaction Key in a very safe place. Do not share it with anyone, as it is used to protect your transactions.
			</p>
			<p>
				The system-generated Transaction Key is similar to a password and is used to authenticate requests submitted to the gateway. If a request cannot be authenticated using the Transaction Key, the request is rejected. You may generate a new Transaction Key as often as needed.
			</p>
		</div>
	"""
