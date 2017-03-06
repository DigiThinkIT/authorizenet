# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt
from __future__ import unicode_literals

import unittest
import random

from frappe.utils import evaluate_filters
from authorizenet.templates.pages.integrations.authorizenet_checkout import process


class TestProcessing(unittest.TestCase):

    def test_processing_api(self):

        result = process({
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
            "billint_info": {
                "address_1": "",
                "address_2": "",
                "city": "",
                "state": "",
                "postal_code": "",
                "country": ""
            }
        }, None)

        self.assertTrue(result.get("status") == "Completed")
