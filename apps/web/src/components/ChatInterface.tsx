import React, { useState, useEffect, useRef } from 'react';
import './ChatInterface.css';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  model_used?: string;
  files?: Array<{ name: string; size: number; type: string }>;
  citations?: Array<{
    document_id: number;
    filename: string;
    page_or_section?: string;
    excerpt: string;
    score?: number;
  }>;
}

interface Collection {
  id: number;
  name: string;
  classification: string;
}

interface ModelItem {
  id: string;
  name: string;
  format?: string;
  quantization?: string;
  status?: string;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState<string>('Thinking...');
  const [models, setModels] = useState<ModelItem[]>([
    { id: 'auto', name: 'Auto (Smart Router)', status: 'active' },
    { id: 'llama3.2:3b', name: 'llama3.2:3b', status: 'active' },
    { id: 'phi3.5:latest', name: 'phi3.5:latest', status: 'active' },
    { id: 'qwen2.5-coder:1.5b', name: 'qwen2.5-coder:1.5b', status: 'active' },
    { id: 'deepseek-r1:1.5b', name: 'deepseek-r1:1.5b', status: 'active' },
    { id: 'llama3:latest', name: 'llama3:latest', status: 'active' },
    { id: 'gemma4:26b', name: 'gemma4:26b', status: 'active' },
  ]);
  const [selectedModel, setSelectedModel] = useState<string>('auto');

  // Attached files for current draft
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Pre-loaded / Selected Document for focused Q&A
  const [activeDocContext, setActiveDocContext] = useState<{
    id: number;
    filename: string;
    content?: string;
  } | null>(null);

  // Collections for Grounded RAG
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Check URL params for document chat navigation
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const docId = params.get('docId');
    const docName = params.get('docName');
    if (docId && docName) {
      fetch(`http://localhost:8000/v1/documents/${docId}/content`)
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          setActiveDocContext({
            id: Number(docId),
            filename: docName,
            content: data?.content || '',
          });
        })
        .catch(() => {
          setActiveDocContext({
            id: Number(docId),
            filename: docName,
          });
        });
      setInput(`Please summarize and explain the key points in ${docName}.`);
    }
  }, []);

  const checkOllamaAndModels = async () => {
    try {
      const [modelsRes, colsRes] = await Promise.all([
        fetch('http://localhost:8000/v1/models'),
        fetch('http://localhost:8000/v1/collections/'),
      ]);

      if (modelsRes.ok) {
        const modelData = await modelsRes.json();
        if (Array.isArray(modelData) && modelData.length > 0) {
          const seen = new Set<string>();
          const list: ModelItem[] = [
            { id: 'auto', name: 'Auto (Smart Router)', status: 'active' },
          ];
          for (const m of modelData) {
            const modelId = m.model_name || m.id;
            if (modelId && !seen.has(modelId)) {
              seen.add(modelId);
              list.push({
                id: modelId,
                name: modelId,
                format: m.format,
                quantization: m.quantization,
                status: m.status,
              });
            }
          }

          if (list.length > 0) {
            setModels(list);
          }
        }
      }

      if (colsRes.ok) {
        const colsData = await colsRes.json();
        setCollections(colsData);
      }
    } catch (e) {
      console.error('Failed to load metadata/status:', e);
    }
  };

  useEffect(() => {
    checkOllamaAndModels();
  }, []);

  // Load conversation history from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('chatMessages');
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse chat history:', e);
      }
    }
  }, []);

  // Persist conversation history to localStorage
  useEffect(() => {
    localStorage.setItem('chatMessages', JSON.stringify(messages));
  }, [messages]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Auto-grow textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  }, [input]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const newFiles = Array.from(e.target.files);
      setAttachedFiles((prev) => [...prev, ...newFiles]);
    }
  };

  const removeAttachedFile = (index: number) => {
    setAttachedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Drag and Drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setAttachedFiles((prev) => [...prev, ...droppedFiles]);
    }
  };

  const handleClearAll = async () => {
    try {
      await fetch('http://localhost:8000/v1/documents/clear-all', { method: 'POST' });
    } catch (e) {
      console.warn('Failed to clear documents on backend:', e);
    }
    setMessages([]);
    setAttachedFiles([]);
    setActiveDocContext(null);
    localStorage.removeItem('chatMessages');
  };

  const handleSend = async (overrideText?: string) => {
    const userText = (overrideText !== undefined ? overrideText : input).trim();
    if ((!userText && attachedFiles.length === 0) || isLoading) return;

    setIsLoading(true);
    setLoadingStatus(attachedFiles.length > 0 ? 'Reading and indexing attached document...' : 'Analyzing prompt and selecting optimal model...');
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // 1. Process files and upload to backend ingestion pipeline
    const fileMetadata = attachedFiles.map((f) => ({
      name: f.name,
      size: f.size,
      type: f.type,
    }));

    let textContext = '';
    for (const f of attachedFiles) {
      let docText = '';
      try {
        setLoadingStatus(`Extracting text from ${f.name}...`);
        const formData = new FormData();
        formData.append('file', f);
        if (selectedCollectionId) {
          formData.append('collection_id', String(selectedCollectionId));
        }

        const uploadRes = await fetch('http://localhost:8000/v1/documents/upload', {
          method: 'POST',
          body: formData,
        });

        if (uploadRes.ok) {
          const uploadData = await uploadRes.json();
          docText = uploadData.extracted_text || uploadData.preview || '';
        }
      } catch (uploadErr) {
        console.warn('Document upload warning:', uploadErr);
      }

      if (
        !docText &&
        (f.name.endsWith('.txt') ||
          f.name.endsWith('.md') ||
          f.name.endsWith('.json') ||
          f.name.endsWith('.py') ||
          f.name.endsWith('.csv') ||
          f.name.endsWith('.log') ||
          f.name.endsWith('.html') ||
          f.name.endsWith('.js') ||
          f.name.endsWith('.ts'))
      ) {
        try {
          docText = await f.text();
        } catch (readErr) {
          console.warn('Browser text read error:', readErr);
        }
      }

      if (docText) {
        textContext += `\n\n--- [Attached Document: ${f.name}] ---\n${docText}`;
      }
    }

    if (activeDocContext && !textContext) {
      if (activeDocContext.content) {
        textContext += `\n\n--- [Active Document Focus: ${activeDocContext.filename}] ---\n${activeDocContext.content}`;
      }
    }

    const promptWithContext = textContext
      ? `${userText ? userText + '\n\n' : ''}Context & Attached Documents:\n${textContext}`
      : userText;

    const userMessage: Message = {
      role: 'user',
      content: userText || `Attached ${attachedFiles.length} file(s) for analysis.`,
      files: fileMetadata.length > 0 ? fileMetadata : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setAttachedFiles([]);

    try {
      setLoadingStatus(selectedModel === 'auto' ? 'Routing to specialist offline model...' : `${selectedModel} is generating response...`);
      const messagesPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      messagesPayload.push({
        role: 'user',
        content: promptWithContext,
      });

      const res = await fetch('http://localhost:8000/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          messages: messagesPayload,
          collection_id: selectedCollectionId || undefined,
          task_mode: 'chat',
          stream: false,
        }),
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      const assistantMsg =
        data.choices?.[0]?.message?.content ||
        data.content ||
        'No response generated.';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: assistantMsg,
          model_used: data.model,
          citations: data.citations || undefined,
        },
      ]);
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error executing request: ${err.message}. Please check connection to local backend services.`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className="chat-container"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Active Document Context Banner (if pre-selected) */}
      {activeDocContext && (
        <div className="active-doc-banner">
          <span>📄 Focused Document: <strong>{activeDocContext.filename}</strong></span>
          <button
            type="button"
            className="banner-close-btn"
            onClick={() => setActiveDocContext(null)}
            title="Remove document focus"
          >
            ✕
          </button>
        </div>
      )}

      {/* Drag & drop indicator */}
      {isDragging && (
        <div className="drag-overlay">
          <div className="drag-content">
            <span className="drag-icon">📂</span>
            <h3>Drop documents here</h3>
            <p>PDFs, Word docs, code, and text will be attached and analyzed locally.</p>
          </div>
        </div>
      )}

      {/* Messages Feed */}
      <div className="messages-feed">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <h3>Air-Gapped Offline Assistant</h3>
            <p>
              Autonomous model selection active. Prompts, documents, code, mathematics, and reasoning are dynamically routed to the optimal specialized local model.
            </p>

            {/* Quick Prompt Starters */}
            <div className="quick-prompts-tray">
              <span className="quick-prompts-title">Quick Actions:</span>
              <button
                type="button"
                className="quick-prompt-chip"
                onClick={() => handleSend('What is the mandatory storage limit for audit logs in the compliance policy?')}
              >
                📄 Check Policy Compliance Limits
              </button>
              <button
                type="button"
                className="quick-prompt-chip"
                onClick={() => handleSend('Summarize the key findings in the uploaded documents.')}
              >
                📊 Summarize Uploaded Documents
              </button>
              <button
                type="button"
                className="quick-prompt-chip"
                onClick={() => handleSend('Write a python function to binary search a sorted array.')}
              >
                💻 Write Python Code
              </button>
              <button
                type="button"
                className="quick-prompt-chip"
                onClick={() => handleSend('Calculate 17 * 23 + 49 / 7. Think step by step.')}
              >
                🧠 Step-by-Step Math Reasoning
              </button>
            </div>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div key={idx} className={`message-row message-${m.role}`}>
              <div className="message-bubble">
                <div className="message-header">
                  <span className="role-label">
                    {m.role === 'user'
                      ? '👤 User'
                      : `🤖 Assistant ${m.model_used ? `(${m.model_used})` : ''}`}
                  </span>
                </div>

                {m.files && m.files.length > 0 && (
                  <div className="attached-files-chips">
                    {m.files.map((file, fIdx) => (
                      <span key={fIdx} className="file-chip">
                        📄 {file.name} ({Math.round(file.size / 1024)} KB)
                      </span>
                    ))}
                  </div>
                )}

                <div className="message-content" style={{ whiteSpace: 'pre-wrap' }}>
                  {m.content}
                </div>

                {m.citations && m.citations.length > 0 && (
                  <div className="citations-tray">
                    <div className="citations-heading">📖 Grounded Document Citations:</div>
                    <div className="citations-list">
                      {m.citations.map((cite, cIdx) => (
                        <div key={cIdx} className="citation-chip" title={cite.excerpt}>
                          <span className="cite-doc">📄 {cite.filename}</span>
                          {cite.page_or_section && (
                            <span className="cite-section">[{cite.page_or_section}]</span>
                          )}
                          <span className="cite-excerpt">{cite.excerpt}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="message-row message-assistant">
            <div className="message-bubble loading-bubble">
              <span className="dot-pulse"></span> {loadingStatus}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Prominent, High-Contrast Text Bar */}
      <div className="chat-input-container">
        {/* Attached files pills tray */}
        {attachedFiles.length > 0 && (
          <div className="attached-draft-tray">
            {attachedFiles.map((file, idx) => (
              <div key={idx} className="draft-file-pill">
                <span className="pill-name">📄 {file.name} ({Math.round(file.size / 1024)} KB)</span>
                <button
                  type="button"
                  className="pill-remove"
                  onClick={() => removeAttachedFile(idx)}
                  title="Remove file"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="chat-input-bar">
          {/* File attach button */}
          <button
            type="button"
            className="input-tool-btn"
            onClick={() => fileInputRef.current?.click()}
            title="Attach PDF, Word, Markdown, Code, or Text"
            disabled={isLoading}
          >
            📎
          </button>
          <button
            type="button"
            className="input-tool-btn"
            onClick={handleClearAll}
            title="Clear conversation & purge stored documents"
            disabled={isLoading}
          >
            🧹
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            className="hidden-file-input"
            onChange={handleFileChange}
          />

          {/* Active Model Selector */}
          <div className="input-model-badge">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="inline-model-select"
              title="Select active local model"
              disabled={isLoading}
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* Expanding input textarea */}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question, paste code, request math calculation or document analysis... (Enter to send)"
            disabled={isLoading}
            className="main-chat-textarea"
            rows={1}
          />

          {/* Send Button */}
          <button
            type="button"
            className={`send-button ${input.trim() || attachedFiles.length > 0 ? 'send-active' : ''}`}
            onClick={() => handleSend()}
            disabled={isLoading || (!input.trim() && attachedFiles.length === 0)}
            title="Send message"
          >
            {isLoading ? '...' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;