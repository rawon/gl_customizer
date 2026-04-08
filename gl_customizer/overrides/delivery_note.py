from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote

from gl_customizer.utils.gl_entry_builder import apply_gl_rules


class CustomDeliveryNote(DeliveryNote):
	def get_gl_entries(
		self, inventory_account_map=None, default_expense_account=None, default_cost_center=None
	):
		gl_entries = super().get_gl_entries(
			inventory_account_map, default_expense_account, default_cost_center
		)
		return apply_gl_rules(self, gl_entries)
