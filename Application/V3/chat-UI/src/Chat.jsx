import { useState, useRef, useEffect } from 'react'
import './Chat.css'

function tryParseTable(data) {
  let arr
  try { arr = JSON.parse(data) } catch { return null }
  if (!Array.isArray(arr) || arr.length === 0) return null
  const keys = Object.keys(arr[0]).filter(k => !k.startsWith('_'))
  if (keys.length === 0) return null
  return { keys, rows: arr.map(r => keys.map(k => r[k])) }
}

function DataTable({ data }) {
  const parsed = tryParseTable(data)
  if (!parsed) return <div className="bubble">Executed</div>
  return (
    <div style={{ maxWidth: '92%', overflowX: 'auto' }}>
      <table className="data-table">
        <thead>
          <tr>{parsed.keys.map(k => <th key={k}>{k.replace(/_/g, ' ')}</th>)}</tr>
        </thead>
        <tbody>
          {parsed.rows.map((row, i) => (
            <tr key={i}>{row.map((cell, j) => {
              const str = String(cell ?? '')
              const isPill = ['status', 'payment', 'state'].includes(parsed.keys[j]) && str.length < 20
              return <td key={j}>{isPill ? <span className={`pill ${str.toLowerCase()}`}>{str}</span> : str}</td>
            })}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [convId, setConvId] = useState(null)
  const [pendingConfirm, setPendingConfirm] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function addToken(content) {
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (last?.role === 'assistant') {
        const updated = [...prev]
        updated[updated.length - 1] = { ...last, content: last.content + content }
        return updated
      }
      return [...prev, { role: 'assistant', content }]
    })
  }

  async function handleSend(e) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    setPendingConfirm(null)

    const cid = convId || crypto.randomUUID().slice(0, 12)
    if (!convId) setConvId(cid)

    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, conversation_id: cid })
    })

    if (!resp.ok) {
      const errText = await resp.text().catch(() => 'Unknown error')
      setMessages(prev => [...prev, { role: 'assistant', content: `Error ${resp.status}: ${errText}` }])
      setLoading(false)
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        if (line.startsWith('event: ')) {
          const eventType = line.slice(7).trim()
          const next = lines[i + 1]
          if (next?.startsWith('data: ')) {
            const data = next.slice(6)
            if (eventType === 'token') {
              addToken(data)
            } else if (eventType === 'status') {
              setMessages(prev => [...prev, { role: 'status', content: data }])
            } else if (eventType === 'tool_call') {
              try {
                const tc = JSON.parse(data)
                setMessages(prev => [...prev, { role: 'tool', content: JSON.stringify(tc.result) }])
              } catch { }
            } else if (eventType === 'confirmation_required') {
              try {
                const info = JSON.parse(data)
                setPendingConfirm({ convId: cid, ...info })
              } catch { }
            } else if (eventType === 'done') {
              setLoading(false)
            }
          }
        }
      }
    }
    setLoading(false)
  }

  async function handleConfirm(approved) {
    const info = pendingConfirm
    setPendingConfirm(null)
    setMessages(prev => [...prev, {
      role: 'tool',
      content: approved ? '{"approved":true}' : '{"approved":false}'
    }])
    await fetch(`/api/confirm/${info.convId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved })
    })
  }

  async function handleNewChat() {
    if (convId) {
      await fetch(`/api/conversation/${convId}`, { method: 'DELETE' })
    }
    setMessages([])
    setConvId(null)
    setInput('')
    setPendingConfirm(null)
  }

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div className="header-left">
          <div className="ai-icon">◆</div>
          <div className="header-info">
            <span className="header-model">Your Model</span>
            <span className="header-status">Connected to YourERP (Odoo)</span>
          </div>
        </div>
        <button className="new-chat-btn" onClick={handleNewChat}>+ New Chat</button>
      </header>

      <div className="messages">
        {messages.length === 0 && (
          <div className="welcome">
            <p>Ask me anything about your Odoo ERP data.</p>
            <p className="examples">
              Try: "Show me all customers" or "Create a sales order for Pepsi with 10 units of Product A"
            </p>
          </div>
        )}

        {messages.map((msg, i) => {
          if (msg.role === 'status') {
            return <div key={i} className="status-msg">{msg.content}</div>
          }
          if (msg.role === 'tool') {
            return (
              <div key={i} className="message assistant">
                <div className="msg-label">YourAIModel · YourERP</div>
                <DataTable data={msg.content} />
              </div>
            )
          }
          return (
            <div key={i} className={`message ${msg.role}`}>
              {msg.role === 'assistant' && <div className="msg-label">YourAIModel · YourERP</div>}
              <div className="bubble">{msg.content}</div>
            </div>
          )
        })}

        {loading && !pendingConfirm && (
          <div className="message assistant">
            <div className="bubble typing">
              <span className="dot-pulse"></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {pendingConfirm && (
        <div className="confirm-overlay">
          <div className="confirm-dialog">
            <div className="confirm-icon">✓</div>
            <div className="confirm-body">
              <h3>Confirm Create</h3>
              <p className="confirm-detail">{pendingConfirm.summary}</p>
            </div>
            <div className="confirm-actions">
              <button className="confirm-btn reject" onClick={() => handleConfirm(false)}>✕</button>
              <button className="confirm-btn approve" onClick={() => handleConfirm(true)}>✓</button>
            </div>
          </div>
        </div>
      )}

      <form className="input-bar" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Message the AI agent..."
          disabled={loading || pendingConfirm}
        />
        <button type="submit" disabled={loading || !input.trim() || pendingConfirm}>Send</button>
      </form>
    </div>
  )
}
