frappe.provide("frappe.integration_service")

frappe.integration_service.authorizenet_gateway = Class.extend({
	card_fields: {
		"authorizenet_name": "name_on_card",
		"authorizenet_number": "card_number",
		"authorizenet_code": "card_code",
		"authorizenet_exp_month": "exp_month",
		"authorizenet_exp_year": "exp_year",
		"authorizenet_store_payment": "store_payment"
	},

	init: function(addressForm, embedForm, selector) {
		this.addressForm = addressForm;
		this.selector = selector;
	},

	collect_billing_info: function() {
		var billing_info = {};
		// collect billing field values

		var result = this.addressForm.validate();
		billing_info = $.extend({}, result.address);

		if ( $('#authorizenet_zipcode').length > 0 ) {
			billing_info["pincode"] = $('#authorizenet_zipcode').val();
		}

		return billing_info;
	},

	collect_card_info: function() {
		var card_info = {};

		// check if store payment was selected
		var stored_payment_option = $('input[name="authorizednet-stored-payment"]:checked').val();
		if ( stored_payment_option !== undefined && stored_payment_option != "none" ) {
			return null;
		}

		// collect card field values
		for(var field in this.card_fields) {
			var $field = $('#'+field);
			if ( $field.attr('type') == 'checkbox' ) {
				card_info[this.card_fields[field]] = $field.is('checked');
			} else {
				card_info[this.card_fields[field]] = $field.val();
			}

			// clean up string
			if ( card_info[this.card_fields[field]] !== undefined && typeof card_info[this.card_fields[field]] == "string" ) {
				// no empty data allowed
				card_info[this.card_fields[field]] = card_info[this.card_fields[field]].trim();
			}
		}

		return card_info;
	},

	collect_stored_payment_info: function() {
		var $input = $('input[name="authorizednet-stored-payment"]:checked');
		var stored_payment_option = $input.val();
		if ( stored_payment_option == "none" ) {
			return null;
		}

		return {
			"payment_id": stored_payment_option,
			"address_name": $input.attr("data-address")
		}
	},

	form: function() {
		var base = this;

		// Handle removal of stored payments
		$('.btn-stored-payment-remove').click(function() {
			var stored_payment = $(this).attr('data-id');
			var $input = $(this).closest('.field').find('input[name="authorizednet-stored-payment"]');
			// sanity check, only allow removing on active selection
			if ( !$input.is(':checked') ) {
				return;
			}

			if ( confirm("Permanently remove stored payment?") ) {
				$('input[name="authorizednet-stored-payment"][value="none"]').prop('checked', true);
				$('input[name="authorizednet-stored-payment"][value="none"]').trigger('change');
				$(this).closest('.field').remove();
				return frappe.call({
					method: 'frappe.client.delete',
					args: {
						doctype: "AuthorizeNet Stored Payment",
						name: stored_payment
					},
					callback: function() {
					}
				});
			}
		});

		// handle displaying manual payment information forms
		$('input[name="authorizednet-stored-payment"]').change(function() {
			if ( $(this).val() != 'none' ) {
				$('#authorizenet-manual-info').slideUp('slow');
			} else {
				$('#authorizenet-manual-info').slideDown('slow');
				$('#authorizenet-manual-info input:first').focus();
			}
		});

		// initially copy all field values on checkbox change
		$('#authorizenet_address_same_as').change(function() {
			var addr_src = $(this).attr('data-source');
			if ( $(this).is(':checked') ) {
				$(addr_src).find('[data-type]').each(function() {
					var name = $(this).attr('data-type');
					var value = $(this).val();
					$('.authorizenet-form .field [data-type="'+name+'"]').val(value);
					$('.authorizenet-form .field [data-type="'+name+'"]').prop('disabled', true);
					$('.authorizenet-form .field [data-type="'+name+'"]').closest('.field').addClass('disabled');
				});
			} else {
				$('.authorizenet-form .field [data-type]').each(function() {
					$(this).prop('disabled', false);
					$(this).closest('.field').removeClass('disabled');
				});
			}
		})

		// then track all changes on source fields
		if ( $('#authorizenet_address_same_as').length > 0 ) {
			var addr_src = $('#authorizenet_address_same_as').attr('data-source');
			$(addr_src).on('field-change', function(e, field) {
				if ( $('#authorizenet_address_same_as').is(':checked') ) {
					$('.authorizenet-form .field [data-type="'+field.name+'"]').val(field.value);
					$('.authorizenet-form .field [data-type="'+field.name+'"]').prop('disabled', true);
					$('.authorizenet-form .field [data-type="'+field.name+'"]').closest('.field').addClass('disabled');
				}
			});
		}

		$('.authorizenet-form .field').each(function() {
			$(this).find('input, select').change(function() {
				if ( base.selector ) {
					base.selector.validate();
				}
			})
		});

		// handle smart placeholder labels
		$('.authorizenet-form .field').each(function() {
			var $field = $(this);
			var $input = $(this).find('input:first, select:first');

			$input
				.change(function() {
					if ( $(this).val() ) {
						$field.addClass('hasvalue');
					} else {
						$field.removeClass('hasvalue');
					}
				})
				.keyup(function() {
					if ( $(this).val() ) {
						$field.addClass('hasvalue');
					} else {
						$field.removeClass('hasvalue');
					}
				})
				.blur(function() {
					$field.removeClass('focus');
				})
				.focus(function() {
					$field.addClass('focus');
				});
		});

		$('.authorizenet-form [data-magic-month]').each(function() {
			var $target = $($(this).attr('data-magic-month'));
			var $month = $(this);

			$target.change(function() {
				var year = $target.find(":selected").val();
				var today = new Date();

				if ( year == today.getFullYear() ) {
					var this_month = today.getMonth() + 1;
					var selected_month = $month.find(":selected").attr("value");

					$month.find("option").each(function() {
						var value = parseInt($(this).attr("value"));
						if ( value < this_month ) {
							$(this).hide();
						}
					});

					if ( selected_month < this_month ) {
						var select = ("0"+this_month).slice(-2);
						$month.val(select);
						$month.change();
					}
				} else {
					$month.find("option").show();
				}
			});

			$target.change();
		});

	},

	process_card: function(card_info, billing_info, stored_payment_options, request_name, callback) {
		this._process({
			card_info: card_info,
			billing_info: billing_info,
			authorizenet_profile: stored_payment_options
		}, request_name, callback);
	},

	_process: function(data, request_name, callback) {
		frappe.call({
			method: "authorizenet.authorizenet.doctype.authorizenet_settings.authorizenet_settings.process",
			freeze: 1,
			freeze_message: "Processing Order. Please Wait...",
			args: {
				options: data,
				request_name: request_name
			}
		})
		.done(function(data, textStatus, xhr) {
			if(typeof data === "string") data = JSON.parse(data);
			var status = xhr.statusCode().status;

			var result = data;
			if ( result.message.status == "Completed" ) {
				callback(null, result.message);
			} else {
				var errors = [];
				if ( result.message.error.constructor != Array ) {
					errors.push(result.message.error);
				} else {
					errors = result.message.error;
				}

				callback({
					errors: errors,
					status: status,
					recoverable: result.recoverable || false,
					xhr: xhr,
					textStatus: textStatus
				}, null);
			}
		})
		.fail(function(xhr, textStatus) {
			if(typeof data === "string") data = JSON.parse(data);
			var status = xhr.statusCode().status;
			var errors = [];
			var _server_messages = null;
			if (xhr.responseJSON && xhr.responseJSON._server_messages) {
				try {
					_server_messages = JSON.parse(xhr.responseJSON._server_messages);
				} catch(ex) {
					errors.push(ex)
					_server_messages = [xhr.responseJSON._server_messages];
				}
			}

			var errors = [];
			if ( _server_messages && _server_messages.constructor == Array ) {
				try {
					for(var i = 0; i < _server_messages.length; i++) {
						var msg;
						try {
							msg = JSON.parse(_server_messages[i]);
							if ( msg.message ) {
								msg = msg.message;
							}
						} catch(ex) {
							msg = ex
						}
						errors.push("Server Error: " + msg);
					}
				} catch(ex) {
					errors.push(_server_messages);
					errors.push(ex);
				}
			}else if ( _server_messages && _server_messages.exc ) {
				errors.push(_server_messages.exc);
			}

			callback({
				errors: errors,
				status: status,
				recoverable: 0,
				xhr: xhr,
				textStatus: textStatus
			}, null);
		});

	},

	/**
	 * Collects all authnet fields necessary to process payment
	 */
	collect: function() {
		var billing_info = this.collect_billing_info();
		var card_info = this.collect_card_info();
		var stored_payment_options = this.collect_stored_payment_info();
		this.process_data = {
			card_info: card_info,
			billing_info: billing_info,
			authorizenet_profile: stored_payment_options
		}
	},

	validate: function() {
		this.collect();
		//TODO: Validate fields
		var valid = true;
		var error = {};
		var address = {};

		// stored payment path
		if ( this.process_data.authorizenet_profile &&
				 this.process_data.authorizenet_profile.payment_id ) {
			valid = true;
			address["address"] = this.process_data.authorizenet_profile.address_name;
		} else {
			// manual entry path
			if ( !this.process_data.card_info.name_on_card ) {
				valid = false;
				error['authorizenet_name'] = "Credit Card Name is required";
			}

			if ( !this.process_data.card_info.card_number ) {
				valid = false;
				error['authorizenet_number'] = "Credit Card Number is required";
			}

			if ( !this.process_data.card_info.card_code ) {
				valid = false;
				error['authorizenet_code'] = "Security Code is required";
			}

			if ( !this.process_data.card_info.exp_month ) {
				valid = false;
				error['authorizenet_exp_month'] = "Exp Month is required";
			}

			if ( !this.process_data.card_info.exp_year ) {
				valid = false;
				error['authorizenet_exp_year'] = "Exp Year is required";
			}

			if ( this.selector.is_backend ) {
				if ( !this.process_data.billing_info.pincode ) {
					valid = false;
					error['authorizenet_bill_pincode'] = "Postal Code is required";
				}
			}

			if ( this.process_data.billing_info && !this.selector.is_backend ) {
				if ( !this.process_data.billing_info.address_1 ) {
					valid = false;
					error['authorizenet_bill_line1'] = "Address line 1 is required";
				}

				if ( !this.process_data.billing_info.city ) {
					valid = false;
					error['authorizenet_bill_city'] = "City is required";
				}

				if ( !this.process_data.billing_info.pincode ) {
					valid = false;
					error['authorizenet_bill_pincode'] = "Postal Code is required";
				}

				if ( !this.process_data.billing_info.country ) {
					valid = false;
					error['authorizenet_bill_country'] = "Postal Code is required";
				}

				// copy address for awc
				for(var key in this.process_data.billing_info) {
					address[key] = this.process_data.billing_info[key]
				}
			} else if ( !this.selector.is_backend ) {
				valid = false;
			}
		} // eof-manual entry path

		return {
			valid: valid,
			errors: error,
			address: address
		}
	}

});
