"""Reports render exclusively from checked values; numbers carry JSON pointers."""
import html

def render(result, binding, simulation):
    lines = [
        "# Synthetic cohort descriptive report", "",
        "**SIMULATION — no human approval; not releasable.**" if simulation
        else "**DRAFT — awaiting human release review.**",
        "", "Research software demonstration only. No patient-care or causal conclusions.",
        "", f"Approval binding: {binding}", "",
        "Denominators are variable-specific observed counts; missing outcomes are never non-events.",
        "Sample SD uses n−1. Quantiles use linear interpolation. All records are retained.",
        "", f"Total participants: {result['total_n']} [results.json#/total_n]", ""]
    claims = [{"label": "Total participants", "pointer": "/total_n", "value": result["total_n"]}]
    def display(value):
        return "Not estimable" if value is None else f"{value:.6g}" if isinstance(value, float) else str(value)
    for group in sorted(result["groups"]):
        data = result["groups"][group]
        lines.extend([f"## Group {html.escape(group)}", ""])
        pointer = f"/groups/{group}/n"
        lines.append(f"- Participants: {display(data['n'])} [results.json#{pointer}]")
        claims.append({"label": f"{group} n", "pointer": pointer, "value": data["n"]})
        for variable in sorted(data["continuous"]):
            values = data["continuous"][variable]
            lines.extend(["", f"### {variable}", ""])
            for name in ["n", "missing", "mean", "sd", "median", "q1", "q3"]:
                value = values[name]
                pointer = f"/groups/{group}/continuous/{variable}/{name}"
                lines.append(f"- {name}: {display(value)} [results.json#{pointer}]")
                claims.append({"label": f"{group} {variable} {name}", "pointer": pointer, "value": value})
        lines.extend(["", "### Follow-up outcome", ""])
        for name in ["events", "observed", "missing", "proportion"]:
            value = data["outcome"][name]
            pointer = f"/groups/{group}/outcome/{name}"
            lines.append(f"- {name}: {display(value)} [results.json#{pointer}]")
            claims.append({"label": f"{group} outcome {name}", "pointer": pointer, "value": value})
    lines.extend(["", "Units: age_years = years; weight_kg = kg; lab_value = synthetic units.",
                  "Population frequency estimates and generalization are outside this demonstration.", ""])
    return "\n".join(lines), claims


def quality_report(qc):
    rows = ["# Data quality review", "",
            "Status: " + ("BLOCKED" if qc["blocked"] else "READY FOR PLAN REVIEW"), "",
            f"Records: {qc['rows']}", "",
            "| Variable | Missing | Percent |", "|---|---:|---:|"]
    for name, count in sorted(qc["missing"].items()):
        rows.append(f"| {name} | {count} | {qc['missing_percent'][name]:.6g}% |")
    rows.extend(["", "## Findings", "",
                 "| ID | Severity | Rule | CSV record | Variable |",
                 "|---|---|---|---:|---|"])
    for f in qc["findings"]:
        rows.append(f"| {f['id']} | {f['severity']} | {f['rule']} | {f['record']} | {f['variable']} |")
    if not qc["findings"]:
        rows.append("| — | — | No findings under implemented rules | — | — |")
    rows.extend(["", "Warnings require explicit acknowledgement by ID; no rows have been removed.",
                 "Bounds are synthetic scenario specifications, not clinical reference ranges.",
                 "No prediction task: train/test leakage checks are NOT_APPLICABLE.", ""])
    return "\n".join(rows)


def html_report(result, binding, simulation):
    """Self-contained, script-free report; each numerical cell points to JSON evidence."""
    def escape(value):
        return html.escape(str(value), quote=True)

    def cell(value, pointer):
        shown = "Not estimable" if value is None else f"{value:.6g}" if isinstance(value, float) else str(value)
        return f'<td data-evidence="{escape(pointer)}" title="{escape(pointer)}">{escape(shown)}</td>'

    sections = []
    for group, data in sorted(result["groups"].items()):
        table_rows = []
        for variable, values in sorted(data["continuous"].items()):
            cells = "".join(cell(values[key], f"/groups/{group}/continuous/{variable}/{key}")
                            for key in ["n", "missing", "mean", "sd", "median", "q1", "q3"])
            table_rows.append("<tr><th scope=\"row\">" + escape(variable) + "</th>" + cells + "</tr>")
        outcome = data["outcome"]
        outcome_cells = "".join(cell(outcome[key], f"/groups/{group}/outcome/{key}")
                                for key in ["events", "observed", "missing", "proportion"])
        sections.append(
            f'<section><h2>Group {escape(group)}</h2>'
            f'<p><span data-evidence="/groups/{escape(group)}/n">{data["n"]}</span> participants</p>'
            '<div class="scroll"><table><thead><tr><th>Variable</th><th>Observed n</th><th>Missing</th>'
            '<th>Mean</th><th>Sample SD</th><th>Median</th><th>Q1</th><th>Q3</th></tr></thead>'
            '<tbody>' + "".join(table_rows) + '</tbody></table></div>'
            '<h3>Follow-up outcome</h3><table><thead><tr><th>Events</th><th>Observed denominator</th>'
            '<th>Missing outcomes</th><th>Proportion</th></tr></thead><tbody><tr>'
            + outcome_cells + '</tr></tbody></table></section>')
    status = "SIMULATION · NO HUMAN APPROVAL" if simulation else "REVIEW COPY · RELEASE DECISION IN release.json"
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; '
        'img-src \'none\'; base-uri \'none\'; form-action \'none\'">'
        '<title>Synthetic cohort — verified descriptive analysis</title><style>'
        ':root{color-scheme:light;font-family:Segoe UI,Arial,sans-serif;color:#183047;background:#f0f4f7}'
        '*{box-sizing:border-box}body{margin:0}main{max-width:1120px;margin:auto;padding:48px 32px}'
        'header{border-top:5px solid #147d83;padding-top:24px}h1{font-size:36px;letter-spacing:-1px;margin:16px 0}'
        'h2{font-size:24px;margin:0 0 12px}h3{font-size:16px;margin-top:28px}'
        '.status{font-size:12px;font-weight:700;letter-spacing:1px;color:#875207;background:#fff0d0;'
        'display:inline-block;padding:10px 14px;border-radius:5px}'
        '.intro{font-size:17px;line-height:1.6;max-width:760px;color:#435c70}'
        'section{background:white;border:1px solid #dbe4eb;border-radius:12px;padding:28px;margin-top:24px}'
        '.cards{display:flex;gap:16px;margin:28px 0}.card{background:#e1f1f0;padding:20px;border-radius:8px;flex:1}'
        '.card strong{display:block;font-size:28px;margin-bottom:6px}.scroll{overflow:auto}'
        'table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:right;padding:13px 10px;'
        'border-bottom:1px solid #e2e9ee;white-space:nowrap}thead th{background:#f3f7fa;color:#40566a}'
        'th:first-child{text-align:left}tbody th{font-weight:500}td[data-evidence]{cursor:help}'
        '.notes{line-height:1.7;font-size:14px;color:#40566a}code{overflow-wrap:anywhere;font-size:12px}'
        'a{color:#096970}footer{margin-top:28px;font-size:13px;line-height:1.6;color:#5c6b78}'
        '@media(max-width:640px){main{padding:24px 16px}h1{font-size:28px}.cards{display:block}.card{margin:10px 0}'
        'section{padding:18px}}@media print{body{background:white}main{padding:0}section{break-inside:avoid}'
        'a{color:inherit}.cards{margin:16px 0}}'
        '</style></head><body><main><header><div class="status">' + escape(status) + '</div>'
        '<h1>Synthetic cohort analysis</h1><p class="intro">Descriptive results checked against a separate '
        'numerical implementation. This is a research-software demonstration, not a clinical finding.</p></header>'
        '<div class="cards"><div class="card"><strong data-evidence="/total_n">'
        + str(result["total_n"]) + '</strong>synthetic participants</div>'
        '<div class="card"><strong>Independent check</strong>CSV + Decimal validation</div>'
        '<div class="card"><strong>Observed values</strong>explicit denominators; no imputation</div></div>'
        + "".join(sections)
        + '<section class="notes"><h2>How to read these results</h2><p>Missing outcomes are not non-events. '
        'The outcome proportion uses only participants with an observed outcome. All accepted records are retained. '
        'Sample SD uses n−1; quartiles use linear interpolation. Not estimable means insufficient observed values.</p>'
        '<p>Units: age_years = years; weight_kg = kg; lab_value = synthetic units. The report supports no causal, '
        'treatment or population-generalization conclusion.</p>'
        '<p>Hover over a numerical cell for its JSON evidence pointer. Inspect '
        '<a href="results.json">results</a>, <a href="claims.json">claims</a>, '
        '<a href="validation.json">validation</a>, <a href="qc.md">QC review</a>, and '
        '<a href="audit.jsonl">audit history</a>.</p><p>Approval binding: <code>'
        + escape(binding) + '</code></p></section><footer>'
        'The status and approval artifacts determine release eligibility. A simulation cannot receive human release. '
        'Local attestations and hash chains do not constitute authenticated identity or clinical certification.'
        '</footer></main></body></html>')
