from html import escape

from app.schemas.engineering import (
    CalculationResult,
    CalculationSnapshot,
    EngineeringQuantity,
)
from app.schemas.project import ProjectResponse, ProjectReviewResponse
from app.schemas.review import EvidenceItem, Finding, Severity


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _number(value: float) -> str:
    return format(value, ".8g")


def _quantity(value: EngineeringQuantity | None) -> str:
    if value is None:
        return '<span class="missing">未提供</span>'
    return f"{_text(_number(value.value))} {_text(value.unit)}"


def _optional_text(value: str | None) -> str:
    if value is None or not value.strip():
        return '<span class="missing">未提供</span>'
    return _text(value)


def _specification_rows(project: ProjectResponse) -> str:
    rows: tuple[tuple[str, str], ...] = (
        ("拓扑", _text(project.topology)),
        ("输入电压 Vin Min", _quantity(project.vin_min)),
        ("输入电压 Vin Nom", _quantity(project.vin_nom)),
        ("输入电压 Vin Max", _quantity(project.vin_max)),
        ("输出电压 Vout", _quantity(project.vout)),
        ("输出电流 Iout", _quantity(project.iout)),
        ("输出功率 Pout", _quantity(project.pout)),
        ("目标效率", _quantity(project.target_efficiency)),
        ("谐振电感 Lr", _quantity(project.lr)),
        ("励磁电感 Lm", _quantity(project.lm)),
        ("谐振电容 Cr", _quantity(project.cr)),
        ("开关频率 Fsw Min", _quantity(project.fsw_min)),
        ("开关频率 Fsw Nom", _quantity(project.fsw_nom)),
        ("开关频率 Fsw Max", _quantity(project.fsw_max)),
        ("变压器匝比", _quantity(project.transformer_ratio)),
        ("Dead Time", _quantity(project.dead_time)),
        ("整流方式", _text(project.rectification_type)),
        ("主开关制造商", _optional_text(project.primary_switch.manufacturer)),
        ("主开关型号", _optional_text(project.primary_switch.part_number)),
        ("MOSFET VDS Rating", _quantity(project.primary_switch.vds_rating)),
        ("控制器型号", _optional_text(project.controller.model)),
        ("控制器最低频率", _quantity(project.controller.frequency_min)),
        ("控制器最高频率", _quantity(project.controller.frequency_max)),
    )
    return "".join(
        f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in rows
    )


def _calculation_rows(
    calculation_snapshot: CalculationSnapshot,
) -> tuple[str, tuple[str, ...]]:
    rows: list[str] = []
    versions: set[str] = set()
    for result in calculation_snapshot.calculations:
        versions.add(result.formula_version)
        rows.append(
            "<tr>"
            f"<td>{_text(result.name)}</td>"
            f"<td>{_text(_number(result.value))}</td>"
            f"<td>{_text(result.unit)}</td>"
            f"<td><code>{_text(result.formula_version)}</code></td>"
            "</tr>"
        )
    if not rows:
        return (
            '<tr><td colspan="4" class="empty-cell">本次 Review 没有可展示的结构化计算结果。</td></tr>',
            tuple(sorted(versions)),
        )
    return "".join(rows), tuple(sorted(versions))


def _evidence_item(evidence: EvidenceItem) -> str:
    values = "".join(
        f"<li><code>{_text(name)}</code>: {_quantity(value)}</li>"
        for name, value in evidence.values.items()
    )
    references = "".join(
        f"<code>{_text(reference)}</code>" for reference in evidence.references
    )
    return (
        '<li class="evidence-item">'
        f'<span class="source">{_text(evidence.source.value)}</span>'
        f"<p>{_text(evidence.description)}</p>"
        f"{'<ul>' + values + '</ul>' if values else ''}"
        f"{'<div class=\"references\">' + references + '</div>' if references else ''}"
        "</li>"
    )


def _finding_card(finding: Finding) -> str:
    calculated_values = "".join(
        (
            f"<li><code>{_text(name)}</code>: {_text(_number(value.value))} "
            f"{_text(value.unit)}"
            + (
                f" <small>({_text(value.formula_version)})</small>"
                if isinstance(value, CalculationResult)
                else ""
            )
            + "</li>"
        )
        for name, value in finding.calculated_values.items()
    )
    missing = "".join(
        f"<li>{_text(item)}</li>" for item in finding.missing_information
    )
    actions = "".join(
        f"<li>{_text(item)}</li>" for item in finding.recommended_action
    )
    evidence = "".join(_evidence_item(item) for item in finding.evidence)
    confirmation = (
        '<p class="engineer-confirmation">Requires qualified engineer review.</p>'
        if finding.requires_engineer_confirmation
        else ""
    )
    return (
        f'<article class="finding finding-{finding.severity.value.lower()}">'
        '<div class="finding-heading">'
        f'<code class="rule-id">{_text(finding.rule_id)}</code>'
        f"<h3>{_text(finding.title)}</h3>"
        f'<span class="badge">{_text(finding.severity.value)}</span>'
        "</div>"
        f"<p>{_text(finding.description)}</p>"
        + (
            '<div class="finding-detail"><h4>Calculated Data</h4><ul>'
            + calculated_values
            + "</ul></div>"
            if calculated_values
            else ""
        )
        + (
            '<div class="finding-detail"><h4>Evidence</h4><ul class="evidence-list">'
            + evidence
            + "</ul></div>"
            if evidence
            else ""
        )
        + (
            '<div class="finding-detail"><h4>Missing Information</h4><ul>'
            + missing
            + "</ul></div>"
            if missing
            else ""
        )
        + (
            '<div class="finding-detail"><h4>Recommended Next Step</h4><ul>'
            + actions
            + "</ul></div>"
            if actions
            else ""
        )
        + confirmation
        + "</article>"
    )


def _finding_section(
    title: str,
    findings: tuple[Finding, ...],
    empty_message: str,
) -> str:
    content = (
        "".join(_finding_card(finding) for finding in findings)
        if findings
        else f'<p class="empty-message">{_text(empty_message)}</p>'
    )
    return f'<section class="report-section"><h2>{_text(title)}</h2>{content}</section>'


def render_design_review_report(
    project: ProjectResponse,
    review: ProjectReviewResponse,
    calculation_snapshot: CalculationSnapshot,
) -> str:
    """Render a self-contained report without invoking calculations or rules."""

    calculation_rows, versions = _calculation_rows(calculation_snapshot)
    versions_markup = (
        "".join(f"<li><code>{_text(version)}</code></li>" for version in versions)
        if versions
        else '<li class="missing">无可用 Calculation Version</li>'
    )
    findings_by_severity = {
        severity: tuple(
            finding for finding in review.findings if finding.severity == severity
        )
        for severity in Severity
    }
    summary = review.summary

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_text(project.name)} · LLC Design Review Report</title>
  <style>
    :root {{ color: #20312b; background: #eef1ef; font-family: Inter, "Segoe UI", "Microsoft YaHei", sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; line-height: 1.6; }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 32px auto; padding: 46px; border: 1px solid #d9e1dd; border-radius: 20px; background: white; box-shadow: 0 18px 50px rgb(31 65 53 / 8%); }}
    header {{ padding-bottom: 28px; border-bottom: 3px solid #1f7658; }}
    .eyebrow {{ margin: 0 0 8px; color: #237a5d; font-size: 12px; font-weight: 800; letter-spacing: .14em; }}
    h1 {{ margin: 0; color: #15372d; font-size: 34px; line-height: 1.2; }}
    .metadata {{ display: flex; flex-wrap: wrap; gap: 8px 24px; margin-top: 18px; color: #65756f; font-size: 13px; }}
    .report-section {{ margin-top: 36px; }}
    h2 {{ padding-bottom: 9px; border-bottom: 1px solid #dce4e0; color: #21473a; font-size: 19px; }}
    h3 {{ margin: 0; font-size: 15px; }}
    h4 {{ margin: 15px 0 4px; color: #557068; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ padding: 10px 12px; border: 1px solid #e0e6e3; text-align: left; vertical-align: top; }}
    th {{ width: 30%; color: #405b52; background: #f4f7f5; }}
    .calculation-table th {{ width: auto; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }}
    .summary-card {{ padding: 15px; border: 1px solid #dce4e0; border-radius: 10px; background: #f8faf9; }}
    .summary-card span, .summary-card strong {{ display: block; }}
    .summary-card span {{ color: #6b7d76; font-size: 10px; font-weight: 800; letter-spacing: .07em; }}
    .summary-card strong {{ margin-top: 5px; font-size: 24px; }}
    .finding {{ margin-top: 12px; padding: 18px; border: 1px solid #dce4e0; border-left: 4px solid #80958d; border-radius: 10px; break-inside: avoid; }}
    .finding-critical {{ border-left-color: #bc3d3d; background: #fffafa; }}
    .finding-warning {{ border-left-color: #c49328; background: #fffdf7; }}
    .finding-insufficient_data {{ border-left-color: #76649a; background: #fcfbff; }}
    .finding-pass {{ border-left-color: #2d8a65; }}
    .finding-heading {{ display: grid; grid-template-columns: 84px 1fr auto; gap: 10px; align-items: center; }}
    .rule-id {{ color: #6e7e78; font-size: 11px; }}
    .badge {{ padding: 4px 7px; border-radius: 5px; color: #3e544c; font-size: 10px; font-weight: 800; background: #e8eeeb; }}
    .finding > p {{ margin: 10px 0 0; color: #51665f; font-size: 13px; }}
    .finding-detail ul {{ margin: 4px 0 0; padding-left: 20px; font-size: 12px; }}
    .evidence-item {{ margin-top: 8px; }}
    .evidence-item p {{ display: inline; margin-left: 7px; }}
    .source {{ padding: 2px 5px; border-radius: 4px; color: #255d49; font-size: 10px; font-weight: 700; background: #e1f0e9; }}
    .references {{ display: flex; flex-wrap: wrap; gap: 5px; margin-top: 4px; }}
    .references code {{ padding: 2px 5px; background: #f0f3f1; }}
    .missing, .empty-message, .empty-cell {{ color: #8a7777; font-style: italic; }}
    .engineer-confirmation {{ padding: 9px 11px; border-radius: 6px; color: #8d2d2d !important; font-weight: 700; background: #fbe9e9; }}
    .disclaimer {{ padding: 18px; border: 1px solid #d8dedb; border-radius: 10px; color: #4f625b; font-size: 13px; background: #f5f7f6; }}
    footer {{ margin-top: 38px; padding-top: 18px; border-top: 1px solid #dce4e0; color: #788780; font-size: 11px; }}
    @media (max-width: 760px) {{ main {{ width: 100%; margin: 0; padding: 22px; border-radius: 0; }} .summary-grid {{ grid-template-columns: repeat(2, 1fr); }} .finding-heading {{ grid-template-columns: 70px 1fr; }} .badge {{ grid-column: 2; justify-self: start; }} }}
    @media print {{ :root {{ background: white; }} main {{ width: 100%; margin: 0; padding: 0; border: 0; box-shadow: none; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <p class="eyebrow">LLC ENGINEERING ASSISTANT · DESIGN REVIEW REPORT</p>
    <h1>{_text(project.name)}</h1>
    <div class="metadata">
      <span>Project ID: <code>{_text(project.id)}</code></span>
      <span>Review ID: <code>{_text(review.review_id)}</code></span>
      <span>Review Time: {_text(review.created_at.isoformat())}</span>
    </div>
  </header>

  <section class="report-section">
    <h2>1. 项目信息与设计规格</h2>
    <table><tbody>{_specification_rows(project)}</tbody></table>
  </section>

  <section class="report-section">
    <h2>2. 结构化计算结果</h2>
    <table class="calculation-table">
      <thead><tr><th>Result</th><th>Value</th><th>Unit</th><th>Formula Version</th></tr></thead>
      <tbody>{calculation_rows}</tbody>
    </table>
  </section>

  <section class="report-section">
    <h2>3. Review Summary</h2>
    <div class="summary-grid">
      <div class="summary-card"><span>PASS</span><strong>{summary.pass_count}</strong></div>
      <div class="summary-card"><span>INFO</span><strong>{summary.info}</strong></div>
      <div class="summary-card"><span>WARNING</span><strong>{summary.warning}</strong></div>
      <div class="summary-card"><span>CRITICAL</span><strong>{summary.critical}</strong></div>
      <div class="summary-card"><span>INSUFFICIENT DATA</span><strong>{summary.insufficient_data}</strong></div>
    </div>
  </section>

  {_finding_section("4. Critical Findings", findings_by_severity[Severity.CRITICAL], "本次 Review 没有 CRITICAL Finding。")}
  {_finding_section("5. Warnings", findings_by_severity[Severity.WARNING], "本次 Review 没有 WARNING Finding。")}
  {_finding_section("6. Missing Information", findings_by_severity[Severity.INSUFFICIENT_DATA], "本次 Review 没有 INSUFFICIENT_DATA Finding。")}
  {_finding_section("7. Passed Checks", findings_by_severity[Severity.PASS], "本次 Review 没有 PASS Finding。")}
  {_finding_section("8. Information Findings", findings_by_severity[Severity.INFO], "本次 Review 没有 INFO Finding。")}

  <section class="report-section">
    <h2>9. Calculation Versions</h2>
    <ul>{versions_markup}</ul>
  </section>

  <section class="report-section">
    <h2>10. Engineering Disclaimer</h2>
    <div class="disclaimer">
      <p>本报告由确定性计算结果和结构化 Design Review Finding 生成，仅用于辅助具备专业能力的电力电子工程师进行研发评审。</p>
      <p>本报告不是安全认证、法规符合性证明或量产批准。PASS 仅表示对应有限规则通过；缺少器件条件、实测波形、温度、容差、保护与验证数据时，不得据此声明设计安全。</p>
      <p>任何 WARNING、CRITICAL 或高风险工程决策均需要合格工程师结合原始 Evidence 复核。</p>
    </div>
  </section>

  <footer>Generated from persisted Review ID {_text(review.review_id)}. The reporting layer did not recalculate engineering results.</footer>
</main>
</body>
</html>"""
