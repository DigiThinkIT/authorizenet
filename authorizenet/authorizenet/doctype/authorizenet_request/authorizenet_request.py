# -*- coding: utf-8 -*-
# Copyright (c) 2015, DigiThinkIT, Inc. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from datetime import datetime

LOG_LEVELS = {
	"None": 0,
	"Info": 1,
	"Error": 2,
	"Debug": 3
}

class AuthorizeNetRequest(Document):

	def max_log_level(self, level):
		self._max_log_level = LOG_LEVELS[level]

	def log_action(self, data, level):
		if LOG_LEVELS[level] <= self._max_log_level:
			self.append("log",{
				"doctype": "AuthorizeNet Request Log",
				"log": data,
				"level": level,
				"timestamp": datetime.now().strftime("%Y-%d-%m %H:%M:%S")
			})
