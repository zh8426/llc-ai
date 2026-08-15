import { useEffect, useState } from 'react'

import {
  createProject,
  getLatestReview,
  listProjects,
  runReview,
  updateProject,
} from '../api'
import {
  buildPayload,
  emptyForm,
  projectToForm,
  type ProjectForm,
} from '../projectForm'
import type { Project, Review } from '../types'

export function useProjectWorkspace() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [form, setForm] = useState<ProjectForm>(emptyForm)
  const [review, setReview] = useState<Review | null>(null)
  const [newProjectName, setNewProjectName] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('正在连接后端服务…')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void listProjects()
      .then(async (items) => {
        if (!active) return
        setProjects(items)
        if (items.length === 0) {
          setNotice('新建一个项目后即可开始设计评审。')
          return
        }
        const first = items[0]
        setSelectedProject(first)
        setForm(projectToForm(first))
        setReview(await getLatestReview(first.id))
        setNotice('项目已加载。')
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : '无法连接后端服务。')
        setNotice('请确认后端服务已在 127.0.0.1:8000 启动。')
      })
    return () => {
      active = false
    }
  }, [])

  function updateForm(field: keyof ProjectForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function openProject(project: Project) {
    setSelectedProject(project)
    setForm(projectToForm(project))
    setReview(null)
    setError('')
    setNotice('正在加载最近一次评审…')
    try {
      setReview(await getLatestReview(project.id))
      setNotice('项目已加载。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '评审加载失败。')
    }
  }

  async function handleCreateProject() {
    if (newProjectName.trim() === '') {
      setError('请输入项目名称。')
      return
    }
    setBusy(true)
    setError('')
    try {
      const project = await createProject(newProjectName.trim())
      setProjects((current) => [project, ...current])
      setNewProjectName('')
      setSelectedProject(project)
      setForm(projectToForm(project))
      setReview(null)
      setNotice('项目已创建，请填写设计参数。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '项目创建失败。')
    } finally {
      setBusy(false)
    }
  }

  async function saveProject(): Promise<Project | null> {
    if (selectedProject === null) return null
    setBusy(true)
    setError('')
    try {
      const updated = await updateProject(selectedProject.id, buildPayload(form))
      setSelectedProject(updated)
      setForm(projectToForm(updated))
      setProjects((current) =>
        current.map((project) => (project.id === updated.id ? updated : project)),
      )
      setNotice('项目参数已保存。')
      return updated
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '项目保存失败。')
      return null
    } finally {
      setBusy(false)
    }
  }

  async function saveAndRunReview() {
    const updated = await saveProject()
    if (updated === null) return
    setBusy(true)
    setError('')
    setNotice('正在执行 R001–R020…')
    try {
      setReview(await runReview(updated.id))
      setNotice('设计评审已完成。')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '评审执行失败。')
    } finally {
      setBusy(false)
    }
  }

  return {
    projects,
    selectedProject,
    form,
    review,
    newProjectName,
    busy,
    notice,
    error,
    setNewProjectName,
    updateForm,
    openProject,
    handleCreateProject,
    saveProject,
    saveAndRunReview,
  }
}
