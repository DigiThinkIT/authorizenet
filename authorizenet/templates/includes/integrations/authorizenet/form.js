frappe.provide("frappe.integration_service")

{% include "templates/includes/integrations/authorizenet/process.js" with context %}

frappe.integration_service.authorizenet_gateway =  frappe.integration_service.authorizenet_gateway.extend({
  form: function(reference_id) {

    var card_fields = {
      "authorizenet_name": "name_on_card",
      "authorizenet_number": "card_number",
      "authorizenet_code": "card_code",
      "authorizenet_exp_month": "exp_month",
      "authorizenet_exp_year": "exp_year",
      "authorizenet_store_payment": "store_payment"
    }

    var billing_fields = {
      "authorizenet_bill_line1": "address_1",
      "authorizenet_bill_line2": "address_2",
      "authorizenet_bill_city": "city",
      "authorizenet_bill_state": "state",
      "authorizenet_bill_zip": "postal_code",
      "authorizenet_bill_country": "country"
    }

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

    var base = this;
    $(function() {
      // trigger processing info
      $('#authorizenet-process-btn').click(function() {
        var billing_info = {};
        var card_info = {}

        // collect billing field values
        for(var field in billing_fields) {
          var $field = $('#'+field);
          billing_info[billing_fields[field]] = $field.val();
        }

        // collect card field values
        for(var field in card_fields) {
          var $field = $('#'+field);
          card_info[card_fields[field]] = $field.val();
        }

        $('#authorizenet-payment').fadeOut('fast');
        $('#authorizenet-process-btn').fadeOut('fast');
        base.process(card_info, billing_info, reference_id,
          function(err, result) {
            console.dir(result);
            if ( err ) {
              $('#authorizenet-error').text(err.error)
              $('#authorizenet-payment').fadeIn('fast');
              $('#authorizenet-process-btn').fadeIn('fast');
            } else {
              window.location.href = result.redirect_to;
            }
          })
      })

    })

  }

});
