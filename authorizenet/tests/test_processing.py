# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
from __future__ import unicode_literals

import unittest
import random

from frappe.utils import evaluate_filters
from authorizenet.authorizenet.doctype.authorizenet_settings.authorizenet_settings import process


class TestProcessing(unittest.TestCase):

	def setUp(self):
		self.transaction_info = {
			"unittest": True,
			"name": None,   # avoids storing doctypes when only testing api calls
			"amount": round(random.uniform(1,9), 2),
			"title": "Payment for bill : 111",
			"description": "payment via cart",
			"payer_email": "NuranVerkleij@example.com",
			"payer_name": "Nuran Verkleij",
			"order_id": "111",
			"currency": "USD",
			"reference_doctype": None,
			"reference_docname": None,
			"card_info": {
				"card_number": "4111111111111111",
				"exp_month": "01",
				"exp_year": "2018",
				"card_code": "123"
			},
			"billing_info": {
				"address_1": "5555 5th Road",
				"address_2": "",
				"city": "Orlando",
				"state": "FL",
				"pincode": "32801",
				"country": "United States"
			}
		}

	def tearDown(self):
		self.transaction_info = None

	def test_processing_api(self):
		result = process(self.transaction_info, None)
		self.assertTrue(result.get("status") == "Completed")

	def test_processing_with_stored_payments_api(self):
		# flag to trigger payment store
		self.transaction_info["card_info"]["store_payment"] = 1
		result = process(self.transaction_info, None)
		print(result)

		self.assertTrue(result.get("status") == "Completed", "Transaction was not completed")

		authorizenet_data = result.get("authorizenet_data")
		self.assertTrue(authorizenet_data is not None, "Missing authorizenet_data")

		# retry transaction but this time with stored payment id
		del self.transaction_info["card_info"];
		self.transaction_info.update({
			# keep authnet happy about no duplicate charges
			"amount": round(random.uniform(1,9), 2),
			"authorizenet_profile": {
				"payment_id": authorizenet_data.get("payment_id"),
				"customer_id": authorizenet_data.get("customer_id")
			}
		})
		result = process(self.transaction_info, None)

		self.assertTrue(result.get("status") == "Completed")

	def test_invalid_card_number(self):
		# truncate cc number to force error
		self.transaction_info["card_info"]["card_number"] = "411111111111111"
		result = process(self.transaction_info, None)
		self.assertTrue(result.get("status") == "Failed", "%s should be Failed" % (result.get("status")))
