import type {
  Project,
  ProjectPayload,
  Review,
  WaveformAnalysisRequest,
  ZVSAnalysis,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

class ApiRequestError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    const messages: Record<number, string> = {
      400: '请求内容无效，请检查输入。',
      404: '请求的项目或评审记录不存在。',
      409: '当前记录缺少生成结果所需的历史数据。',
      422: '输入数据格式或单位不正确，请检查后重试。',
      500: '后端服务发生错误，请稍后重试。',
    }
    super(messages[status] ?? `请求失败（HTTP ${status}）。`)
    this.name = 'ApiRequestError'
    this.status = status
    this.detail = detail
  }
}

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
    throw new ApiRequestError(response.status, detail)
  }

  return (await response.json()) as T
}

async function requestMultipart<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body,
  })

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail ?? detail
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new ApiRequestError(response.status, detail)
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
    if (
      error instanceof ApiRequestError &&
      error.status === 404 &&
      error.detail.includes('No review has been run')
    ) {
      return null
    }
    throw error
  }
}

export function reportUrl(projectId: string): string {
  return `${API_BASE_URL}/projects/${projectId}/report`
}

export function analyzeZVS(input: WaveformAnalysisRequest): Promise<ZVSAnalysis> {
  const body = new FormData()
  body.append('file', input.file)
  body.append('sample_rate', String(input.sampleRate))
  body.append('time_unit', input.timeUnit)
  body.append('channels', JSON.stringify(input.channels))
  body.append('test_condition', JSON.stringify(input.testCondition))
  body.append('vds_zvs_threshold', String(input.vdsZvsThreshold))
  body.append('vds_hard_switching_threshold', String(input.vdsHardSwitchingThreshold))
  if (input.gateLowThreshold !== null && input.gateHighThreshold !== null) {
    body.append('gate_low_threshold', String(input.gateLowThreshold))
    body.append('gate_high_threshold', String(input.gateHighThreshold))
  }
  return requestMultipart<ZVSAnalysis>('/waveforms/zvs', body)
}
