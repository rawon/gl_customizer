app_name = "gl_customizer"
app_title = "GL Entry Customizer"
app_publisher = "Aditya W"
app_description = "Configure which GL entries are created when Purchase Invoices and Delivery Notes are submitted"
app_email = "aditya@example.com"
app_license = "MIT"

override_doctype_class = {
	"Purchase Invoice": "gl_customizer.overrides.purchase_invoice.CustomPurchaseInvoice",
	"Delivery Note": "gl_customizer.overrides.delivery_note.CustomDeliveryNote",
}
