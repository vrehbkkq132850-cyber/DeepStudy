import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI, chatAPI, mindMapAPI } from '../../services/api'
import { AgentResponse, MindMapGraph } from '../../types/api'
import TextFragment from '../Markdown/TextFragment'
import KnowledgeGraph from '../MindMap/KnowledgeGraph'

/**
 * 聊天界面主组件
 * 包含对话展示、输入框、思维导图侧边栏
 */
const ChatInterface = () => {
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  
  const [messages, setMessages] = useState<AgentResponse[]>([])
  const [userMessages, setUserMessages] = useState<string[]>([])
  const [input, setInput] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [hasFirstChunk, setHasFirstChunk] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [mindMapData, setMindMapData] = useState<MindMapGraph>({ nodes: [], edges: [] })
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true)
  const [sessionId] = useState<string>(() => `session_${Date.now()}`)

  /**
   * 自动滚动到底部
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  /**
   * 发送消息（支持普通提问和划词追问）
   */
  const handleSend = async (refFragmentId?: string) => {
    if (!input.trim() || loading) return

    const query = input.trim()
    setInput('')
    setError('')
    setLoading(true)
    setHasFirstChunk(false)

    // 先记录用户消息
    setUserMessages(prev => [...prev, query])

    // 为 AI 创建一条占位消息
    const parentId = messages.length > 0 ? messages[messages.length - 1].conversation_id : null
    const aiIndex = messages.length
    setMessages(prev => [
      ...prev,
      {
        answer: '',
        fragments: [],
        knowledge_triples: [],
        suggestion: undefined,
        conversation_id: '',
        parent_id: parentId,
      },
    ])

    try {
      await chatAPI.sendMessageStream(
        {
          query,
          parent_id: parentId,
          ref_fragment_id: refFragmentId || null,
          session_id: sessionId,
        },
        (payload: { type: string; text?: string; conversation_id?: string; parent_id?: string; answer?: string }) => {
          // 处理流式增量
          if (payload.type === 'meta' && payload.conversation_id) {
            // 更新占位消息的 conversation_id
            setMessages(prev => {
              const next = [...prev]
              const target = next[aiIndex]
              if (target) {
                next[aiIndex] = {
                  ...target,
                  conversation_id: payload.conversation_id as string,
                }
              }
              return next
            })
          } else if (payload.type === 'delta' && payload.text) {
            // 收到首个增量，隐藏“思考中”
            setHasFirstChunk(true)
            setMessages(prev => {
              const next = [...prev]
              const target = next[aiIndex]
              if (target) {
                next[aiIndex] = {
                  ...target,
                  answer: (target.answer || '') + payload.text,
                }
              }
              return next
            })
          } else if (payload.type === 'full' && payload.answer) {
            // 非流式划词追问路径：一次性完整返回
            setMessages(prev => {
              const next = [...prev]
              next[aiIndex] = {
                answer: payload.answer as string,
                fragments: [],
                knowledge_triples: [],
                suggestion: undefined,
                conversation_id: payload.conversation_id as string,
                parent_id: payload.parent_id as string | null | undefined,
              }
              return next
            })
          }
        }
      )

      // 流结束后，如果拿到了 conversation_id，则刷新思维导图
      const finalMsg = (messages => messages[aiIndex])(messages)
      if (finalMsg && finalMsg.conversation_id) {
        try {
          const graphData = await mindMapAPI.getMindMap(finalMsg.conversation_id)
          setMindMapData(graphData)
        } catch (err) {
          // 思维导图加载失败不影响主流程
          console.warn('思维导图加载失败:', err)
        }
      }
    } catch (error: any) {
      console.error('发送消息失败:', error)
      setUserMessages(prev => prev.slice(0, -1))

      if (error?.response?.status === 401) {
        authAPI.logout()
        navigate('/login')
      } else if (error?.response?.status === 404) {
        setError('聊天功能暂时不可用，请稍后再试')
      } else {
        setError('发送消息失败，请稍后再试')
      }
    } finally {
      setLoading(false)
    }
  }

  /**
   * 处理片段选择（划词追问）
   */
  const handleFragmentSelect = (fragmentId: string) => {
    const query = prompt('请输入你的问题:')
    if (query && messages.length > 0) {
      setInput(query)
      setTimeout(() => {
        handleSend(fragmentId)
      }, 0)
    }
  }

  /**
   * 处理键盘事件
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  /**
   * 登出
   */
  const handleLogout = () => {
    authAPI.logout()
    navigate('/login')
  }

  // 样式常量
  const containerStyle: React.CSSProperties = {
    position: 'relative',
    display: 'flex',
    height: '100vh',
    backgroundColor: 'transparent',
  }

  const backgroundStyle: React.CSSProperties = {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    backgroundImage: 'url(/bg.jpg)',
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    backgroundRepeat: 'no-repeat',
    backgroundAttachment: 'fixed',
    filter: 'blur(10px)',
    opacity: 0.6,
    zIndex: -1,
  }

  const mainAreaStyle: React.CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    margin: '16px',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    overflow: 'hidden',
    position: 'relative',
    zIndex: 1,
  }

  const headerStyle: React.CSSProperties = {
    padding: '16px 24px',
    borderBottom: '1px solid #E5E7EB',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: 'white',
  }

  const messagesAreaStyle: React.CSSProperties = {
    flex: 1,
    overflowY: 'auto',
    padding: '24px',
    backgroundColor: 'rgba(249, 250, 251, 0.6)',
  }

  const userMessageStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'flex-end',
    marginBottom: '16px',
  }

  const userBubbleStyle: React.CSSProperties = {
    maxWidth: '70%',
    padding: '12px 16px',
    backgroundColor: '#2563EB',
    color: 'white',
    borderRadius: '12px 12px 4px 12px',
    fontSize: '16px',
    lineHeight: '1.5',
    wordWrap: 'break-word',
  }

  const aiMessageStyle: React.CSSProperties = {
    display: 'flex',
    justifyContent: 'flex-start',
    marginBottom: '24px',
  }

  const aiCardStyle: React.CSSProperties = {
    maxWidth: '85%',
    padding: '20px',
    backgroundColor: 'white',
    borderRadius: '8px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    border: '1px solid #E5E7EB',
  }

  const inputAreaStyle: React.CSSProperties = {
    padding: '16px 24px',
    borderTop: '1px solid #E5E7EB',
    backgroundColor: 'white',
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-end',
  }

  const textareaStyle: React.CSSProperties = {
    flex: 1,
    padding: '12px 16px',
    border: '1px solid #D1D5DB',
    borderRadius: '8px',
    fontSize: '16px',
    fontFamily: 'inherit',
    resize: 'none',
    minHeight: '44px',
    maxHeight: '120px',
    outline: 'none',
    transition: 'border-color 0.2s',
  }

  const buttonStyle: React.CSSProperties = {
    padding: '12px 24px',
    backgroundColor: '#2563EB',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: 500,
    cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
    opacity: loading || !input.trim() ? 0.6 : 1,
    transition: 'background-color 0.2s',
  }

  const sidebarStyle: React.CSSProperties = {
    width: sidebarOpen ? '400px' : '0',
    borderLeft: sidebarOpen ? '1px solid #E5E7EB' : 'none',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    transition: 'width 0.3s',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    margin: '16px 16px 16px 0',
    borderRadius: '8px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
    position: 'relative',
    zIndex: 1,
  }

  const errorStyle: React.CSSProperties = {
    padding: '12px 16px',
    marginBottom: '16px',
    backgroundColor: '#FEE2E2',
    color: '#EF4444',
    borderRadius: '8px',
    fontSize: '14px',
  }

  return (
    <div style={containerStyle}>
      {/* 背景层（模糊） */}
      <div style={backgroundStyle} />

      {/* 主聊天区域 */}
      <div style={mainAreaStyle}>
        {/* 头部 */}
        <div style={headerStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h1 style={{ fontSize: '20px', fontWeight: 600, color: '#111827', margin: 0 }}>
              DeepStudy
            </h1>
            <span style={{ fontSize: '14px', color: '#6B7280' }}>
              递归学习助手
            </span>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{
                padding: '8px 16px',
                border: '1px solid #D1D5DB',
                borderRadius: '6px',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '14px',
                color: '#111827',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#F3F4F6'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'white'
              }}
            >
              {sidebarOpen ? '隐藏图谱' : '显示图谱'}
            </button>
            <button
              onClick={handleLogout}
              style={{
                padding: '8px 16px',
                border: '1px solid #D1D5DB',
                borderRadius: '6px',
                backgroundColor: 'white',
                cursor: 'pointer',
                fontSize: '14px',
                color: '#111827',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#F3F4F6'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'white'
              }}
            >
              登出
            </button>
          </div>
        </div>

        {/* 消息列表 */}
        <div style={messagesAreaStyle}>
          {messages.length === 0 && (
            <div style={{
              textAlign: 'center',
              color: '#6B7280',
              marginTop: '100px',
            }}>
              <h2 style={{ fontSize: '24px', marginBottom: '8px', color: '#111827' }}>
                开始你的学习之旅
              </h2>
              <p>输入你的问题，AI 助手会帮助你深入理解</p>
            </div>
          )}

          {messages.map((msg, index) => (
            <div key={index}>
              {/* 用户消息 */}
              {userMessages[index] && (
                <div style={userMessageStyle}>
                  <div style={userBubbleStyle}>
                    {userMessages[index]}
                  </div>
                </div>
              )}

              {/* AI 回答 */}
              <div style={aiMessageStyle}>
                <div style={aiCardStyle}>
                  {msg.answer
                    ? (
                      <TextFragment
                        content={msg.answer}
                        fragments={msg.fragments || []}
                        onFragmentSelect={handleFragmentSelect}
                      />
                    )
                    : loading && !hasFirstChunk && index === messages.length - 1
                      ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6B7280' }}>
                          <div style={{
                            width: '16px',
                            height: '16px',
                            border: '2px solid #E5E7EB',
                            borderTopColor: '#2563EB',
                            borderRadius: '50%',
                            animation: 'spin 1s linear infinite',
                          }}
                          />
                          <span>思考中...</span>
                        </div>
                        )
                      : null}
                </div>
              </div>
            </div>
          ))}

          {/* 错误提示 */}
          {error && (
            <div style={errorStyle} role="alert">
              {error}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div style={inputAreaStyle}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              setError('')
            }}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
            disabled={loading}
            style={{
              ...textareaStyle,
              ...(loading ? { backgroundColor: '#F3F4F6', cursor: 'not-allowed' } : {}),
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#2563EB'
              e.target.style.boxShadow = '0 0 0 3px rgba(37, 99, 235, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#D1D5DB'
              e.target.style.boxShadow = 'none'
            }}
            rows={1}
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            style={buttonStyle}
            onMouseEnter={(e) => {
              if (!loading && input.trim()) {
                e.currentTarget.style.backgroundColor = '#1D4ED8'
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#2563EB'
            }}
          >
            {loading ? '发送中...' : '发送'}
          </button>
        </div>
      </div>

      {/* 思维导图侧边栏 */}
      {sidebarOpen && (
        <div style={sidebarStyle}>
          <div style={{
            padding: '16px',
            borderBottom: '1px solid #E5E7EB',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <h3 style={{ fontSize: '18px', fontWeight: 600, margin: 0, color: '#111827' }}>
              知识图谱
            </h3>
            <button
              onClick={() => setSidebarOpen(false)}
              style={{
                padding: '4px 8px',
                border: 'none',
                backgroundColor: 'transparent',
                cursor: 'pointer',
                fontSize: '20px',
                color: '#6B7280',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#111827'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#6B7280'
              }}
            >
              ×
            </button>
          </div>
          <div style={{ flex: 1, padding: '16px' }}>
            <KnowledgeGraph data={mindMapData} />
          </div>
        </div>
      )}
    </div>
  )
}

export default ChatInterface
