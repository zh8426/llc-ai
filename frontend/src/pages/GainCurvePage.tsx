import GainCurvePanel from '../components/GainCurvePanel'
import type { Project } from '../types'

export default function GainCurvePage({ project }: { project: Project | null }) {
  return <GainCurvePanel project={project} />
}
