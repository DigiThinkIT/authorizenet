frappe.provide("frappe.integration_service")

frappe.integration_service.authorizenet_gateway = Class.extend({
  init: function() {

  },

  process: function(card_info, billing_info, reference_id, callback) {

    frappe.call({
      method: "authorizenet.templates.pages.integrations.authorizenet_checkout.process",
      args: {
        options: {
          card_info: card_info,
          billing_info: billing_info,
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
