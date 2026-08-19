import ProjectEditor from '../components/ProjectEditor'
import ReviewPanel from '../components/ReviewPanel'
import type { ProjectForm } from '../projectForm'
import type { Project, Review } from '../types'

type ProjectPageProps = {
  selectedProject: Project | null
  form: ProjectForm
  busy: boolean
  review: Review | null
  onUpdateForm: (field: keyof ProjectForm, value: string | boolean) => void
  onSave: () => void
  onSaveAndRunReview: () => void
  onDelete: () => void
}

export default function ProjectPage({
  selectedProject,
  form,
  busy,
  review,
  onUpdateForm,
  onSave,
  onSaveAndRunReview,
  onDelete,
}: ProjectPageProps) {
  if (selectedProject === null) {
    return (
      <section className="empty-state">
        <p className="eyebrow">LLC 设计评审</p>
        <h2>新建第一个 LLC 项目</h2>
        <p>使用左侧输入框创建项目，然后填写带单位的设计参数并运行确定性评审。</p>
      </section>
    )
  }

  return (
    <>
      <ProjectEditor
        form={form}
        busy={busy}
        onUpdateForm={onUpdateForm}
        onSave={onSave}
        onSaveAndRunReview={onSaveAndRunReview}
        onDelete={onDelete}
      />
      {review === null ? (
        <section className="review-placeholder">
          <p className="eyebrow">暂无评审结果</p>
          <h2>保存参数并运行 R001–R026</h2>
          <p>缺少的数据将明确显示为“数据不足”，不会由系统猜测。</p>
        </section>
      ) : (
        <ReviewPanel review={review} />
      )}
    </>
  )
}
