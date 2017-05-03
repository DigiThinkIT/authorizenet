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
  },

  getSummary: function() {
    this.collect()

    var stored_payment_label = false;
    if ( this.process_data.authorizenet_profile && this.process_data.authorizenet_profile.payment_id ) {
      stored_payment_label = $('input[name="authorizednet-stored-payment"]:checked').siblings('.long-text').html();
    }

    return frappe.render(frappe.templates.authorizenet_summary, Object.assign({
        store_payments: $('#authorizenet_store_payment').is(':checked'),
        stored_payment_label: stored_payment_label
      }, this.process_data));
  }

});
