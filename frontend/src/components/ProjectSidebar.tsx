import type { Project } from '../types'

type ProjectSidebarProps = {
  projects: Project[]
  selectedProject: Project | null
  newProjectName: string
  busy: boolean
  onNewProjectNameChange: (value: string) => void
  onCreateProject: () => void
  onOpenProject: (project: Project) => void
}

export default function ProjectSidebar({
  projects,
  selectedProject,
  newProjectName,
  busy,
  onNewProjectNameChange,
  onCreateProject,
  onOpenProject,
}: ProjectSidebarProps) {
  return (
    <aside className="project-sidebar">
      <div className="brand">
        <span>LLC</span>
        <div>
          <strong>工程评审助手</strong>
          <small>Half-Bridge LLC 设计评审</small>
        </div>
      </div>

      <form
        className="create-project"
        onSubmit={(event) => {
          event.preventDefault()
          onCreateProject()
        }}
      >
        <label htmlFor="new-project">新建项目</label>
        <div>
          <input
            id="new-project"
            value={newProjectName}
            onChange={(event) => onNewProjectNameChange(event.target.value)}
            placeholder="输入项目名称"
            disabled={busy}
          />
          <button type="submit" disabled={busy} aria-label="创建项目">
            +
          </button>
        </div>
      </form>

      <nav aria-label="项目列表">
        <p className="nav-label">项目</p>
        {projects.length === 0 && <p className="empty-list">暂无项目。</p>}
        {projects.map((project) => (
          <button
            className={project.id === selectedProject?.id ? 'project-active' : ''}
            key={project.id}
            onClick={() => onOpenProject(project)}
            type="button"
          >
            <strong>{project.name}</strong>
            <small>{project.topology}</small>
          </button>
        ))}
      </nav>
    </aside>
  )
}
