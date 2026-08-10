import type { Project, ProjectPayload, Review } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = (await response.json()) as { detail?: string }
      detail = body.detail ?? detail
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new Error(detail)
  }

  return (await response.json()) as T
}

export async function listProjects(): Promise<Project[]> {
  const result = await request<{ projects: Project[] }>('/projects')
  return result.projects
}

export function createProject(name: string): Promise<Project> {
  return request<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function updateProject(
  projectId: string,
  payload: ProjectPayload,
): Promise<Project> {
  return request<Project>(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function runReview(projectId: string): Promise<Review> {
  return request<Review>(`/projects/${projectId}/review`, { method: 'POST' })
}

export async function getLatestReview(projectId: string): Promise<Review | null> {
  try {
    return await request<Review>(`/projects/${projectId}/review`)
  } catch (error) {
    if (error instanceof Error && error.message.includes('No review has been run')) {
      return null
    }
    throw error
  }
}

export function reportUrl(projectId: string): string {
  return `${API_BASE_URL}/projects/${projectId}/report`
}
