import { useCallback, useMemo, useEffect } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { MindMapGraph } from '../../types/api'

/**
 * 知识图谱组件
 * 使用 ReactFlow 渲染思维导图
 */
interface KnowledgeGraphProps {
  data: MindMapGraph
  onNodeClick?: (nodeId: string) => void
}

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({ 
  data, 
  onNodeClick
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(data.nodes as Node[])
  const [edges, setEdges, onEdgesChange] = useEdgesState(data.edges as Edge[])
  const { fitView } = useReactFlow()

  /**
   * 当数据变化时，更新节点和边
   */
  useEffect(() => {
    if (data) {
      setNodes(data.nodes as Node[])
      setEdges(data.edges as Edge[])
    }
  }, [data, setNodes, setEdges])

  /**
   * 当数据变化时，重新拟合视图
   */
  useEffect(() => {
    if (data.nodes.length > 0) {
      setTimeout(() => {
        fitView({ padding: 0.2 })
      }, 100)
    }
  }, [data, fitView])

  /**
   * 处理节点连接
   */
  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  /**
   * 处理节点点击
   */
  const handleNodeClick = useCallback(
    (event: React.MouseEvent, node: Node) => {
      if (onNodeClick) {
        onNodeClick(node.id)
      }
    },
    [onNodeClick]
  )

  /**
   * 处理节点鼠标悬停
   */
  const handleNodeMouseEnter = useCallback(
    (event: React.MouseEvent, node: Node) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === node.id
            ? {
                ...n,
                style: {
                  ...n.style,
                  boxShadow: '0 0 10px rgba(0, 123, 255, 0.5)',
                  transform: 'scale(1.05)',
                  transition: 'all 0.3s ease',
                },
              }
            : n
        )
      )
    },
    [setNodes]
  )

  /**
   * 处理节点鼠标离开
   */
  const handleNodeMouseLeave = useCallback(
    (event: React.MouseEvent, node: Node) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === node.id
            ? {
                ...n,
                style: {
                  ...n.style,
                  boxShadow: 'none',
                  transform: 'scale(1)',
                  transition: 'all 0.3s ease',
                },
              }
            : n
        )
      )
    },
    [setNodes]
  )

  /**
   * 节点样式
   */
  const nodeStyles = useMemo(
    () => ({
      default: {
        background: '#fff',
        border: '2px solid #007bff',
        borderRadius: '8px',
        padding: '10px',
        minWidth: '150px',
        fontSize: '14px',
        fontWeight: '500',
      },
      center: {
        background: '#007bff',
        color: 'white',
        border: '2px solid #0056b3',
        borderRadius: '8px',
        padding: '12px',
        minWidth: '200px',
        fontSize: '16px',
        fontWeight: 'bold',
      },
      subject: {
        background: '#fff',
        border: '2px solid #28a745',
        borderRadius: '8px',
        padding: '10px',
        minWidth: '150px',
        fontSize: '14px',
        fontWeight: '500',
      },
      object: {
        background: '#fff',
        border: '2px solid #ffc107',
        borderRadius: '8px',
        padding: '10px',
        minWidth: '150px',
        fontSize: '14px',
        fontWeight: '500',
      },
    }),
    []
  )

  return (
    <div style={{ width: '100%', height: '600px', position: 'relative' }}>
      {/* 知识图谱标题 */}
      <div style={{
        position: 'absolute',
        top: '10px',
        left: '20px',
        zIndex: 1000,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        padding: '8px 16px',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        fontSize: '16px',
        fontWeight: '600',
        color: '#333',
      }}>
        知识图谱
      </div>

      {/* 节点数量统计 */}
      <div style={{
        position: 'absolute',
        top: '10px',
        right: '20px',
        zIndex: 1000,
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        padding: '6px 12px',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        fontSize: '12px',
        color: '#666',
      }}>
        节点: {nodes.length} | 边: {edges.length}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onNodeMouseEnter={handleNodeMouseEnter}
        onNodeMouseLeave={handleNodeMouseLeave}
        fitView
        attributionPosition="bottom-right"
      >
        <Background gap={12} size={1} />
        <Controls 
          showInteractive={false}
          showFitView={true}
          showZoom={true}
        />
        <MiniMap 
          nodeColor={(n) => {
            if (n.data.type === 'center') return '#007bff'
            if (n.data.type === 'subject') return '#28a745'
            if (n.data.type === 'object') return '#ffc107'
            return '#007bff'
          }}
        />
      </ReactFlow>
    </div>
  )
}

export default KnowledgeGraph
