from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice

from gl_customizer.utils.gl_entry_builder import apply_gl_rules


class CustomPurchaseInvoice(PurchaseInvoice):
	def get_gl_entries(self, inventory_account_map=None):
		gl_entries = super().get_gl_entries(inventory_account_map)
		return apply_gl_rules(self, gl_entries)
