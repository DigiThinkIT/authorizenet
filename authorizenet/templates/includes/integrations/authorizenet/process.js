frappe.provide("authorizenet");

authorizenet.form = function(charge_info, reference_doctype, reference_docname) {

  $(function() {

    

  })

}

authorizenet.process = function(charge_info, card_info, billing_info, reference_doctype, reference_docname, callback) {

  frappe.call({
    method: "templates.pages.integrations.authorizenet_checkout.process",
    args: {
      charge_info: charge_info,
      card_info: card_info,
      billing_info: billing_info,
      reference_doctype: reference_doctype,
      reference_docname: reference_docname
    },
    callback: function(result) {
      if ( result.message.success ) {
        callback(null, result.message.data);
      } else {
        callback(result.message.error, null);
      }
    }
  });

}
