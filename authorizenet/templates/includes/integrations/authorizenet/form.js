frappe.provide("frappe.integration_service")

{% include "templates/includes/integrations/authorizenet/process.js" with context %}

frappe.integration_service.authorizenet_gateway =  frappe.integration_service.authorizenet_gateway.extend({
  form: function(reference_id) {
    this._super();
    var base = this;
    $(function() {
      // trigger processing info
      $('#authorizenet-process-btn').click(function() {
        var billing_info = base.collect_billing_info();
        var card_info = base.collect_card_info();
        var stored_payment_options = base.collect_stored_payment_info();

        $('#authorizenet-payment').fadeOut('fast');
        $('#authorizenet-process-btn').fadeOut('fast');
        base.process_card(card_info, billing_info, stored_payment_options, reference_id,
          function(err, result) {
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
