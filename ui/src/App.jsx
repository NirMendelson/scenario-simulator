import React, { useEffect, useMemo, useState } from 'react'
import ReactFlow, { Background, Controls, MarkerType, Handle, Position } from 'reactflow'
import 'reactflow/dist/style.css'
import dagre from 'dagre'

const primaryColor = '#58a6ff'
const nodeFontSize = 18
const nodeLineHeight = 22
const titleFontSize = 18

function toTree(json) {
  if (json?.children) {
    return { scenario: json.scenario, children: json.children }
  }
  // fallback to flat 4 outcomes (no levels)
  return { scenario: json.scenario, children: (json.selected_outcomes || []).map(o => ({ ...o, children: [] })) }
}

const nodeWidth = 360

function layout(nodes, edges, nodeHeight) {
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

function measureMaxHeight(tree) {
  const container = document.createElement('div')
  container.style.position = 'absolute'
  container.style.visibility = 'hidden'
  container.style.width = `${nodeWidth - 20}px`
  container.style.padding = '10px'
  container.style.lineHeight = `${nodeLineHeight}px`
  container.style.fontSize = `${nodeFontSize}px`
  container.style.fontFamily = 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif'
  container.style.background = '#0b0e14'
  document.body.appendChild(container)

  const samples = []
  samples.push({ title: 'Scenario', body: tree.scenario })
  // Include only outcomes for height measurement
  if (tree.children) {
    (tree.children || []).forEach((n) => {
      samples.push({ title: 'Outcome', body: n.outcome })
      ;(n.children || []).forEach((c) => {
        samples.push({ title: 'Outcome', body: c.outcome })
      })
    })
  } else {
    ;(tree.nodes || []).forEach((n) => samples.push({ title: 'Outcome', body: n.outcome }))
  }

  let max = 120
  samples.forEach((s) => {
    container.innerHTML = `<div style="margin-bottom:4px">${s.title}</div><div>${s.body}</div>`
    const h = container.offsetHeight + 20
    if (h > max) max = h
  })

  document.body.removeChild(container)
  return Math.min(Math.max(max, 120), 320)
}

function makeFlowElements(data, nodeHeight) {
  const nodes = []
  const edges = []

  const commonNodeStyle = (border) => ({ background: '#0b0e14', border, color: '#fff', width: nodeWidth, height: nodeHeight })

  nodes.push({
    id: 'root',
    data: { title: 'Scenario', body: data.scenario },
    style: { background: '#11131a', border: `1px solid ${primaryColor}`, color: '#fff', width: nodeWidth, height: nodeHeight },
    sourcePosition: 'bottom', targetPosition: 'top', position: { x: 0, y: 0 },
  })

  const edgeStyle = { stroke: '#e6eaf0' }

  // level 1
  const level1 = data.children || []
  level1.forEach((n, i) => {
    const id = `l1-${i}`
    nodes.push({
      id,
      data: { title: 'Outcome', body: n.outcome, explanation: n.explanation, profit: n.profit },
      style: commonNodeStyle(`1px solid ${primaryColor}`),
      sourcePosition: 'bottom', targetPosition: 'top', position: { x: 0, y: 0 },
    })
    edges.push({ id: `e-root-${id}`, source: 'root', target: id, type: 'straight', style: edgeStyle })
    // level 2 (leaves)
    ;(n.children || []).forEach((c, j) => {
      const cid = `l2-${i}-${j}`
      nodes.push({
        id: cid,
        data: { title: 'Outcome', body: c.outcome, explanation: c.explanation, profit: c.profit },
        style: commonNodeStyle(`1px solid ${primaryColor}`),
        sourcePosition: 'bottom', targetPosition: 'top', position: { x: 0, y: 0 },
      })
      edges.push({ id: `e-${id}-${cid}`, source: id, target: cid, type: 'straight', style: edgeStyle })
    })
  })

  const laidOut = layout(nodes, edges, nodeHeight)
  return { nodes: laidOut, edges }
}

function NodeRenderer({ data }) {
  const color = primaryColor
  return (
    <div style={{ height: '100%', padding: 10, boxSizing: 'border-box', display: 'flex', flexDirection: 'column', justifyContent: 'center', fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif' }}>
      <Handle type="target" position={Position.Top} style={{ background: color, border: 'none' }} />
      <div style={{ fontSize: titleFontSize, marginBottom: 6, color, textAlign: 'center' }}><b>{data.title}</b></div>
      <div style={{ fontSize: nodeFontSize, color: '#f2f5f8', lineHeight: `${nodeLineHeight}px`, textAlign: 'center', whiteSpace:'pre-wrap' }}>{data.body}</div>
      {/* trade idea intentionally omitted from node boxes */}
      <Handle type="source" position={Position.Bottom} style={{ background: color, border: 'none' }} />
    </div>
  )
}

export default function App() {
  const [json, setJson] = useState(null)
  const [elements, setElements] = useState({ nodes: [], edges: [] })
  const [nodeHeight, setNodeHeight] = useState(120)
  const [selected, setSelected] = useState(null)
  const [panelOpen, setPanelOpen] = useState(true)

  useEffect(() => { fetch('/api/tree').then(r => r.json()).then(setJson).catch(console.error) }, [])

  useEffect(() => {
    if (!json) return
    const tree = toTree(json)
    const h = measureMaxHeight(tree)
    setNodeHeight(h)
    setElements(makeFlowElements(tree, h))
  }, [json])

  const onNodeClick = (_, node) => {
    const d = node.data || {}
    setSelected({
      outcome: d.body,
      explanation: d.explanation,
      profitIdea: d.profit?.idea,
      profitExplanation: d.profit?.explanation,
    })
    setPanelOpen(true)
  }

  return (
    <div className="container" style={{ display: 'flex', height: '100%' }}>
      {panelOpen && (
        <div className="panel" style={{ width: 320, padding: 22, borderRight: '1px solid #2a2f3a', background: '#11131a', color: '#fff', overflow: 'auto', position:'relative', fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif' }}>
          <button
            onClick={() => setPanelOpen(false)}
            aria-label="Close panel"
            title="Close"
            style={{ position:'absolute', top: 8, right: 10, background:'transparent', border:'none', color:'#9aa3b2', fontSize:18, cursor:'pointer' }}
          >×</button>
          {!selected ? (
            <>
              <h3 style={{ marginTop:0, paddingRight:24 }}>Scenario</h3>
              <div style={{ whiteSpace:'pre-wrap' }}>{json?.scenario || ''}</div>
              <p style={{ opacity:.85 }}>Click a node to see full details.</p>
            </>
          ) : (
            <>
              <div style={{ marginTop: 8, marginBottom: 12 }}>
                <div style={{ fontSize: 18, fontWeight: 700, lineHeight: '22px', color:'#fff', whiteSpace:'pre-wrap' }}>{selected.outcome}</div>
                {selected.explanation && (
                  <div style={{ marginTop: 6, color:'#fff', lineHeight: '20px', whiteSpace:'pre-wrap' }}>{selected.explanation}</div>
                )}
              </div>
              {selected.profitIdea && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ borderTop: '1px solid #2a2f3a', margin: '10px 0' }} />
                  <div style={{ fontSize: 18, fontWeight: 700, lineHeight: '22px', color:'#fff', whiteSpace:'pre-wrap' }}>{selected.profitIdea}</div>
                  {selected.profitExplanation && (
                    <div style={{ marginTop: 6, color:'#fff', lineHeight: '20px', whiteSpace:'pre-wrap' }}>{selected.profitExplanation}</div>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      )}
      <div className="tree" style={{ flex: 1, background:'#0b0e14' }}>
        <ReactFlow
          nodes={elements.nodes.map(n => ({ ...n, type: 'default' }))}
          edges={elements.edges}
          nodeTypes={{ default: NodeRenderer }}
          fitView
          minZoom={0.05}
          maxZoom={3}
          onNodeClick={onNodeClick}
        >
          <Background gap={16} color="#2a2f3a" />
          <Controls position="bottom-right" />
        </ReactFlow>
      </div>
    </div>
  )
}
