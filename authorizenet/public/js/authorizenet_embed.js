frappe.provide("frappe.gateway_selector")

frappe.gateway_selector.authorizenet_embed =  frappe.integration_service.authorizenet_gateway.extend({
  _initialized: false,

  /**
   * Called when the form is displayed
   */
  show: function() {
    if ( !this._initialized ) {
      this.form('');
    }

    $('#gateway-selector-continue').text("Submit Payment");
  },

  /**
   * Called when the form is hidden
   */
  hide: function() {
    // form was hidden
  },

  /**
   * Collects all authnet fields necessary to process payment
   */
  collect: function() {
    var billing_info = base.collect_billing_info();
    var card_info = base.collect_card_info();
    var stored_payment_options = base.collect_stored_payment_info();
    this.process_data = {
      card_info: card_info,
      billing_info: billing_info,
      authorizenet_profile: stored_payment_options
    }
  },

  /**
   * Process card. Requires a callback function of the form (err, data).
   *
   * When err is not undefined, the payment processing failed. Err should have
   * information about the error.
   *
   * When data is not undefined, the payment processing was successful. Data
   * should return an object of the form:
   * {
   *    redirect_to: <success url>,
   *    status: <status string from Integration Request doctype>
   * }
   */
  process: function(overrides, callback) {
    var data = Object.assign({}, this.process_data, overrides);
    this._process(data, null, callback);
  }

});
