import React, { useEffect, useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, MarkerType, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import dagre from 'dagre'

const expertColor = (e) => ({
  geo: '#e67e22',
  econ: '#2ecc71',
  tech: '#3498db',
  social: '#f1c40f',
  scenario: '#95a5a6',
}[e] || '#7f8c8d')

function toTree(json) {
  return {
    scenario: json.scenario,
    level1: (json.children || []).map((n, i) => ({ ...n, idx: i })),
  }
}

const nodeWidth = 320
const nodeHeight = 60

function layout(nodes, edges) {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 120 })
  g.setDefaultEdgeLabel(() => ({}))
  nodes.forEach((n) => g.setNode(n.id, { width: nodeWidth, height: nodeHeight }))
  edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)
  return nodes.map((n) => {
    const p = g.node(n.id)
    return { ...n, position: { x: p.x - nodeWidth / 2, y: p.y - nodeHeight / 2 } }
  })
}

function makeFlowElements(data) {
  const nodes = []
  const edges = []

  // root
  nodes.push({
    id: 'root',
    data: { expert: 'scenario', title: 'Scenario', body: data.scenario },
    style: { background: '#11131a', border: '1px solid #9aa1a9', color: '#fff', width: nodeWidth },
    sourcePosition: 'bottom', targetPosition: 'top', position: { x: 0, y: 0 },
  })

  const arrow = { type: MarkerType.ArrowClosed, color: '#e6eaf0' }
  const edgeStyle = { stroke: '#e6eaf0' }

  data.level1.forEach((n, i) => {
    const id = `l1-${i}`
    nodes.push({
      id,
      data: { expert: n.expert, title: `[${n.expert}]`, body: n.outcome, explanation: n.explanation },
      style: { background: '#0b0e14', border: `1px solid ${expertColor(n.expert)}`, color: '#fff', width: nodeWidth },
      sourcePosition: 'bottom', targetPosition: 'top', position: { x: 0, y: 0 },
    })
    edges.push({ id: `e-root-${id}`, source: 'root', target: id, type: 'smoothstep', markerEnd: arrow, style: edgeStyle })

    ;(n.children || []).forEach((c, j) => {
      const cid = `l2-${i}-${j}`
      nodes.push({
        id: cid,
        data: { expert: c.expert, title: `[${c.expert}]`, body: c.outcome, explanation: c.explanation, profit: c.profit },
        style: { background: '#0b0e14', border: `1px solid ${expertColor(c.expert)}`, color: '#fff', width: nodeWidth },
        sourcePosition: 'bottom', targetPosition: 'top', position: { x: 0, y: 0 },
      })
      edges.push({ id: `e-${id}-${cid}`, source: id, target: cid, type: 'smoothstep', markerEnd: arrow, style: edgeStyle })
    })
  })

  const laidOut = layout(nodes, edges)
  return { nodes: laidOut, edges }
}

function NodeRenderer({ data }) {
  const color = expertColor(data.expert)
  return (
    <div style={{ padding: 10 }}>
      <Handle type="target" position={Position.Top} style={{ background: color, border: 'none' }} />
      <div style={{ fontSize: 12, marginBottom: 4, color }}><b>{data.title}</b></div>
      <div style={{ fontSize: 12, color: '#f2f5f8', lineHeight: '16px' }}>{data.body}</div>
      <Handle type="source" position={Position.Bottom} style={{ background: color, border: 'none' }} />
    </div>
  )
}

export default function App() {
  const [json, setJson] = useState(null)
  const [elements, setElements] = useState({ nodes: [], edges: [] })
  const [selected, setSelected] = useState(null)

  useEffect(() => { fetch('/api/tree').then(r => r.json()).then(setJson).catch(console.error) }, [])

  useEffect(() => {
    if (!json) return
    const tree = toTree(json)
    setElements(makeFlowElements(tree))
  }, [json])

  const onNodeClick = (_, node) => {
    const d = node.data || {}
    setSelected({
      expert: d.expert,
      outcome: d.body,
      explanation: d.explanation,
      profitIdea: d.profit?.idea,
      profitExplanation: d.profit?.explanation,
    })
  }

  return (
    <div className="container" style={{ display: 'flex', height: '100%' }}>
      <div className="panel" style={{ width: 420, padding: 16, borderRight: '1px solid #2a2f3a', background: '#11131a', color: '#fff', overflow: 'auto' }}>
        {!selected ? (
          <>
            <h3 style={{ marginTop:0 }}>Scenario</h3>
            <div style={{ fontFamily:'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace', whiteSpace:'pre-wrap' }}>{json?.scenario || ''}</div>
            <p style={{ opacity:.85 }}>Click a node to see full details.</p>
          </>
        ) : (
          <>
            <h3 style={{ marginTop:0 }}>Details</h3>
            <div style={{ marginBottom:8, color: expertColor(selected.expert) }}><b>[{selected.expert}]</b></div>
            <h4>Outcome</h4>
            <div style={{ whiteSpace:'pre-wrap' }}>{selected.outcome}</div>
            {selected.explanation && <>
              <h4>Explanation</h4>
              <div style={{ whiteSpace:'pre-wrap' }}>{selected.explanation}</div>
            </>}
            {selected.profitIdea && <>
              <h4>Profit idea</h4>
              <div>{selected.profitIdea}</div>
              {selected.profitExplanation && <div style={{ opacity:.95 }}>{selected.profitExplanation}</div>}
            </>}
          </>
        )}
      </div>
      <div className="tree" style={{ flex: 1, background:'#0b0e14' }}>
        <ReactFlow
          nodes={elements.nodes.map(n => ({ ...n, type: 'default' }))}
          edges={elements.edges}
          nodeTypes={{ default: NodeRenderer }}
          fitView
          onNodeClick={onNodeClick}
        >
          <Background gap={16} color="#2a2f3a" />
          <Controls position="bottom-right" />
        </ReactFlow>
      </div>
    </div>
  )
}
