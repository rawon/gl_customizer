import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, cint


class GLEntryRule(Document):
	def validate(self):
		self.validate_condition_syntax()
		if self.enable_custom_entries:
			self.validate_formula_syntax()
			self.validate_entry_lines()
			self.validate_account_fields()

	def validate_condition_syntax(self):
		if self.condition:
			try:
				compile(self.condition, "<condition>", "eval")
			except SyntaxError as e:
				frappe.throw(
					_("Invalid syntax in Condition: {0}").format(str(e)),
					title=_("Syntax Error"),
				)

	def validate_formula_syntax(self):
		for line in self.entry_lines:
			for field in ("debit_formula", "credit_formula", "account_field", "party_field", "cost_center_field"):
				expr = line.get(field)
				if expr:
					try:
						compile(expr, f"<{field} row {line.idx}>", "eval")
					except SyntaxError as e:
						frappe.throw(
							_("Row {0}: Invalid syntax in {1}: {2}").format(
								line.idx, field, str(e)
							),
							title=_("Syntax Error"),
						)

	def validate_entry_lines(self):
		if not self.entry_lines:
			frappe.throw(_("At least one Entry Line is required."))

		has_debit = any(line.debit_formula for line in self.entry_lines)
		has_credit = any(line.credit_formula for line in self.entry_lines)

		if not has_debit or not has_credit:
			frappe.msgprint(
				_("Warning: Entry lines have only {0} formulas. They may not balance.").format(
					"debit" if has_debit else "credit"
				),
				indicator="orange",
				alert=True,
			)

	def validate_account_fields(self):
		for line in self.entry_lines:
			if not line.account and not line.account_field:
				frappe.throw(
					_("Row {0}: Either Account or Account Field is required.").format(line.idx),
					title=_("Missing Account"),
				)
			if line.account and line.account_field:
				frappe.throw(
					_("Row {0}: Set either Account or Account Field, not both.").format(line.idx),
					title=_("Ambiguous Account"),
				)


@frappe.whitelist()
def test_rule(rule_name, source_doc_name):
	"""Dry-run a GL Entry Rule against a document and return preview of entries."""
	rule = frappe.get_doc("GL Entry Rule", rule_name)
	doc = frappe.get_doc(rule.source_doctype, source_doc_name)

	from gl_customizer.utils.gl_entry_builder import build_custom_entries, evaluate_condition

	if not evaluate_condition(rule, doc):
		return {"message": _("Condition did not match for this document."), "entries": []}

	entries = build_custom_entries(doc, rule)

	preview = []
	for entry in entries:
		preview.append({
			"account": entry.get("account"),
			"debit": flt(entry.get("debit"), 2),
			"credit": flt(entry.get("credit"), 2),
			"party_type": entry.get("party_type"),
			"party": entry.get("party"),
			"cost_center": entry.get("cost_center"),
			"remarks": entry.get("remarks"),
		})

	return {"message": _("Rule matched. Preview below."), "entries": preview}
