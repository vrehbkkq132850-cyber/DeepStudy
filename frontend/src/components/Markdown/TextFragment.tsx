import React, { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { ContentFragment } from '../../types/api'
import remarkGfm from 'remark-gfm'

/**
 * Markdown 文本片段组件
 * 为代码块和公式注入唯一 ID，支持划词选择
 */
interface TextFragmentProps {
  content: string
  fragments?: ContentFragment[]
  onFragmentSelect?: (fragmentId: string, selectedText: string) => void
}

const TextFragment: React.FC<TextFragmentProps> = ({
  content,
  fragments = [],
  onFragmentSelect,
}) => {
  const [isSelected, setIsSelected] = useState(false)

  /**
   * 处理文本选择事件
   */
  const handleSelection = () => {
    const selection = window.getSelection()
    if (!selection || selection.rangeCount === 0) {
      setIsSelected(false)
      return
    }

    const selectedText = selection.toString().trim()
    if (!selectedText) {
      setIsSelected(false)
      return
    }

    setIsSelected(true)

    // 查找匹配的 fragment
    const matchedFragment = fragments.find((fragment) =>
      selectedText.includes(fragment.content) || fragment.content.includes(selectedText)
    )

    if (onFragmentSelect) {
      // 如果找到匹配的 fragment，使用其 ID
      // 如果没有找到匹配的 fragment，生成一个临时 ID
      const fragmentId = matchedFragment ? matchedFragment.id : `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
      onFragmentSelect(fragmentId, selectedText)
    }
  }

  // 监听全局鼠标点击，取消选择状态
  useEffect(() => {
    const handleGlobalClick = () => {
      const selection = window.getSelection()
      if (!selection || selection.toString().trim() === '') {
        setIsSelected(false)
      }
    }

    document.addEventListener('click', handleGlobalClick)
    return () => document.removeEventListener('click', handleGlobalClick)
  }, [])

  return (
    <div
      onMouseUp={handleSelection}
      style={{
        lineHeight: '1.6',
        fontSize: '1rem',
        position: 'relative',
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          code: ({ className, children, ...props }) => {
            const codeString = String(children).replace(/\n$/, '')
            const fragment = fragments.find((f) => f.content === codeString && f.type === 'code')
            
            return (
              <code
                id={fragment?.id}
                className={className}
                style={{
                  backgroundColor: '#f4f4f4',
                  padding: '2px 4px',
                  borderRadius: '3px',
                  cursor: fragment ? 'pointer' : 'default',
                  transition: 'background-color 0.2s',
                }}
                {...props}
              >
                {children}
              </code>
            )
          },
          pre: ({ children }) => {
            return (
              <pre
                style={{
                  backgroundColor: '#f4f4f4',
                  padding: '1rem',
                  borderRadius: '4px',
                  overflow: 'auto',
                  transition: 'background-color 0.2s',
                }}
              >
                {children}
              </pre>
            )
          },
          p: ({ children, ...props }) => {
            return (
              <p
                style={{
                  transition: 'background-color 0.2s',
                }}
                {...props}
              >
                {children}
              </p>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
      
      {/* 划词提示 */}
      {isSelected && (
        <div
          style={{
            position: 'absolute',
            top: '10px',
            right: '10px',
            padding: '4px 8px',
            backgroundColor: 'rgba(37, 99, 235, 0.1)',
            color: '#2563EB',
            borderRadius: '4px',
            fontSize: '12px',
            pointerEvents: 'none',
            transition: 'opacity 0.3s',
          }}
        >
          已选择文本，可进行追问
        </div>
      )}
    </div>
  )
}

export default TextFragment
