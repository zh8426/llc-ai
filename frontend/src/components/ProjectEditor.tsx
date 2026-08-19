import type { ProjectForm } from '../projectForm'
import QuantityField from './QuantityField'

type ProjectEditorProps = {
  form: ProjectForm
  busy: boolean
  onUpdateForm: (field: keyof ProjectForm, value: string | boolean) => void
  onSave: () => void
  onSaveAndRunReview: () => void
  onDelete: () => void
}

export default function ProjectEditor({
  form,
  busy,
  onUpdateForm,
  onSave,
  onSaveAndRunReview,
  onDelete,
}: ProjectEditorProps) {
  return (
    <section className="editor-panel" aria-labelledby="editor-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">结构化工程数据</p>
          <h2 id="editor-title">设计参数</h2>
        </div>
        <div className="editor-actions">
          <button className="button-secondary" onClick={onSave} disabled={busy} type="button">
            保存
          </button>
          <button className="button-primary" onClick={onSaveAndRunReview} disabled={busy} type="button">
            {busy ? '处理中…' : '保存并开始评审'}
          </button>
          <button className="button-danger" onClick={onDelete} disabled={busy} type="button">
            删除项目
          </button>
        </div>
      </div>

      <div className="form-section">
        <h3>基本规格</h3>
        <div className="form-grid">
          <label className="field field-wide">
            <span>项目名称</span>
            <input
              value={form.name}
              onChange={(event) => onUpdateForm('name', event.target.value)}
              disabled={busy}
            />
          </label>
          <QuantityField label="最小输入电压 Vin Min" unit="V" value={form.vinMin} onChange={(value) => onUpdateForm('vinMin', value)} disabled={busy} />
          <QuantityField label="标称输入电压 Vin Nom" unit="V" value={form.vinNom} onChange={(value) => onUpdateForm('vinNom', value)} disabled={busy} />
          <QuantityField label="最大输入电压 Vin Max" unit="V" value={form.vinMax} onChange={(value) => onUpdateForm('vinMax', value)} disabled={busy} />
          <QuantityField label="输出电压 Vout" unit="V" value={form.vout} onChange={(value) => onUpdateForm('vout', value)} disabled={busy} />
          <QuantityField label="输出功率 Pout" unit="W" value={form.pout} onChange={(value) => onUpdateForm('pout', value)} disabled={busy} />
          <QuantityField label="目标效率" unit="%" value={form.efficiencyPercent} onChange={(value) => onUpdateForm('efficiencyPercent', value)} disabled={busy} />
        </div>
      </div>

      <div className="form-section">
        <h3>谐振腔</h3>
        <div className="form-grid">
          <QuantityField label="谐振电感 Lr" unit="µH" value={form.lr} onChange={(value) => onUpdateForm('lr', value)} disabled={busy} />
          <QuantityField label="励磁电感 Lm" unit="µH" value={form.lm} onChange={(value) => onUpdateForm('lm', value)} disabled={busy} />
          <QuantityField label="谐振电容 Cr" unit="nF" value={form.cr} onChange={(value) => onUpdateForm('cr', value)} disabled={busy} />
        </div>
      </div>

      <div className="form-section">
        <h3>开关频率与变压器</h3>
        <div className="form-grid">
          <QuantityField label="最低开关频率 Fsw Min" unit="kHz" value={form.fswMin} onChange={(value) => onUpdateForm('fswMin', value)} disabled={busy} />
          <QuantityField label="标称开关频率 Fsw Nom" unit="kHz" value={form.fswNom} onChange={(value) => onUpdateForm('fswNom', value)} disabled={busy} />
          <QuantityField label="最高开关频率 Fsw Max" unit="kHz" value={form.fswMax} onChange={(value) => onUpdateForm('fswMax', value)} disabled={busy} />
          <QuantityField label="变压器匝比 n = Np / Ns" unit="ratio" value={form.transformerRatio} onChange={(value) => onUpdateForm('transformerRatio', value)} disabled={busy} />
        </div>
      </div>

      <div className="form-section">
        <h3>主开关器件与控制器</h3>
        <div className="form-grid">
          <label className="field">
            <span>制造商</span>
            <input value={form.manufacturer} onChange={(event) => onUpdateForm('manufacturer', event.target.value)} disabled={busy} />
          </label>
          <label className="field">
            <span>器件型号</span>
            <input value={form.partNumber} onChange={(event) => onUpdateForm('partNumber', event.target.value)} disabled={busy} />
          </label>
          <QuantityField label="MOSFET VDS 额定值" unit="V" value={form.vdsRating} onChange={(value) => onUpdateForm('vdsRating', value)} disabled={busy} />
          <label className="field">
            <span>控制器型号</span>
            <input value={form.controllerModel} onChange={(event) => onUpdateForm('controllerModel', event.target.value)} disabled={busy} />
          </label>
          <QuantityField label="控制器最低频率" unit="kHz" value={form.controllerFmin} onChange={(value) => onUpdateForm('controllerFmin', value)} disabled={busy} />
          <QuantityField label="控制器最高频率" unit="kHz" value={form.controllerFmax} onChange={(value) => onUpdateForm('controllerFmax', value)} disabled={busy} />
        </div>
      </div>

      <div className="form-section">
        <h3>项目评审设置</h3>
        <p className="section-note">留空表示没有项目批准的阈值；系统不会自动补充通用裕量。</p>
        <div className="form-grid">
          <QuantityField label="输出功率容差" unit="%" value={form.powerTolerancePercent} onChange={(value) => onUpdateForm('powerTolerancePercent', value)} disabled={busy} />
          <QuantityField label="实测 VDS 裕量" unit="%" value={form.vdsMarginPercent} onChange={(value) => onUpdateForm('vdsMarginPercent', value)} disabled={busy} />
        </div>
        <div className="review-request-options">
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={form.fullGainReviewRequested}
              onChange={(event) => onUpdateForm('fullGainReviewRequested', event.target.checked)}
              disabled={busy}
            />
            <span>
              <strong>启用完整 FHA 增益评审（R021–R026）</strong>
              <small>启用后重新评审时，系统会计算 FHA 工作包络、所需增益和工作点；不会自动给出安全结论。</small>
            </span>
          </label>
        </div>
      </div>
    </section>
  )
}
