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
    { id: 'llama3.2:3b', name: 'llama3.2:3b (Meta)', status: 'active' },
    { id: 'llama3.1:8b', name: 'llama3.1:8b (Meta)', status: 'active' },
    { id: 'llama3.3:70b', name: 'llama3.3:70b (Meta)', status: 'active' },
    { id: 'deepseek-r1:7b', name: 'deepseek-r1:7b (Reasoning)', status: 'active' },
    { id: 'deepseek-r1:8b', name: 'deepseek-r1:8b (Reasoning)', status: 'active' },
    { id: 'deepseek-coder:6.7b', name: 'deepseek-coder:6.7b (Coding)', status: 'active' },
    { id: 'mistral-7b-instruct', name: 'mistral-7b-instruct (Mistral AI)', status: 'active' },
    { id: 'mixtral:8x7b', name: 'mixtral:8x7b (MoE)', status: 'active' },
    { id: 'qwen2.5:7b', name: 'qwen2.5:7b (Alibaba)', status: 'active' },
    { id: 'qwen2.5-coder:7b', name: 'qwen2.5-coder:7b (Coding)', status: 'active' },
    { id: 'phi3.5:3.8b', name: 'phi3.5:3.8b (Microsoft)', status: 'active' },
    { id: 'gemma2:9b', name: 'gemma2:9b (Google)', status: 'active' },
    { id: 'gemma2:2b', name: 'gemma2:2b (Google)', status: 'active' },
    { id: 'codellama:7b', name: 'codellama:7b (Meta)', status: 'active' },
    { id: 'llama-2-7b-chat', name: 'llama-2-7b-chat (Meta)', status: 'active' },
    { id: 'tinyllama:1.1b', name: 'tinyllama:1.1b (Fast)', status: 'active' },
  ]);
  const [selectedModel, setSelectedModel] = useState<string>('llama3.2:3b');

  // Attached files for current draft
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);

  // Collections for Grounded RAG
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null);

  // Workspace Mode (General RAG, Summarization, Science, News, Rewriter)
  const [workspaceMode, setWorkspaceMode] = useState<string>('chat');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const [modelsRes, colsRes] = await Promise.all([
          fetch('http://localhost:8000/v1/models'),
          fetch('http://localhost:8000/v1/collections/'),
        ]);

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
                  name: modelId,
                  format: m.format,
                  quantization: m.quantization,
                  status: m.status,
                });
              }
            }
            if (list.length > 0) {
              setModels(list);
              setSelectedModel(list[0].id);
            }
          }
        }

        if (colsRes.ok) {
          const colsData = await colsRes.json();
          setCollections(colsData);
        }
      } catch (e) {
        console.error('Failed to load initial metadata:', e);
      }
    };

    fetchMetadata();
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

  const handleSend = async () => {
    const userText = input.trim();
    if ((!userText && attachedFiles.length === 0) || isLoading) return;

    setIsLoading(true);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    // 1. Process files
    const fileMetadata = attachedFiles.map((f) => ({
      name: f.name,
      size: f.size,
      type: f.type,
    }));

    // Read textual files to attach to prompt context
    let textContext = '';
    for (const f of attachedFiles) {
      if (
        f.name.endsWith('.txt') ||
        f.name.endsWith('.md') ||
        f.name.endsWith('.json') ||
        f.name.endsWith('.py') ||
        f.name.endsWith('.csv')
      ) {
        try {
          const content = await f.text();
          textContext += `\n\n--- [Attached Document: ${f.name}] ---\n${content}`;
        } catch (err) {
          console.warn('Could not read text content:', err);
        }
      }

      // Also upload to RAG index in background
      try {
        const formData = new FormData();
        formData.append('file', f);
        if (selectedCollectionId) {
          formData.append('collection_id', String(selectedCollectionId));
        }
        fetch('http://localhost:8000/v1/documents/upload', {
          method: 'POST',
          body: formData,
        }).catch((err) => console.warn('Background document upload notice:', err));
      } catch (e) {
        console.warn('Document upload error:', e);
      }
    }

    const fullPrompt = textContext ? `${userText}${textContext}` : userText;

    const userMessage: Message = {
      role: 'user',
      content: userText || `Attached ${attachedFiles.length} file(s) for analysis.`,
      files: fileMetadata.length > 0 ? fileMetadata : undefined,
    };

    setMessages((prev) => [...prev, userMessage]);
    setAttachedFiles([]);

    // 2. Dispatch request to backend
    try {
      const res = await fetch('http://localhost:8000/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: selectedModel,
          messages: [...messages, userMessage].map((m) => ({
            role: m.role,
            content: m.content,
          })),
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
      </div>

      {/* Drag & drop indicator */}
      {isDragging && (
        <div className="drag-overlay">
          <div className="drag-content">
            <span className="drag-icon">📂</span>
            <h3>Drop documents here</h3>
            <p>Files will be attached to your prompt and indexed into the local RAG store.</p>
          </div>
        </div>
      )}

      {/* Messages Feed */}
      <div className="messages-feed">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <h3>Offline Assistant</h3>
            <p>
              Operating in a zero-egress local environment. All prompts, documents, embeddings, and outputs remain strictly inside this secure deployment.
            </p>
          </div>
        ) : (
          messages.map((m, idx) => (
            <div key={idx} className={`message-row message-${m.role}`}>
              <div className="message-bubble">
                <div className="message-header">
                  <span className="role-label">
                    {m.role === 'user' ? 'User' : 'Assistant'}
                  </span>
                </div>

                {m.files && m.files.length > 0 && (
                  <div className="attached-files-chips">
                    {m.files.map((file, fIdx) => (
                      <span key={fIdx} className="file-chip">
                        📄 {file.name}
                      </span>
                    ))}
                  </div>
                )}

                <div className="message-content">{m.content}</div>

                {m.citations && m.citations.length > 0 && (
                  <div className="citations-tray">
                    <div className="citations-heading">Grounded Document Citations:</div>
                    <div className="citations-list">
                      {m.citations.map((cite, cIdx) => (
                        <div key={cIdx} className="citation-chip" title={cite.excerpt}>
                          <span className="cite-doc">📄 {cite.filename}</span>
                          {cite.page_or_section && (
                            <span className="cite-section">[{cite.page_or_section}]</span>
                          )}
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
              <span className="dot-pulse"></span> Generating response locally...
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
                <span className="pill-name">📄 {file.name}</span>
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
            title="Attach documents (.txt, .md, .pdf, .docx, .json, .py)"
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
            placeholder="Ask a question or enter a prompt... (Enter to send, Shift+Enter for newline)"
            disabled={isLoading}
            className="main-chat-textarea"
            rows={1}
          />

          {/* Send Button */}
          <button
            type="button"
            className={`send-button ${input.trim() || attachedFiles.length > 0 ? 'send-active' : ''}`}
            onClick={handleSend}
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