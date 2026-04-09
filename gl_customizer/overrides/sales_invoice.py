from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice

from gl_customizer.utils.gl_entry_builder import apply_gl_rules


class CustomSalesInvoice(SalesInvoice):
	def get_gl_entries(self, inventory_account_map=None):
		gl_entries = super().get_gl_entries(inventory_account_map)
		return apply_gl_rules(self, gl_entries)
