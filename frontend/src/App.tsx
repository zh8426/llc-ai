const capabilities = [
  'FastAPI Backend health check',
  'React + TypeScript + Vite Frontend',
  'pytest 基础测试环境',
]

function App() {
  return (
    <main className="page-shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="phase-label">PHASE 0 · PROJECT SKELETON</p>
        <h1 id="page-title">LLC Engineering Assistant</h1>
        <p className="intro">
          Half-Bridge LLC 设计评审与故障排查助手的基础工程已就绪。
        </p>

        <div className="status-card">
          <span className="status-dot" aria-hidden="true" />
          <div>
            <strong>开发环境骨架可用</strong>
            <p>当前仅提供项目基础设施，尚未实现任何 LLC 工程分析。</p>
          </div>
        </div>

        <ul className="capability-list">
          {capabilities.map((capability) => (
            <li key={capability}>{capability}</li>
          ))}
        </ul>

        <p className="boundary-note">
          Engineering calculations, design rules, waveform analysis and AI features will
          follow the approved phase sequence.
        </p>
      </section>
    </main>
  )
}

export default App

