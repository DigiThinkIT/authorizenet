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

  billing_fields: {
    "authorizenet_bill_line1": "address_1",
    "authorizenet_bill_line2": "address_2",
    "authorizenet_bill_city": "city",
    "authorizenet_bill_state": "state",
    "authorizenet_bill_pincode": "pincode",
    "authorizenet_bill_country": "country"
  },

  init: function() {

  },

  collect_billing_info: function() {
    var billing_info = {};
    // collect billing field values
    for(var field in this.billing_fields) {
      var $field = $('#'+field);
      billing_info[this.billing_fields[field]] = $field.val();
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
      },
      callback: function(result) {
        if ( result.message.status == "Completed" ) {
          callback(null, result.message);
        } else {
          callback(result.message, null);
        }
      },
      error: function(err) {
        callback(err, null);
      }
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

      if ( this.process_data.billing_info ) {
        if ( !this.process_data.billing_info.address_1 ) {
          valid = false;
          error['authorizenet_bill_line1'] = "Address line 1 is required";
        }

        if ( !this.process_data.billing_info.city ) {
          valid = false;
          error['authorizenet_bill_city'] = "City is required";
        }

        if ( !this.process_data.billing_info.state ) {
          valid = false;
          error['authorizenet_bill_state'] = "State is required";
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
      } else {
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
