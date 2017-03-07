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
    "authorizenet_bill_zip": "postal_code",
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
    if ( stored_payment_option != "none" ) {
      return null;
    }

    // collect card field values
    for(var field in this.card_fields) {
      var $field = $('#'+field);
      card_info[this.card_fields[field]] = $field.val();
    }
    return card_info;
  },

  collect_stored_payment_info: function() {
    var stored_payment_option = $('input[name="authorizednet-stored-payment"]:checked').val();
    if ( stored_payment_option == "none" ) {
      return null;
    }

    return {
      "payment_id": stored_payment_option
    }
  },

  form: function(reference_id) {
    $('input[name="authorizednet-stored-payment"]').change(function() {
      if ( $(this).val() != 'none' ) {
        $('#authorizenet-manual-info').slideUp('slow');
      } else {
        $('#authorizenet-manual-info').slideDown('slow');
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

  process: function(card_info, billing_info, stored_payment_options, reference_id, callback) {

    frappe.call({
      method: "authorizenet.templates.pages.integrations.authorizenet_checkout.process",
      args: {
        options: {
          card_info: card_info,
          billing_info: billing_info,
          authorizenet_profile: stored_payment_options
        },
        request_name: reference_id
      },
      callback: function(result) {
        if ( result.message.status == "Completed" ) {
          callback(null, result.message);
        } else {
          callback(result.message, null);
        }
      }
    });

  }

});

if ( $.mobile ) {
  alert('mobile');
}
