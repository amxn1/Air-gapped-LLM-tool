import React, { useState, useEffect, useRef } from 'react';
import './ChatInterface.css';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
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
  const [models, setModels] = useState<ModelItem[]>([
    { id: 'llama3.2:1b', name: 'llama3.2:1b (Meta / Local Ollama - Active)', status: 'active' },
    { id: 'llama3.2:3b', name: 'llama3.2:3b (Meta)', status: 'staged' },
    { id: 'llama3.1:8b', name: 'llama3.1:8b (Meta)', status: 'staged' },
    { id: 'llama3.3:70b', name: 'llama3.3:70b (Meta)', status: 'staged' },
    { id: 'deepseek-r1:7b', name: 'deepseek-r1:7b (Reasoning)', status: 'staged' },
    { id: 'mistral-7b-instruct', name: 'mistral-7b-instruct (Mistral AI)', status: 'staged' },
    { id: 'qwen2.5:7b', name: 'qwen2.5:7b (Alibaba)', status: 'staged' },
  ]);
  const [selectedModel, setSelectedModel] = useState<string>('llama3.2:1b');

  // Ollama Live Connection State
  const [ollamaStatus, setOllamaStatus] = useState<{
    online: boolean;
    activeModel: string;
    installedModels: string[];
  }>({
    online: true,
    activeModel: 'llama3.2:1b',
    installedModels: ['llama3.2:1b'],
  });

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

  // Workspace Mode (General RAG, Summarization, Science, News, Rewriter)
  const [workspaceMode, setWorkspaceMode] = useState<string>('chat');

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
      const [statusRes, modelsRes, colsRes] = await Promise.all([
        fetch('http://localhost:8000/v1/models/status'),
        fetch('http://localhost:8000/v1/models'),
        fetch('http://localhost:8000/v1/collections/'),
      ]);

      if (statusRes.ok) {
        const sData = await statusRes.json();
        setOllamaStatus({
          online: sData.ollama_online,
          activeModel: sData.active_model || 'llama3.2:1b',
          installedModels: sData.installed_models || ['llama3.2:1b'],
        });
      }

      if (modelsRes.ok) {
        const modelData = await modelsRes.json();
        if (Array.isArray(modelData) && modelData.length > 0) {
          const seen = new Set<string>();
          const list: ModelItem[] = [];
          for (const m of modelData) {
            const modelId = m.model_name || m.id;
            if (modelId && !seen.has(modelId)) {
              seen.add(modelId);
              list.push({
                id: modelId,
                name: modelId === 'llama3.2:1b' ? `${modelId} (Meta / Local Ollama - Active)` : modelId,
                format: m.format,
                quantization: m.quantization,
                status: m.status,
              });
            }
          }
          if (list.length > 0) {
            setModels(list);
            // Default to llama3.2:1b if available
            const hasLlama1b = list.some((m) => m.id === 'llama3.2:1b');
            if (hasLlama1b) {
              setSelectedModel('llama3.2:1b');
            } else {
              setSelectedModel(list[0].id);
            }
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
    const interval = setInterval(checkOllamaAndModels, 15000);
    return () => clearInterval(interval);
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

  // Save conversation history to localStorage
  useEffect(() => {
    localStorage.setItem('chatMessages', JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Adjust textarea height automatically
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
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

  const handleSend = async (customPrompt?: string) => {
    const userText = (customPrompt || input).trim();
    if ((!userText && attachedFiles.length === 0) || isLoading) return;

    setIsLoading(true);
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

      // If backend didn't return text (e.g. offline/network issue) and file is text-based, read directly in browser
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

    // If active document context is selected from Document Management
    if (activeDocContext && !textContext) {
      if (activeDocContext.content) {
        textContext += `\n\n--- [Attached Document: ${activeDocContext.filename}] ---\n${activeDocContext.content}`;
      } else {
        textContext += `\n\n[Referenced Document: ${activeDocContext.filename}]`;
      }
    }

    const fullPrompt = textContext
      ? `${userText || 'Please analyze and explain the document.'}${textContext}`
      : userText;

    const userMessage: Message = {
      role: 'user',
      content: userText || `Attached ${attachedFiles.length} file(s) for analysis.`,
      files: fileMetadata.length > 0 ? fileMetadata : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setAttachedFiles([]);

    // 2. Dispatch request to backend with full grounded context
    try {
      const historyForApi = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));
      historyForApi.push({
        role: 'user',
        content: fullPrompt,
      });

      const res = await fetch('http://localhost:8000/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          messages: historyForApi,
          collection_id: selectedCollectionId || undefined,
          task_mode: workspaceMode,
          stream: false,
        }),
      });

      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      const data = await res.json();
      const assistantMsg =
        data.choices?.[0]?.message?.content || 'No response generated.';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: assistantMsg,
          citations: data.citations || undefined,
        },
      ]);
    } catch (err: any) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error executing request: ${err.message}. Please verify local backend connection.`,
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

  const clearChat = () => {
    if (window.confirm('Clear current chat conversation?')) {
      setMessages([]);
      localStorage.removeItem('chatMessages');
    }
  };

  return (
    <div
      className="chat-container"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Top Workspace Controls Bar */}
      <div className="chat-controls-bar">
        <div className="control-group">
          <label htmlFor="workspace-mode-select">WORKSPACE MODE:</label>
          <select
            id="workspace-mode-select"
            value={workspaceMode}
            onChange={(e) => setWorkspaceMode(e.target.value)}
          >
            <option value="chat">🔮 General Assistant & RAG</option>
            <option value="summarize">📄 Document Summarization</option>
            <option value="science">🔬 Science & Technology Analysis</option>
            <option value="news">📰 News & Editorial Briefing</option>
            <option value="rewriter">✍️ Context Rewriter & Grammar</option>
          </select>
        </div>

        {/* Live Ollama & Model Status Pill */}
        <div className="ollama-live-status">
          <span className={`status-dot ${ollamaStatus.online ? 'dot-online' : 'dot-offline'}`}></span>
          <span className="status-label">
            {ollamaStatus.online
              ? `Ollama: ${selectedModel} (Live)`
              : 'Ollama Offline (Using resilient engine)'}
          </span>
          <button
            type="button"
            className="status-refresh-btn"
            onClick={checkOllamaAndModels}
            title="Refresh local model status"
          >
            🔄
          </button>
        </div>

        {/* Clear Chat Button */}
        {messages.length > 0 && (
          <button
            type="button"
            className="clear-chat-btn"
            onClick={clearChat}
            title="Clear current conversation"
          >
            🗑️ Clear Chat
          </button>
        )}
      </div>

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
            <p>PDFs, Word docs, code, and text will be attached and read by {selectedModel}.</p>
          </div>
        </div>
      )}

      {/* Messages Feed */}
      <div className="messages-feed">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="welcome-icon">🛡️</div>
            <h3>Air-Gapped Offline Assistant</h3>
            <p>
              Connected to <strong>{selectedModel}</strong>. All documents, prompts, embeddings, and inference remain 100% on your local machine with zero network egress.
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
                onClick={() => handleSend('Write a secure Python script for local file processing.')}
              >
                💻 Write Secure Python Code
              </button>
            </div>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div key={idx} className={`message-row message-${m.role}`}>
              <div className="message-bubble">
                <div className="message-header">
                  <span className="role-label">
                    {m.role === 'user' ? '👤 User' : `🤖 Assistant (${selectedModel})`}
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
              <span className="dot-pulse"></span> {selectedModel} is thinking and reading documents...
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
            placeholder="Ask a question or request document analysis... (Enter to send, Shift+Enter for newline)"
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