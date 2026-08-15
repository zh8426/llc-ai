import { useMemo } from 'react'

import { reportUrl } from '../api'
import type { EngineeringQuantity, Finding, Review } from '../types'
import {
  categoryLabels,
  dataLabel,
  evidenceSourceLabels,
  findingTitleLabels,
  formatCalculatedValue,
  formatQuantity,
  inputData,
  severityLabels,
} from '../reviewLabels'

function DataList({ values }: { values: Array<[string, EngineeringQuantity]> }) {
  if (values.length === 0) return <p className="empty-detail">无直接用户输入数据。</p>
  return (
    <dl className="data-list">
      {values.map(([name, value]) => (
        <div key={name}>
          <dt>{dataLabel(name)}</dt>
          <dd>{formatQuantity(value)}</dd>
        </div>
      ))}
    </dl>
  )
}

function FindingCard({ finding }: { finding: Finding }) {
  const inputs = inputData(finding)
  const calculated = Object.entries(finding.calculated_values)
  return (
    <details className={`finding finding-${finding.severity.toLowerCase()}`}>
      <summary>
        <span className="rule-id">{finding.rule_id}</span>
        <strong>{findingTitleLabels[finding.rule_id] ?? finding.title}</strong>
        <span className={`severity severity-${finding.severity.toLowerCase()}`}>
          {severityLabels[finding.severity]}
        </span>
      </summary>
      <div className="finding-body">
        <section>
          <h4>为什么</h4>
          <p>{finding.description}</p>
        </section>

        <section>
          <h4>输入数据</h4>
          <DataList values={inputs} />
        </section>

        <section>
          <h4>计算数据</h4>
          {calculated.length === 0 ? (
            <p className="empty-detail">本评审项没有单独的计算结果。</p>
          ) : (
            <dl className="data-list">
              {calculated.map(([name, value]) => (
                <div key={name}>
                  <dt>{dataLabel(name)}</dt>
                  <dd>{formatCalculatedValue(value)}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>

        <section>
          <h4>依据</h4>
          {finding.evidence.length === 0 ? (
            <p className="empty-detail">未提供依据。</p>
          ) : (
            <ul>
              {finding.evidence.map((item, index) => (
                <li key={`${item.source}-${index}`}>
                  <strong>{evidenceSourceLabels[item.source] ?? item.source}</strong>
                  {' — '}
                  {item.description}
                  {Object.keys(item.values).length > 0 && (
                    <dl className="data-list compact-data-list">
                      {Object.entries(item.values).map(([name, value]) => (
                        <div key={name}>
                          <dt>{dataLabel(name)}</dt>
                          <dd>{formatQuantity(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h4>缺失信息</h4>
          {finding.missing_information.length === 0 ? (
            <p className="empty-detail">无。</p>
          ) : (
            <ul>
              {finding.missing_information.map((item) => (
                <li key={item}>{dataLabel(item)}</li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h4>建议下一步</h4>
          {finding.recommended_action.length === 0 ? (
            <p className="empty-detail">暂无额外建议。</p>
          ) : (
            <ul>
              {finding.recommended_action.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          )}
        </section>

        <p className="finding-trace">规则编号：{finding.rule_id}</p>

        {finding.requires_engineer_confirmation && (
          <p className="confirmation">需要具备相应资质的工程师确认。</p>
        )}
      </div>
    </details>
  )
}

export default function ReviewPanel({ review }: { review: Review }) {
  const grouped = useMemo(() => {
    return review.findings.reduce<Record<string, Finding[]>>((result, finding) => {
      const category = finding.category
      result[category] = [...(result[category] ?? []), finding]
      return result
    }, {})
  }, [review])

  const summary = [
    ['通过', review.summary.pass, 'pass'],
    ['提示', review.summary.info, 'info'],
    ['警告', review.summary.warning, 'warning'],
    ['严重', review.summary.critical, 'critical'],
    ['数据不足', review.summary.insufficient_data, 'insufficient_data'],
  ] as const

  return (
    <section className="review-panel" aria-labelledby="review-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">确定性规则引擎</p>
          <h2 id="review-title">设计评审结果</h2>
        </div>
        <div className="review-actions">
          <time>{new Date(review.created_at).toLocaleString()}</time>
          <a
            className="report-link"
            href={reportUrl(review.project_id)}
            target="_blank"
            rel="noreferrer"
          >
            查看 HTML 报告
          </a>
        </div>
      </div>

      <div className="summary-grid">
        {summary.map(([label, count, key]) => (
          <article className={`summary-card summary-${key}`} key={key}>
            <span>{label}</span>
            <strong>{count}</strong>
          </article>
        ))}
      </div>

      <p className="review-disclaimer">
        “通过”仅表示对应有限规则检查通过，不代表设计安全、合规或可以量产。
      </p>

      <div className="finding-groups">
        {Object.entries(grouped).map(([category, findings]) => (
          <section className="finding-group" key={category}>
            <h3>{categoryLabels[category] ?? category.replaceAll('_', ' ')}</h3>
            {findings.map((finding) => (
              <FindingCard finding={finding} key={finding.rule_id} />
            ))}
          </section>
        ))}
      </div>
    </section>
  )
}
