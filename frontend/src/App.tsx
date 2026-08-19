import { lazy, Suspense } from 'react'

import ProjectSidebar from './components/ProjectSidebar'
import { useProjectWorkspace } from './hooks/useProjectWorkspace'
import { useAppRoute } from './hooks/useAppRoute'

const ProjectPage = lazy(() => import('./pages/ProjectPage'))
const GainCurvePage = lazy(() => import('./pages/GainCurvePage'))
const WaveformPage = lazy(() => import('./pages/WaveformPage'))
const DatasheetsPage = lazy(() => import('./pages/DatasheetsPage'))

function App() {
  const workspace = useProjectWorkspace()
  const { route, navigate } = useAppRoute()

  return (
    <main className="app-shell">
      <ProjectSidebar
        projects={workspace.projects}
        selectedProject={workspace.selectedProject}
        newProjectName={workspace.newProjectName}
        busy={workspace.busy}
        onNewProjectNameChange={workspace.setNewProjectName}
        onCreateProject={() => void workspace.handleCreateProject()}
        onOpenProject={(project) => {
          void workspace.openProject(project)
          navigate('/')
        }}
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

        <nav className="workspace-nav" aria-label="功能页面">
          <button className={route === 'project' ? 'workspace-nav-active' : ''} onClick={() => navigate('/')} type="button">
            项目与评审
          </button>
          <button className={route === 'gain-curve' ? 'workspace-nav-active' : ''} onClick={() => navigate('/gain-curve')} type="button">
            FHA 增益曲线
          </button>
          <button className={route === 'waveform' ? 'workspace-nav-active' : ''} onClick={() => navigate('/waveform')} type="button">
            波形与 ZVS
          </button>
          <button className={route === 'datasheets' ? 'workspace-nav-active' : ''} onClick={() => navigate('/datasheets')} type="button">
            数据手册
          </button>
        </nav>

        <Suspense fallback={<section className="page-loading">正在加载功能模块…</section>}>
          {route === 'project' && (
            <ProjectPage
              selectedProject={workspace.selectedProject}
              form={workspace.form}
              busy={workspace.busy}
              review={workspace.review}
              onUpdateForm={workspace.updateForm}
              onSave={() => void workspace.saveProject()}
              onSaveAndRunReview={() => void workspace.saveAndRunReview()}
              onDelete={() => void workspace.deleteSelectedProject()}
            />
          )}
          {route === 'gain-curve' && <GainCurvePage project={workspace.selectedProject} />}
          {route === 'waveform' && <WaveformPage />}
          {route === 'datasheets' && <DatasheetsPage />}
        </Suspense>
      </div>
    </main>
  )
}

export default App
