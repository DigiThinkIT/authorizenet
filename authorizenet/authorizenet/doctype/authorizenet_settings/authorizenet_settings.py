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
For authorize.net status parameter is one from: [Completed, Failed]


More Details:
<div class="small">For details on how to get your API credentials, follow this link: <a href="https://support.authorize.net/authkb/index?page=content&id=A405" target="_blank">https://support.authorize.net/authkb/index?page=content&id=A405</a></div>

"""

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import get_url, call_hook_method, cint, flt
from urllib import urlencode
from frappe.integration_broker.doctype.integration_service.integration_service import IntegrationService
import urllib
import authorize

from authorize import Transaction
from authorize import AuthorizeResponseError, AuthorizeInvalidError

class AuthorizeNetSettings(IntegrationService):
	service_name = "AuthorizeNet"
	supported_currencies = ["USD"]

	def validate(self):
		if not self.flags.ignore_mandatory:
			self.validate_authorizenet_credentails()

	def on_update(self):
		pass

	def enable(self):
		call_hook_method("payment_gateway_enabled", gateway=self.service_name)
		if not self.flags.ignore_mandatory:
			self.validate_authorizenet_credentails()

	def validate_authorizenet_credentails(self):
		pass

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. {0} does not support transactions in currency \"{1}\"").format(self.service_name, currency))

	def build_authorizenet_request(self, **kwargs):
		"""Creates an AuthorizeNet Request record to keep params off the url"""

		data = {
			"doctype": "AuthorizeNet Request",
			"status": "Issued",
		}
		data.update(kwargs)
		del data["reference_docname"] # have to set it after insert

		request = frappe.get_doc(data)
		request.flags.ignore_permissions = 1
		request.insert()

		# TODO: Why must we save doctype first before setting docname?
		request.reference_docname = kwargs["reference_docname"]
		request.save()

		return request

	def get_payment_url(self, **kwargs):
		request = self.build_authorizenet_request(**kwargs)
		url = "./integrations/authorizenet_checkout?req={0}"
		return get_url(url.format(request.get("name" )))

	def get_settings(self):
		settings = frappe._dict({
			"api_login_id": self.api_login_id,
			"api_transaction_key": self.get_password(fieldname="api_transaction_key", raise_exception=False)
		})

		return settings

	def process_payment(self):
		data = self.process_data
		settings = self.get_settings()
		redirect_to = data.get("notes", {}).get("redirect_to") or None
		redirect_message = data.get("notes", {}).get("redirect_message") or None

		# uses dummy request doc for unittests
		if not data.get("unittest"):
			request = frappe.get_doc("AuthorizeNet Request", data.get("name"))
		else:
			request = frappe.get_doc({"doctype": "AuthorizeNet Request"})

		request.flags.ignore_permissions = 1

		# set the max log level as per settings
		request.max_log_level(self.log_level)

		try:

			# ensure card fields exist
			required_card_fields = ['card_number', 'exp_month', 'exp_year', 'card_code']
			for f in required_card_fields:
				if not self.card_info.get(f):
					request.status = "Error"
					return {
						request,
						None,
						

					}
					raise Exception("Missing field: %s" % f)

			authorize.Configuration.configure(
				authorize.Environment.TEST if self.use_sandbox else authorize.Environment.PRODUCTION,
				settings.api_login_id,
				settings.api_transaction_key
			)

			expiration_date = "{0}/{1}".format(
				self.card_info.get("exp_month"),
				self.card_info.get("exp_year"))

			transaction_data = {
				"amount": flt(self.process_data.get("amount")),
				"credit_card": {
					"card_number": self.card_info.get("card_number"),
					"expiration_date": expiration_date,
					"card_code": self.card_info.get("card_code")
				}
			}

			request.log_action("Requesting Transaction: %s" % \
				json.dumps(transaction_data), "Debug")
			result = authorize.Transaction.sale(transaction_data)
			request.log_action(json.dumps(result), "Debug")

			request.transaction_id = result.transaction_response.trans_id
			request.status = "Captured"
			request.flags.ignore_permissions = 1

		except AuthorizeInvalidError as iex:
			request.log_action(frappe.get_traceback(), "Error")
			request.status = "Error"
			pass

		except AuthorizeResponseError as ex:
			result = ex.full_response
			request.log_action(json.dumps(result), "Debug")
			request.log_action(str(ex), "Error")
			request.status = "Error"

			redirect_message = str(ex)
			if result and hasattr(result, 'transaction_response'):
				errors = result.transaction_response.errors
				request.log_action("\n".join([err.error_text for err in errors]), "Error")
				request.log_action(traceback.format_exc(), "Error")

				request.transaction_id = result.transaction_response.trans_id
				redirect_message = "Success"

			pass

		except Exception as ex:
			request.log_action(frappe.get_traceback(), "Error")
			request.status = "Error"
			pass

		return request, redirect_to, redirect_message

	def create_request(self, data):
		self.process_data = frappe._dict(data)

		# try:
		# remove sensitive info from being entered into db
		self.card_info = self.process_data.get("card_info")
		redirect_url = ""
		request, redirect_to, redirect_message = self.process_payment()

		if self.process_data.get('creation'):
			del self.process_data['creation']
		if self.process_data.get('modified'):
			del self.process_data['modified']
		if self.process_data.get('log'):
			del self.process_data['log']

		# sanitize card info
		self.process_data.card_info["card_number"] = "%s%s" % ("X" * \
		 	(len(self.process_data.card_info["card_number"]) - 4),
			self.process_data["card_info"]["card_number"][-4])

		self.process_data.card_info["card_code"] = "X" * \
		 	len(self.process_data.card_info["card_code"])

		if not self.process_data.get("unittest"):
			self.integration_request = super(AuthorizeNetSettings, self)\
				.create_request(self.process_data, "Host", self.service_name)

		if request.get('status') == "Captured":
			status = "Completed"
		elif request.get('status') == "Authorized":
			status = "Authorized"
		else:
			status = "Failed"

		# prevents unit test from inserting data on db
		if not self.process_data.get("unittest"):
			self.integration_request.status = status
			self.integration_request.save()
			request.save()

		custom_redirect_to = None
		try:
			custom_redirect_to = frappe.get_doc(
				self.process_data.reference_doctype,
				self.process_data.reference_docname).run_method("on_payment_authorized",
				status)
			request.log_action("Custom Redirect To: %s" % custom_redirect_to, "Info")
		except Exception:
			print(frappe.get_traceback())
			request.log_action(frappe.get_traceback(), "Error")

		if custom_redirect_to:
			redirect_to = custom_redirect_to

		if request.status == "Captured" or request.status == "Authorized":
			redirect_url = "/integrations/payment-success"
			redirect_message = "Success"
			success = True
		else:
			redirect_url = "/integrations/payment-failed"
			redirect_message = "Declined"
			success = False

		if redirect_to:
			redirect_url += "?" + urllib.urlencode({"redirect_to": redirect_to})
		if redirect_message:
			redirect_url += "&" + urllib.urlencode({"redirect_message": redirect_message})

		if not self.process_data.get("unittest"):
			request.log_action("Redirect To: %s" % redirect_url, "Info")
			request.save()


		return {
			"redirect_to": redirect_url,
			"error": redirect_message if status == "Failed" else None,
			"status": status
		}
		return result


		# except Exception:
		# 	frappe.log_error(frappe.get_traceback())
		# 	return{
		# 		"redirect_to": frappe.redirect_to_message(_("Server Error"), _("There was an internal error processing your payment. Please try again later.")),
		# 		"status": 401
		# 	}

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
