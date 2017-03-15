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
from frappe import _, _dict
from frappe.utils import get_url, call_hook_method, cint, flt
from frappe.integration_broker.doctype.integration_service.integration_service import IntegrationService

import json
from urllib import urlencode
from datetime import datetime
import urllib
import authorize

from authorize import Transaction
from authorize import AuthorizeResponseError, AuthorizeInvalidError
from authorizenet.utils import get_authorizenet_user, get_card_accronym, authnet_address, get_contact


class AuthorizeNetSettings(IntegrationService):
    service_name = "AuthorizeNet"
    supported_currencies = ["USD"]
    is_embedable = True

    def validate(self):
        if not self.flags.ignore_mandatory:
            self.validate_authorizenet_credentails()

    def on_update(self):
        pass

    def enable(self):
        call_hook_method("payment_gateway_enabled", gateway=self.service_name)
        if not self.flags.ignore_mandatory:
            self.validate_authorizenet_credentails()

    def get_embed_context(self, context):
        # list countries for billing address form
        context["authorizenet_countries"] = frappe.get_list("Country", fields=["country_name", "code"])
        context["year"] = datetime.today().year

        # get the authorizenet user record
        authnet_user = get_authorizenet_user()

        if authnet_user:
            context["stored_payments"] = authnet_user.get("stored_payments", [])

    def get_embed_form(self):

        context = _dict({
            "source": "templates/includes/integrations/authorizenet/embed.html"
        })

        self.get_embed_context(context)

        return {
            "form": frappe.render_template(context.source, context),
            "style_url": "/assets/css/authorizenet_embed.css",
            "script_url": "/assets/js/authorizenet_embed.js"
        }

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
        url = "./integrations/authorizenet_checkout/{0}"
        return get_url(url.format(request.get("name" )))

    def get_settings(self):
        settings = frappe._dict({
            "api_login_id": self.api_login_id,
            "api_transaction_key": self.get_password(fieldname="api_transaction_key", raise_exception=False)
        })

        return settings

    def process_payment(self):
        # used for feedback about which payment was used
        authorizenet_data = {}
        # the current logged in contact
        contact = get_contact()
        # get authorizenet user if available
        authnet_user = get_authorizenet_user()
        # the cc data available
        data = self.process_data
        # get auth keys
        settings = self.get_settings()
        # fetch redirect info
        redirect_to = data.get("notes", {}).get("redirect_to") or None
        redirect_message = data.get("notes", {}).get("redirect_message") or None

        # uses dummy request doc for unittests
        if not data.get("unittest"):
            if data.get("name"):
                request = frappe.get_doc("AuthorizeNet Request", data.get("name"))
            else:
                # Create request from scratch when embeding form on the fly
                #
                # This allows payment processing without having to pre-create
                # a request first.
                #
                # This path expects all the payment request information to be
                # available!!
                #
                # keys expected: ('amount', 'currency', 'order_id', 'title', \
                #                 'description', 'payer_email', 'payer_name', \
                #                 'reference_docname', 'reference_doctype')
                request = self.build_authorizenet_request(**{ \
                    key: data[key] for key in \
                        ('amount', 'currency', 'order_id', 'title', \
                         'description', 'payer_email', 'payer_name', \
                         'reference_docname', 'reference_doctype') })

                data["name"] = request.get("name")
        else:
            request = frappe.get_doc({"doctype": "AuthorizeNet Request"})

        request.flags.ignore_permissions = 1

        # set the max log level as per settings
        request.max_log_level(self.log_level)

        try:

            if self.card_info:
                # ensure card fields exist
                required_card_fields = ['card_number', 'exp_month', 'exp_year', 'card_code']
                for f in required_card_fields:
                    if not self.card_info.get(f):
                        request.status = "Error"
                        return {
                            request,
                            None,
                            "Missing field: %s" % f,
                            {}
                        }

            # prepare authorize api
            authorize.Configuration.configure(
                authorize.Environment.TEST if self.use_sandbox else authorize.Environment.PRODUCTION,
                settings.api_login_id,
                settings.api_transaction_key
            )

            # cache billing fields as per authorize api requirements
            billing = authnet_address(self.billing_info)

            # build transaction data
            transaction_data = {
                "amount": flt(self.process_data.get("amount")),
                "email": contact.get("email_id"),
                "description": "%s, %s" % (contact.get("last_name"), contact.get("first_name")),
                "customer_type": "individual"
            }

            # track ip for tranasction records
            if frappe.local.request_ip:
                transaction_data.update({
                    "extra_options": {
                        "customer_ip": frappe.local.request_ip
                    }
                })

            # get authorizenet profile informatio for stored payments
            authorizenet_profile = self.process_data.get("authorizenet_profile");

            # use card
            # see: https://vcatalano.github.io/py-authorize/transaction.html
            if self.card_info != None:
                # exp formating for sale/auth api
                expiration_date = "{0}/{1}".format(
                    self.card_info.get("exp_month"),
                    self.card_info.get("exp_year"))

                transaction_data.update({
                    "credit_card": {
                        "card_number": self.card_info.get("card_number"),
                        "expiration_date": expiration_date,
                        "card_code": self.card_info.get("card_code")
                    }
                })
            elif authorizenet_profile:

                # if the customer_id isn't provided, then fetch from authnetuser
                if not authorizenet_profile.get("customer_id"):
                    authorizenet_profile["customer_id"] = authnet_user.get("authorizenet_id")

                # or stored payment
                transaction_data.update({
                    "customer_id": authorizenet_profile.get("customer_id"),
                    "payment_id": authorizenet_profile.get("payment_id")
                })

                # track transaction payment profile ids to return later
                authorizenet_data.update({
                    "customer_id": authorizenet_profile.get("customer_id"),
                    "payment_id": authorizenet_profile.get("payment_id")
                })
            else:
                raise "Missing Credit Card Information"

            # add billing information if available
            if len(billing.keys()):
                transaction_data["billing"] = billing

            # include line items if available
            if self.process_data.get("line_items"):
                transaction_data["line_items"] = self.process_data.get("line_items")

            request.log_action("Requesting Transaction: %s" % \
                json.dumps(transaction_data), "Debug")

            # performt transaction finally
            result = authorize.Transaction.sale(transaction_data)
            request.log_action(json.dumps(result), "Debug")

            # if all went well, record transaction id
            request.transaction_id = result.transaction_response.trans_id
            request.status = "Captured"
            request.flags.ignore_permissions = 1

        except AuthorizeInvalidError as iex:
            # log validation errors
            request.log_action(frappe.get_traceback(), "Error")
            request.status = "Error"
            pass

        except AuthorizeResponseError as ex:
            # log authorizenet server response errors
            result = ex.full_response
            request.log_action(json.dumps(result), "Debug")
            request.log_action(str(ex), "Error")
            request.status = "Error"

            redirect_message = str(ex)
            if result and hasattr(result, 'transaction_response'):
                # if there is extra transaction data, log it
                errors = result.transaction_response.errors
                request.log_action("\n".join([err.error_text for err in errors]), "Error")
                request.log_action(frappe.get_traceback(), "Error")

                request.transaction_id = result.transaction_response.trans_id
                redirect_message = "Success"

            pass

        except Exception as ex:
            # any other errors
            request.log_action(frappe.get_traceback(), "Error")
            request.status = "Error"
            pass


        # now check if we should store payment information on success
        if request.status in ("Captured", "Authorized") and \
            self.card_info and \
            self.card_info.get("store_payment"):

            try:

                # create customer if authnet_user doesn't exist
                if not authnet_user:
                    request.log_action("Creating AUTHNET customer", "Info")

                    customer_result = authorize.Customer.from_transaction(request.transaction_id)

                    request.log_action("Success", "Debug")

                    authnet_user = frappe.get_doc({
                        "doctype": "AuthorizeNet Users",
                        "authorizenet_id": customer_result.customer_id,
                        "contact": contact.name
                    })

                card_store_info = {
                    "card_number": self.card_info.get("card_number"),
                    "expiration_month": self.card_info.get("exp_month"),
                    "expiration_year": self.card_info.get("exp_year"),
                    "card_code": self.card_info.get("card_code"),
                    "billing": self.billing_info
                }

                request.log_action("Storing Payment Information With AUTHNET", "Info")
                request.log_action(json.dumps(card_store_info), "Debug")

                try:
                    card_result = authorize.CreditCard.create(
                        authnet_user.get("authorizenet_id"), card_store_info)
                except AuthorizeResponseError as ex:
                    card_result = ex.full_response
                    request.log_action(json.dumps(card_result), "Debug")
                    request.log_action(str(ex), "Error")

                    try:
                        # duplicate payment profile
                        if card_result["messages"][0]["message"]["code"] == "E00039":
                            request.log_action("Duplicate payment profile, ignore", "Error")
                        else:
                            raise ex
                    except:
                        raise ex


                request.log_action("Success: %s" % card_result.payment_id, "Debug")

                address_short = "{0}, {1} {2}".format(
                    billing.get("city"),
                    billing.get("state"),
                    billing.get("zip"))

                card_label = "{0}{1}".format(
                    get_card_accronym(self.card_info.get("card_number")), self.card_info.get("card_number")[-4:])

                authnet_user.flags.ignore_permissions = 1
                authnet_user.append("stored_payments", {
                    "doctype": "AuthorizeNet Stored Payment",
                    "short_text": "%s %s" % (card_label,
                    address_short),
                    "long_text": "{0}\n{1}\n{2}, {3} {4}\n{5}".format(
                        card_label,
                        billing.get("address", ""),
                        billing.get("city", ""),
                        billing.get("state", ""),
                        billing.get("zip", ""),
                        frappe.get_value("Country",  filters={"code": self.billing_info.get("country")}, fieldname="country_name")
                    ),
                    "address_1": self.billing_info.get("address_1"),
                    "address_2": self.billing_info.get("address_2"),
                    "expires": "{0}-{1}-01".format(
                        self.card_info.get("exp_year"),
                        self.card_info.get("exp_month")),
                    "city": self.billing_info.get("city"),
                    "state": self.billing_info.get("state"),
                    "postal_code": self.billing_info.get("postal_code"),
                    "country": frappe.get_value("Country",  filters={"code": self.billing_info.get("country")}, fieldname="name"),
                    "postal_code": self.billing_info.get("postal_code"),
                    "payment_type": "Card",
                    "authorizenet_payment_id": card_result.payment_id
                })

                authorizenet_data.update({
                    "customer_id": authnet_user.get("authorizenet_id"),
                    "payment_id": card_result.payment_id
                })


                if not data.get("unittest"):
                    authnet_user.save()

                request.log_action("Stored in DB", "Debug")
            except Exception as exx:
                # any other errors
                request.log_action(frappe.get_traceback(), "Error")
                raise exx

        return request, redirect_to, redirect_message, authorizenet_data

    def create_request(self, data):
        self.process_data = frappe._dict(data)

        # try:
        # remove sensitive info from being entered into db
        self.card_info = self.process_data.get("card_info")
        self.billing_info = self.process_data.get("billing_info")
        redirect_url = ""
        request, redirect_to, redirect_message, authorizenet_data = self.process_payment()

        if self.process_data.get('creation'):
            del self.process_data['creation']
        if self.process_data.get('modified'):
            del self.process_data['modified']
        if self.process_data.get('log'):
            del self.process_data['log']

        # sanitize card info
        if self.process_data.get("card_info"):
            self.process_data.card_info["card_number"] = "%s%s" % ("X" * \
                 (len(self.process_data.card_info["card_number"]) - 4),
                self.process_data["card_info"]["card_number"][-4:])

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
            if not self.process_data.get("unittest"):
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
        else:
            for log in request.log:
                print(log.get("level") + "----------------")
                print(log.get("log"))
                print("")

        self.process_data = {}
        self.card_info = {}
        self.billing_info = {}

        return {
            "redirect_to": redirect_url,
            "error": redirect_message if status == "Failed" else None,
            "status": status,
            "authorizenet_data": authorizenet_data
        }


        # except Exception:
        #     frappe.log_error(frappe.get_traceback())
        #     return{
        #         "redirect_to": frappe.redirect_to_message(_("Server Error"), _("There was an internal error processing your payment. Please try again later.")),
        #         "status": 401
        #     }

@frappe.whitelist(allow_guest=True)
def process(options, request_name=None):
    data = {}

    # handles string json as well as dict argument
    if isinstance(options, basestring):
        options = json.loads(options)

    # fixes bug where js null value is casted as a string
    if request_name == 'null':
        request_name = None

    if not options.get("unittest"):
        if request_name:
            request = frappe.get_doc("AuthorizeNet Request", request_name).as_dict()
        else:
            request = {}
    else:
        request = {}

    data.update(options)
    data.update(request)

    data = frappe.get_doc("AuthorizeNet Settings").create_request(data)

    frappe.db.commit()
    return data

@frappe.whitelist()
def get_service_details():
    return """
        <div>
            <p>    To obtain the API Login ID and Transaction Key:
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
