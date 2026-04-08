import frappe
from frappe import _
from frappe.utils import flt, cint


def apply_gl_rules(doc, gl_entries):
	"""Apply all matching GL Entry Rules to modify the GL entry map.

	Called from overridden get_gl_entries() on Purchase Invoice and Delivery Note.
	Returns the modified gl_entries list.
	"""
	rules = get_matching_rules(doc)
	if not rules:
		return gl_entries

	for rule in rules:
		if not evaluate_condition(rule, doc):
			continue

		# Suppress default entries
		if rule.suppress_default_entries:
			gl_entries = []
		elif rule.suppress_filters:
			gl_entries = apply_suppress_filters(gl_entries, rule.suppress_filters)

		# Build and validate custom entries
		custom_entries = build_custom_entries(doc, rule)
		validate_group_balance(custom_entries, rule.name)

		gl_entries.extend(custom_entries)

	return gl_entries


def get_matching_rules(doc):
	"""Fetch enabled GL Entry Rules matching this document."""
	filters = {
		"enabled": 1,
		"source_doctype": doc.doctype,
	}

	rules = frappe.get_all(
		"GL Entry Rule",
		filters=filters,
		fields=["name"],
		order_by="priority desc, creation asc",
	)

	result = []
	for r in rules:
		rule = frappe.get_doc("GL Entry Rule", r.name)
		# Filter by company if set on the rule
		if rule.company and rule.company != doc.company:
			continue
		result.append(rule)

	return result


def evaluate_condition(rule, doc):
	"""Evaluate the rule's condition expression against the document."""
	if not rule.condition:
		return True

	try:
		return frappe.safe_eval(
			rule.condition,
			eval_globals=_get_eval_globals(doc),
		)
	except Exception as e:
		frappe.log_error(
			title=f"GL Customizer: Condition error in rule '{rule.name}'",
			message=str(e),
		)
		return False


def apply_suppress_filters(gl_entries, filters):
	"""Remove GL entries matching the suppress filter criteria."""
	result = []
	for entry in gl_entries:
		suppress = False
		account = (entry.get("account") or "").lower()

		for f in filters:
			pattern = (f.account_contains or "").lower()
			if pattern and pattern in account:
				side = f.side or "Both"
				if side == "Both":
					suppress = True
				elif side == "Debit" and flt(entry.get("debit")) > 0:
					suppress = True
				elif side == "Credit" and flt(entry.get("credit")) > 0:
					suppress = True

		if not suppress:
			result.append(entry)

	return result


def build_custom_entries(doc, rule):
	"""Build GL entry dicts from a rule's entry lines."""
	entries = []

	for line in rule.entry_lines:
		eval_globals = _get_eval_globals(doc)

		# Resolve account
		account = line.account
		if not account and line.account_field:
			account = _safe_eval_field(line.account_field, eval_globals, f"account_field row {line.idx}")
		if not account:
			frappe.throw(
				_("GL Customizer rule '{0}', row {1}: Could not resolve account.").format(
					rule.name, line.idx
				)
			)

		# Resolve amounts
		debit = flt(_safe_eval_field(line.debit_formula, eval_globals, f"debit_formula row {line.idx}")) if line.debit_formula else 0
		credit = flt(_safe_eval_field(line.credit_formula, eval_globals, f"credit_formula row {line.idx}")) if line.credit_formula else 0

		if debit == 0 and credit == 0:
			continue

		# Resolve party
		party_type = line.party_type or None
		party = None
		if line.party_field:
			party = _safe_eval_field(line.party_field, eval_globals, f"party_field row {line.idx}")

		# Resolve cost center
		cost_center = line.cost_center
		if not cost_center and line.cost_center_field:
			cost_center = _safe_eval_field(line.cost_center_field, eval_globals, f"cost_center_field row {line.idx}")

		# Build GL dict using the document's helper for proper structure
		gl_dict = doc.get_gl_dict(
			{
				"account": account,
				"debit": debit,
				"credit": credit,
				"debit_in_account_currency": debit,
				"credit_in_account_currency": credit,
				"against": account,
				"party_type": party_type,
				"party": party,
				"cost_center": cost_center or doc.get("cost_center"),
				"remarks": line.remarks or _("GL Customizer: {0}").format(rule.name),
			},
			item=None,
		)

		# Tag with entry group for validation (not saved to DB)
		gl_dict["_entry_group"] = line.entry_group
		entries.append(gl_dict)

	return entries


def validate_group_balance(entries, rule_name):
	"""Validate that entries within each entry group balance."""
	groups = {}
	for entry in entries:
		group = entry.get("_entry_group", "default")
		if group not in groups:
			groups[group] = {"debit": 0, "credit": 0}
		groups[group]["debit"] += flt(entry.get("debit"))
		groups[group]["credit"] += flt(entry.get("credit"))

	for group, totals in groups.items():
		diff = abs(totals["debit"] - totals["credit"])
		if diff > 0.001:
			frappe.throw(
				_(
					"GL Customizer rule '{0}': Entry group '{1}' is not balanced. "
					"Debit: {2}, Credit: {3}, Difference: {4}"
				).format(
					rule_name,
					group,
					frappe.format_value(totals["debit"], {"fieldtype": "Currency"}),
					frappe.format_value(totals["credit"], {"fieldtype": "Currency"}),
					frappe.format_value(diff, {"fieldtype": "Currency"}),
				),
				title=_("GL Entry Imbalance"),
			)


def _get_eval_globals(doc):
	"""Build the safe evaluation context."""
	return {
		"doc": doc,
		"flt": flt,
		"cint": cint,
		"abs": abs,
		"sum": sum,
		"len": len,
		"round": round,
	}


def _safe_eval_field(expression, eval_globals, context_label):
	"""Safely evaluate a formula field expression."""
	if not expression:
		return None

	try:
		return frappe.safe_eval(expression, eval_globals=eval_globals)
	except Exception as e:
		frappe.throw(
			_("GL Customizer: Error evaluating {0}: {1}").format(context_label, str(e)),
			title=_("Expression Error"),
		)
