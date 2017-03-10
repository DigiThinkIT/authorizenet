frappe.provide("frappe.gateway_selector")

frappe.gateway_selector.authorizenet_embed =  frappe.integration_service.authorizenet_gateway.extend({
  _initialized: false,

  show: function() {
    console.log("Show authnet form")
    if ( !this._initialized ) {
      this.form('');
    }
  },

  hide: function() {
    console.log("Hide authnet form")
  },

  collect_data: function() {

  },

  process: function(data, callback) {

  }

});
