import React, { useEffect, useMemo, useRef, useState } from 'react'
import Tree from 'react-d3-tree'

const circleFill = (expert) => {
  switch (expert) {
    case 'econ': return '#2ecc71' // green
    case 'tech': return '#3498db' // blue
    case 'geo': return '#e67e22'  // orange
    case 'social': return '#f1c40f' // yellow
    case 'scenario': return '#95a5a6' // grey
    default: return '#7f8c8d'
  }
}

function toD3(treeJson) {
  const root = {
    name: '',
    attributes: { expert: 'scenario', outcome: treeJson.scenario, explanation: '', level: 0, idx: 0 },
    children: (treeJson.children || []).map((level1, i) => ({
      name: '',
      attributes: { outcome: level1.outcome, explanation: level1.explanation, expert: level1.expert, level: 1, idx: i },
      children: (level1.children || []).map((ch, j) => ({
        name: '',
        attributes: {
          outcome: ch.outcome,
          explanation: ch.explanation,
          expert: ch.expert,
          profitIdea: ch.profit?.idea,
          profitExplanation: ch.profit?.explanation,
          level: 2,
          idx: j
        }
      }))
    }))
  }
  return root
}

export default function App() {
  const [data, setData] = useState(null)
  const [selected, setSelected] = useState(null)
  const containerRef = useRef(null)
  const [translate, setTranslate] = useState({ x: 520, y: 140 })

  useEffect(() => {
    fetch('/api/tree').then(r => r.json()).then(setData).catch(console.error)
  }, [])

  const d3Data = useMemo(() => data ? toD3(data) : null, [data])

  useEffect(() => {
    if (!containerRef.current) return
    const { width } = containerRef.current.getBoundingClientRect()
    setTranslate({ x: Math.max(320, width * 0.28), y: 160 })
  }, [containerRef.current])

  if (!data) return <div className="container"><div className="panel">Loading...</div></div>

  const handleNodeClick = (nodeDatum) => {
    const a = nodeDatum?.attributes || {}
    setSelected({
      expert: a.expert,
      outcome: a.outcome || data.scenario,
      explanation: a.explanation,
      profitIdea: a.profitIdea,
      profitExplanation: a.profitExplanation
    })
  }

  const labelBox = (level) => {
    if (level === 0) return { width: 520, height: 48 }
    if (level === 1) return { width: 360, height: 48 }
    return { width: 320, height: 48 }
  }

  // Compute label position relative to the node
  const labelPos = (level, idx, width, height) => {
    if (level === 0) {
      // root: centered above
      return { x: -width / 2, y: -(height), align: 'center' }
    }
    if (level === 1) {
      // first level: 0,1 to left; 2,3 to right
      const left = idx % 4 < 2
      return left
        ? { x: -(width + 16), y: -40, align: 'right' }
        : { x: 16, y: -40, align: 'left' }
    }
    // leaves: below; special alignment by relative order under the parent (0..3)
    if (idx === 0) {
      // leftmost: below and to the left
      return { x: -(width + 12), y: 22, align: 'right' }
    }
    if (idx === 3) {
      // rightmost: below and to the right
      return { x: 12, y: 22, align: 'left' }
    }
    // middle two: centered below
    return { x: -width / 2, y: 22, align: 'center' }
  }

  return (
    <div className="container">
      <div className="panel">
        {!selected ? (
          <>
            <h3 style={{ marginTop:0 }}>Scenario</h3>
            <div className="mono" style={{ whiteSpace:'pre-wrap' }}>{data.scenario}</div>
            <p style={{ opacity:.85 }}>Click a node to see full details.</p>
          </>
        ) : (
          <>
            <h3 style={{ marginTop:0 }}>Details</h3>
            <h4>Outcome</h4>
            <div className="mono" style={{ whiteSpace:'pre-wrap' }}>{selected.outcome}</div>
            {selected.explanation && <>
              <h4>Explanation</h4>
              <div className="mono" style={{ whiteSpace:'pre-wrap' }}>{selected.explanation}</div>
            </>}
            {selected.profitIdea && <>
              <h4>Profit idea</h4>
              <div className="mono">{selected.profitIdea}</div>
              {selected.profitExplanation && <div className="mono" style={{ whiteSpace:'pre-wrap', opacity:.95 }}>{selected.profitExplanation}</div>}
            </>}
          </>
        )}
      </div>
      <div className="tree" ref={containerRef}>
        <Tree
          data={d3Data}
          orientation="vertical"
          separation={{ siblings: 1.8, nonSiblings: 2.2 }}
          translate={translate}
          zoomable
          scaleExtent={{ min: 0.1, max: 8 }}
          pathFunc="straight"
          onNodeClick={handleNodeClick}
          styles={{
            links: { stroke: '#ffffff' },
            nodes: {
              node: { circle: { stroke: '#ffffff', strokeWidth: 1.2 } },
              leafNode: { circle: { stroke: '#ffffff', strokeWidth: 1.0 } }
            }
          }}
          renderCustomNodeElement={({ nodeDatum }) => {
            const a = nodeDatum.attributes || {}
            const fill = circleFill(a.expert)
            const text = a.outcome
            const { width, height } = labelBox(a.level)
            const { x, y, align } = labelPos(a.level, a.idx, width, height)
            return (
              <g onClick={() => handleNodeClick(nodeDatum)} style={{ cursor: 'pointer' }}>
                <circle r={12} fill={fill} />
                {text && (
                  <foreignObject x={x} y={y} width={width} height={height}>
                    <div style={{ color:'#f2f5f8', fontSize:12, lineHeight:'16px', textAlign: align, overflow:'hidden', display:'-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical' }}>
                      {text}
                    </div>
                  </foreignObject>
                )}
              </g>
            )
          }}
        />
      </div>
    </div>
  )
}
