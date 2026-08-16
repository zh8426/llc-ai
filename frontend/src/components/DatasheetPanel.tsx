import { useEffect, useState } from 'react'

import {
  listDatasheets,
  uploadDatasheet,
  verifyDatasheetParameter,
} from '../api'
import type { Datasheet, DatasheetParameter } from '../types'

const statusLabels: Record<Datasheet['parser_status'], string> = {
  NEEDS_HUMAN_REVIEW: '待工程师确认',
  VERIFIED: '已确认',
  NO_SUPPORTED_PARAMETERS: '未识别支持的参数',
}

const valueTypeLabels: Record<DatasheetParameter['value_type'], string> = {
  minimum: '最小值',
  typical: '典型值',
  maximum: '最大值',
  unknown: '未标注',
}

export default function DatasheetPanel() {
  const [datasheets, setDatasheets] = useState<Datasheet[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [manufacturer, setManufacturer] = useState('')
  const [partNumber, setPartNumber] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    void listDatasheets()
      .then(setDatasheets)
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : '数据手册列表加载失败。')
      })
  }, [])

  async function submit() {
    if (file === null) {
      setError('请先选择 PDF 数据手册。')
      return
    }
    setBusy(true)
    setError('')
    setNotice('正在提取 MOSFET 候选参数…')
    try {
      const datasheet = await uploadDatasheet(file, manufacturer, partNumber)
      setDatasheets((current) => [datasheet, ...current])
      setFile(null)
      setNotice('数据手册已保存，候选参数需要工程师逐项确认。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '数据手册上传失败。')
      setNotice('')
    } finally {
      setBusy(false)
    }
  }

  async function verify(documentId: string, parameterId: string) {
    setBusy(true)
    setError('')
    try {
      const updated = await verifyDatasheetParameter(documentId, parameterId)
      setDatasheets((current) =>
        current.map((datasheet) =>
          datasheet.id === updated.id ? updated : datasheet,
        ),
      )
      setNotice('参数已标记为人工确认。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '参数确认失败。')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="datasheet-panel" aria-labelledby="datasheet-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Phase 7 · MOSFET 数据手册</p>
          <h2 id="datasheet-title">数据手册候选参数</h2>
        </div>
        <span className="phase-badge">必须人工确认</span>
      </div>
      <p className="section-note datasheet-note">
        当前只提取可读 PDF 文本中的明确字段，不执行 OCR，不猜测缺失参数，也不会自动将候选值用于设计评审。
      </p>

      <div className="datasheet-upload">
        <label className="field field-wide">
          <span>PDF 数据手册</span>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            disabled={busy}
          />
          <small>{file?.name ?? '尚未选择文件'}</small>
        </label>
        <label className="field">
          <span>制造商（可选）</span>
          <input value={manufacturer} onChange={(event) => setManufacturer(event.target.value)} disabled={busy} />
        </label>
        <label className="field">
          <span>器件型号（可选）</span>
          <input value={partNumber} onChange={(event) => setPartNumber(event.target.value)} disabled={busy} />
        </label>
        <button className="button-primary" type="button" onClick={() => void submit()} disabled={busy}>
          {busy ? '处理中…' : '上传并提取'}
        </button>
      </div>

      {(error || notice) && <p className={error ? 'inline-error' : 'inline-notice'}>{error || notice}</p>}

      <div className="datasheet-list">
        {datasheets.length === 0 ? (
          <p className="empty-detail">暂无已上传的数据手册。</p>
        ) : (
          datasheets.map((datasheet) => (
            <article className="datasheet-card" key={datasheet.id}>
              <div className="datasheet-card-heading">
                <div>
                  <h3>{datasheet.part_number ?? datasheet.filename}</h3>
                  <p>{datasheet.manufacturer ?? '制造商未提供'} · {datasheet.filename}</p>
                </div>
                <span className="phase-badge">{statusLabels[datasheet.parser_status]}</span>
              </div>
              {datasheet.parameters.length === 0 ? (
                <p className="empty-detail">未识别到当前支持的 MOSFET 参数。</p>
              ) : (
                <div className="datasheet-table-wrap">
                  <table>
                    <thead>
                      <tr><th>参数</th><th>值</th><th>类型</th><th>来源</th><th>状态</th><th /></tr>
                    </thead>
                    <tbody>
                      {datasheet.parameters.map((parameter) => (
                        <tr key={parameter.id}>
                          <td>{parameter.parameter_name}</td>
                          <td>{String(parameter.value)} {parameter.unit}</td>
                          <td>{valueTypeLabels[parameter.value_type]}</td>
                          <td>第 {parameter.source_page ?? '未知'} 页</td>
                          <td>{parameter.human_verified ? '已确认' : '待确认'}</td>
                          <td>
                            {!parameter.human_verified && (
                              <button
                                className="button-secondary button-small"
                                type="button"
                                onClick={() => void verify(datasheet.id, parameter.id)}
                                disabled={busy}
                              >
                                确认
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </article>
          ))
        )}
      </div>
    </section>
  )
}
