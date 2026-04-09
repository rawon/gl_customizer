frappe.ui.form.on("GL Entry Rule", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Test Rule"), function () {
				let doctype = frm.doc.source_doctype;
				if (!doctype) {
					frappe.msgprint(__("Please select a Source Document Type first."));
					return;
				}

				let d = new frappe.ui.Dialog({
					title: __("Test GL Entry Rule"),
					fields: [
						{
							fieldname: "source_doc",
							fieldtype: "Link",
							label: __(doctype),
							options: doctype,
							reqd: 1,
							description: __(
								"Select a submitted {0} to test this rule against.",
								[doctype]
							),
						},
					],
					primary_action_label: __("Test"),
					primary_action(values) {
						d.hide();
						frappe.call({
							method: "gl_customizer.gl_customizer.doctype.gl_entry_rule.gl_entry_rule.test_rule",
							args: {
								rule_name: frm.doc.name,
								source_doc_name: values.source_doc,
							},
							callback(r) {
								if (r.message) {
									show_test_results(r.message);
								}
							},
						});
					},
				});
				d.show();
			});
		}
	},
});

function show_test_results(result) {
	let html = `<p>${result.message}</p>`;

	if (result.entries && result.entries.length) {
		html += `<table class="table table-bordered table-sm">
			<thead>
				<tr>
					<th>${__("Account")}</th>
					<th class="text-right">${__("Debit")}</th>
					<th class="text-right">${__("Credit")}</th>
					<th>${__("Party")}</th>
					<th>${__("Cost Center")}</th>
				</tr>
			</thead>
			<tbody>`;

		let total_debit = 0;
		let total_credit = 0;

		for (let entry of result.entries) {
			total_debit += entry.debit || 0;
			total_credit += entry.credit || 0;
			html += `<tr>
				<td>${entry.account || ""}</td>
				<td class="text-right">${frappe.format(entry.debit, { fieldtype: "Currency" })}</td>
				<td class="text-right">${frappe.format(entry.credit, { fieldtype: "Currency" })}</td>
				<td>${entry.party ? entry.party_type + ": " + entry.party : ""}</td>
				<td>${entry.cost_center || ""}</td>
			</tr>`;
		}

		html += `<tr class="font-weight-bold">
				<td>${__("Total")}</td>
				<td class="text-right">${frappe.format(total_debit, { fieldtype: "Currency" })}</td>
				<td class="text-right">${frappe.format(total_credit, { fieldtype: "Currency" })}</td>
				<td colspan="2"></td>
			</tr>`;

		let balanced = Math.abs(total_debit - total_credit) < 0.01;
		html += `<tr>
				<td colspan="5" class="text-center ${balanced ? "text-success" : "text-danger"}">
					${balanced ? __("Balanced") : __("IMBALANCED: Debit - Credit = ") + frappe.format(total_debit - total_credit, { fieldtype: "Currency" })}
				</td>
			</tr>`;

		html += `</tbody></table>`;
	}

	frappe.msgprint({ title: __("Test Results"), message: html, wide: true });
}
