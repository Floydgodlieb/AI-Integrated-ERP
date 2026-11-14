import { useState, useRef, useEffect } from 'react'
import './Chat.css'

function parseTable(data) {
  if (!Array.isArray(data) || data.length === 0 || !data[0] || typeof data[0] !== 'object') return null
  const keys = Object.keys(data[0]).filter(key => !key.startsWith('_'))
  if (keys.length === 0) return null
  return { keys, rows: data.map(row => keys.map(key => row[key])) }
}

function displayCell(value) {
  if (Array.isArray(value) && value.length === 2 && typeof value[0] === 'number') return value[1]
  if (value && typeof value === 'object') return JSON.stringify(value)
  return String(value ?? '')
}

function ToolResult({ result, model }) {
  const parsed = parseTable(result)
  if (parsed) {
    return (
      <div className="tool-result-table">
        <p>{parsed.rows.length} matching record(s)</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>{parsed.keys.map(key => <th key={key}>{key.replace(/_/g, ' ')}</th>)}</tr>
            </thead>
            <tbody>
              {parsed.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>{row.map((cell, cellIndex) => {
                  const value = displayCell(cell)
                  const isPill = ['status', 'payment_state', 'state'].includes(parsed.keys[cellIndex]) && value.length < 20
                  return <td key={cellIndex}>{isPill ? <span className={`pill ${value.toLowerCase()}`}>{value}</span> : value}</td>
                })}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  if (Array.isArray(result)) return <div className="tool-result">No matching records found.</div>
  if (result?.error) return <div className="tool-result error">I couldn't complete the request: {result.error}</div>
  if (result?.status === 'success') {
    const recordType = model === 'account.move'
      ? 'draft invoice'
      : model === 'sale.order'
        ? 'draft sales order'
        : 'draft record'
    return (
      <div className="tool-result success">
        <strong>Created {recordType}{result.created_id ? ` #${result.created_id}` : ''}.</strong>
        {result.note && <p>{result.note}</p>}
      </div>
    )
  }
  if (result?.status === 'cancelled') return <div className="tool-result">No draft was created. You declined the request.</div>
  if (result?.status === 'expired') return <div className="tool-result">Approval expired. Nothing was created.</div>
  return <div className="tool-result">Odoo completed the request.</div>
}

function parseSseBlock(block) {
  let event = 'message'
  const data = []

  for (const line of block.split('\n')) {
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator === -1 ? line : line.slice(0, separator)
    let value = separator === -1 ? '' : line.slice(separator + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'event') event = value
    if (field === 'data') data.push(value)
  }

  if (data.length === 0) return null
  return { event, data: data.join('\n') }
}

function approvalLines(info) {
  const values = info?.values || {}
  const lines = values.invoice_line_ids || values.order_line || []
  return lines.map((entry, index) => {
    const line = Array.isArray(entry) ? entry[2] : entry
    if (!line || typeof line !== 'object') return null
    return {
      key: index,
      product: line._resolved_product_id_name || line.product_name || `Product ${line.product_id ?? ''}`.trim(),
      quantity: line.quantity ?? line.product_uom_qty ?? '—',
    }
  }).filter(Boolean)
}

function errorMessage(response, body) {
  return body?.detail || body?.message || `The request failed (${response.status}).`
}

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [convId, setConvId] = useState(null)
  const [pendingConfirm, setPendingConfirm] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState('')
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
    setConfirmError('')

    const cid = convId || crypto.randomUUID().slice(0, 12)
    if (!convId) setConvId(cid)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, conversation_id: cid }),
      })

      if (!response.ok) {
        const body = await response.json().catch(() => null)
        setMessages(prev => [...prev, { role: 'assistant', content: errorMessage(response, body) }])
        return
      }

      if (!response.body) throw new Error('The chat stream was empty.')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      function handleEvent(block) {
        const parsed = parseSseBlock(block)
        if (!parsed) return
        const { event, data } = parsed

        if (event === 'token') {
          addToken(data)
        } else if (event === 'status') {
          setMessages(prev => [...prev.filter(message => message.role !== 'status'), { role: 'status', content: data }])
        } else if (event === 'tool_call') {
          try {
            const tool = JSON.parse(data)
            setMessages(prev => [...prev, {
              role: 'tool',
              model: tool.model,
              content: tool.result,
            }])
          } catch {
            setMessages(prev => [...prev, { role: 'assistant', content: 'The server returned an unreadable result.' }])
          }
        } else if (event === 'confirmation_required') {
          try {
            setPendingConfirm({ convId: cid, ...JSON.parse(data) })
            setConfirmError('')
          } catch {
            setMessages(prev => [...prev, { role: 'assistant', content: 'The approval details could not be read. Nothing was created.' }])
          }
        } else if (event === 'error') {
          setMessages(prev => [...prev, { role: 'assistant', content: data }])
        } else if (event === 'done') {
          setMessages(prev => prev.filter(message => message.role !== 'status'))
        }
      }

      function processBuffer(final = false) {
        const normalized = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
        const blocks = normalized.split('\n\n')
        const remainder = blocks.pop() || ''
        if (final && remainder.trim()) blocks.push(remainder)
        buffer = final ? '' : remainder
        for (const block of blocks) handleEvent(block)
      }

      while (true) {
        const { done, value } = await reader.read()
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
        processBuffer(done)
        if (done) break
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: error instanceof Error ? `Chat connection failed: ${error.message}` : 'Chat connection failed.',
      }])
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(approved) {
    if (!pendingConfirm || confirming) return
    setConfirming(true)
    setConfirmError('')
    try {
      const response = await fetch(`/api/confirm/${pendingConfirm.convId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved }),
      })
      if (!response.ok) {
        const body = await response.json().catch(() => null)
        setConfirmError(errorMessage(response, body))
        return
      }
      setPendingConfirm(null)
    } catch {
      setConfirmError('The approval could not reach the server. Try again.')
    } finally {
      setConfirming(false)
    }
  }

  async function handleNewChat() {
    let clearError = false
    if (convId) {
      try {
        await fetch(`/api/conversation/${convId}`, { method: 'DELETE' })
      } catch {
        clearError = true
      }
    }
    setMessages(clearError ? [{ role: 'assistant', content: 'The previous chat could not be cleared from the server.' }] : [])
    setConvId(null)
    setInput('')
    setPendingConfirm(null)
    setConfirmError('')
  }

  const reviewLines = approvalLines(pendingConfirm)
  const isInvoice = pendingConfirm?.model === 'account.move'
  const customerName = pendingConfirm?.values?._resolved_partner_id_name

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div className="header-left">
          <div className="ai-icon" aria-hidden="true">◆</div>
          <div className="header-info">
            <span className="header-model">Odoo Assistant</span>
            <span className="header-status">Local AI · Odoo</span>
          </div>
        </div>
        <button className="new-chat-btn" onClick={handleNewChat}>+ New Chat</button>
      </header>

      <div className="messages" aria-live="polite">
        {messages.length === 0 && (
          <div className="welcome">
            <p>Ask the assistant to look up Odoo records or prepare a draft.</p>
            <p className="examples">Try: “Create an invoice for Pepsi with 3 chairs.”</p>
          </div>
        )}

        {messages.map((message, index) => {
          if (message.role === 'status') return <div key={index} className="status-msg">{message.content}</div>
          if (message.role === 'tool') {
            return (
              <div key={index} className="message assistant">
                <div className="msg-label">Odoo result</div>
                <ToolResult result={message.content} model={message.model} />
              </div>
            )
          }
          return (
            <div key={index} className={`message ${message.role}`}>
              {message.role === 'assistant' && <div className="msg-label">Odoo Assistant</div>}
              <div className="bubble">{message.content}</div>
            </div>
          )
        })}

        {loading && !pendingConfirm && (
          <div className="message assistant">
            <div className="bubble typing"><span className="dot-pulse" /></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {pendingConfirm && (
        <div className="confirm-overlay">
          <section className="confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
            <div className="confirm-icon" aria-hidden="true">?</div>
            <div className="confirm-body">
              <h3 id="confirm-title">Review {isInvoice ? 'draft invoice' : 'draft sales order'}</h3>
              <p className="approval-customer">Customer: {customerName || 'Please review the customer in Odoo'}</p>
              {reviewLines.length > 0 ? (
                <ul className="approval-lines">
                  {reviewLines.map(line => <li key={line.key}>{line.product} <span>× {line.quantity}</span></li>)}
                </ul>
              ) : <p className="confirm-detail">{pendingConfirm.summary}</p>}
              {pendingConfirm.values?.invoice_date && <p className="approval-date">Invoice date: {pendingConfirm.values.invoice_date}</p>}
              <p className="approval-pricing">Odoo will apply the product price list and tax settings.</p>
              {confirmError && <p className="confirm-error" role="alert">{confirmError}</p>}
            </div>
            <div className="confirm-actions">
              <button className="confirm-btn reject" onClick={() => handleConfirm(false)} disabled={confirming}>
                {confirming ? 'Please wait…' : 'Reject'}
              </button>
              <button className="confirm-btn approve" onClick={() => handleConfirm(true)} disabled={confirming}>
                {confirming ? 'Please wait…' : 'Approve draft'}
              </button>
            </div>
          </section>
        </div>
      )}

      <form className="input-bar" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={event => setInput(event.target.value)}
          placeholder="Message the Odoo assistant…"
          disabled={loading || pendingConfirm}
          aria-label="Message the Odoo assistant"
        />
        <button type="submit" disabled={loading || !input.trim() || pendingConfirm}>Send</button>
      </form>
    </div>
  )
}
