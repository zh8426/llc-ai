import type {
  Project,
  ProjectPayload,
  Review,
  Datasheet,
  WaveformAnalysisRequest,
  ZVSAnalysis,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

type APIErrorPayload = {
  code?: unknown
  message?: unknown
  details?: unknown
  detail?: unknown
}

const errorCodeMessages: Record<string, string> = {
  PROJECT_NOT_FOUND: '项目不存在。',
  REVIEW_NOT_FOUND: '该项目尚未执行设计评审。',
  INVALID_ENGINEERING_UNIT: '工程参数单位或数值无效。',
  MISSING_REQUIRED_DATA: '缺少必要输入数据。',
  WAVEFORM_TOO_LARGE: '波形文件或分析规模超过限制。',
  WAVEFORM_SCHEMA_INVALID: '波形 CSV 或元数据不符合输入契约。',
  ZVS_INSUFFICIENT_DATA: '波形证据不足，无法完成 ZVS 分析。',
  DATABASE_CONFLICT: '历史记录缺少生成结果所需的数据。',
  INVALID_REQUEST: '请求参数无效，请检查输入。',
  RESOURCE_NOT_FOUND: '请求的资源不存在。',
  METHOD_NOT_ALLOWED: '请求方法不被允许。',
  INTERNAL_ERROR: '后端服务发生错误，请稍后重试。',
  DATASHEET_TOO_LARGE: '数据手册 PDF 超过大小限制。',
  DATASHEET_PDF_INVALID: 'PDF 无法提取可验证的文本。',
  DATASHEET_NOT_FOUND: '数据手册不存在。',
  DATASHEET_PARAMETER_NOT_FOUND: '数据手册参数不存在。',
}

const fallbackErrorCodes: Record<number, string> = {
  400: 'INVALID_REQUEST',
  404: 'RESOURCE_NOT_FOUND',
  405: 'METHOD_NOT_ALLOWED',
  409: 'DATABASE_CONFLICT',
  413: 'WAVEFORM_TOO_LARGE',
  422: 'INVALID_REQUEST',
  500: 'INTERNAL_ERROR',
}

class ApiRequestError extends Error {
  readonly status: number
  readonly code: string
  readonly apiMessage: string
  readonly details: unknown
  readonly detail: string

  constructor(status: number, code: string, message: string, details: unknown) {
    const statusMessage = {
      400: '请求内容无效，请检查输入。',
      404: '请求的项目或评审记录不存在。',
      409: '当前记录缺少生成结果所需的历史数据。',
      422: '输入数据格式或单位不正确，请检查后重试。',
      500: '后端服务发生错误，请稍后重试。',
    }[status]
    super(errorCodeMessages[code] ?? message ?? statusMessage ?? `请求失败（HTTP ${status}）。`)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = code
    this.apiMessage = message
    this.details = details
    this.detail = message
  }
}

async function createApiRequestError(response: Response): Promise<ApiRequestError> {
  const fallback = `${response.status} ${response.statusText}`
  let payload: APIErrorPayload = {}
  try {
    payload = (await response.json()) as APIErrorPayload
  } catch {
    // Keep the HTTP status when the server does not return JSON.
  }
  const code =
    typeof payload.code === 'string'
      ? payload.code
      : (fallbackErrorCodes[response.status] ?? 'INTERNAL_ERROR')
  const message =
    typeof payload.message === 'string'
      ? payload.message
      : typeof payload.detail === 'string'
        ? payload.detail
        : fallback
  return new ApiRequestError(response.status, code, message, payload.details ?? null)
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
    throw await createApiRequestError(response)
  }

  return (await response.json()) as T
}

async function requestMultipart<T>(path: string, body: FormData): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    body,
  })

  if (!response.ok) {
    throw await createApiRequestError(response)
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
      error.code === 'REVIEW_NOT_FOUND'
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

export async function listDatasheets(): Promise<Datasheet[]> {
  const result = await request<{ datasheets: Datasheet[] }>('/datasheets')
  return result.datasheets
}

export function uploadDatasheet(
  file: File,
  manufacturer: string,
  partNumber: string,
): Promise<Datasheet> {
  const body = new FormData()
  body.append('file', file)
  if (manufacturer.trim() !== '') body.append('manufacturer', manufacturer.trim())
  if (partNumber.trim() !== '') body.append('part_number', partNumber.trim())
  return requestMultipart<Datasheet>('/datasheets', body)
}

export function verifyDatasheetParameter(
  documentId: string,
  parameterId: string,
): Promise<Datasheet> {
  return request<Datasheet>(`/datasheets/${documentId}/parameters/${parameterId}`, {
    method: 'PATCH',
    body: JSON.stringify({ human_verified: true }),
  })
}
