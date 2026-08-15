import ProjectEditor from './components/ProjectEditor'
import ProjectSidebar from './components/ProjectSidebar'
import ReviewPanel from './components/ReviewPanel'
import WaveformPanel from './components/WaveformPanel'
import { useProjectWorkspace } from './hooks/useProjectWorkspace'

function App() {
  const workspace = useProjectWorkspace()

  return (
    <main className="app-shell">
      <ProjectSidebar
        projects={workspace.projects}
        selectedProject={workspace.selectedProject}
        newProjectName={workspace.newProjectName}
        busy={workspace.busy}
        onNewProjectNameChange={workspace.setNewProjectName}
        onCreateProject={() => void workspace.handleCreateProject()}
        onOpenProject={(project) => void workspace.openProject(project)}
      />

      <div className="workspace">
        <header className="workspace-header">
          <div>
            <p className="eyebrow">项目 → 保存 → 评审 → 查看结论</p>
            <h1>{workspace.selectedProject?.name ?? 'LLC 设计评审'}</h1>
          </div>
          <div className="status-area" aria-live="polite">
            <span
              className={workspace.error === '' ? 'status-dot' : 'status-dot status-error'}
            />
            <span>{workspace.error || workspace.notice}</span>
          </div>
        </header>

        {workspace.selectedProject === null ? (
          <section className="empty-state">
            <p className="eyebrow">LLC 设计评审</p>
            <h2>新建第一个 LLC 项目</h2>
            <p>
              使用左侧输入框创建项目，然后填写带单位的设计参数并运行确定性评审。
            </p>
          </section>
        ) : (
          <>
            <ProjectEditor
              form={workspace.form}
              busy={workspace.busy}
              onUpdateForm={workspace.updateForm}
              onSave={() => void workspace.saveProject()}
              onSaveAndRunReview={() => void workspace.saveAndRunReview()}
            />

            {workspace.review === null ? (
              <section className="review-placeholder">
                <p className="eyebrow">暂无评审结果</p>
                <h2>保存参数并运行 R001–R020</h2>
                <p>缺少的数据将明确显示为“数据不足”，不会由系统猜测。</p>
              </section>
            ) : (
              <ReviewPanel review={workspace.review} />
            )}
          </>
        )}

        <WaveformPanel />
      </div>
    </main>
  )
}

export default App
