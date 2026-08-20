import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ChatInterface from './ChatInterface';

// Mock fetch API
global.fetch = jest.fn();

describe('ChatInterface', () => {
  beforeEach(() => {
    fetch.mockClear();
    // Clear localStorage before each test
    localStorage.clear();
  });

  test('renders chat interface with model selector and controls', () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { id: 'llama-7b-chat', name: 'Llama 2 7B Chat' },
        { id: 'mistral-7b', name: 'Mistral 7B' }
      ]
    });

    render(<ChatInterface />);

    // Check for model selector
    const modelSelect = screen.getByLabelText(/model:/i);
    expect(modelSelect).toBeInTheDocument();
    expect(modelSelect).toHaveValue('llama-7b-chat');

    // Check for controls
    expect(screen.getByRole('button', { name: /copy conversation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /export conversation/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear chat/i })).toBeInTheDocument();

    // Check for input and send button
    expect(screen.getByPlaceholderText(/type your message here/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument();
  });

  test('loads models from API and sets selected model', async () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { id: 'llama-7b-chat', name: 'Llama 2 7B Chat' },
        { id: 'mistral-7b', name: 'Mistral 7B' }
      ]
    });

    const { findByLabelText } = render(<ChatInterface />);

    // Wait for the model options to be populated
    const llamaOption = await screen.findByOptionValue('llama-7b-chat');
    expect(llamaOption).toBeInTheDocument();
    const mistralOption = await screen.findByOptionValue('mistral-7b');
    expect(mistralOption).toBeInTheDocument();
  });

  test('sends message with selected model', async () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'llama-7b-chat', name: 'Llama 2 7B Chat' }]
    });
    // Mock the chat completion API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: 'Hello! How can I help you today?'
            }
          }
        ]
      })
    });

    render(<ChatInterface />);

    const modelSelect = screen.getByLabelText(/model:/i);
    fireEvent.change(modelSelect, { target: { value: 'llama-7b-chat' } });

    const input = screen.getByPlaceholderText(/type your message here/i);
    const button = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(button);

    // Wait for loading state
    expect(await screen.findByText(/sending.../i)).toBeInTheDocument();

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText(/hello! how can i help you today?/i)).toBeInTheDocument();
    });

    // Verify fetch was called twice: once for models, once for chat
    expect(fetch).toHaveBeenCalledTimes(2);
    // Check the chat completion call
    expect(fetch).toHaveBeenNthCalledWith(2, 'http://localhost:8000/v1/chat/completions', expect.objectContaining({
      method: 'POST',
      headers: expect.objectContaining({
        'Content-Type': 'application/json'
      }),
      body: expect.stringContaining('"model":"llama-7b-chat"')
    }));
  });

  test('persists messages to localStorage', async () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'llama-7b-chat', name: 'Llama 2 7B Chat' }]
    });
    // Mock the chat completion API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: 'Hi there!'
            }
          }
        ]
      })
    });

    render(<ChatInterface />);

    const input = screen.getByPlaceholderText(/type your message here/i);
    const button = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Hello' } });
    fireEvent.click(button);

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText(/hi there!/i)).toBeInTheDocument();
    });

    // Reload the component to see if it loads from localStorage
    // We'll unmount and mount a new instance
    const { rerender } = render(<ChatInterface />);
    // Mock models API again for the rerender
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'llama-7b-chat', name: 'Llama 2 7B Chat' }]
    });

    // Wait for the messages to appear
    expect(await screen.findByText(/you:/i)).toBeInTheDocument();
    expect(await screen.findByText(/hello/i)).toBeInTheDocument();
    expect(await screen.findByText(/assistant:/i)).toBeInTheDocument();
    expect(await screen.findByText(/hi there!/i)).toBeInTheDocument();
  });

  test('copy conversation button works', async () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'llama-7b-chat', name: 'Llama 2 7B Chat' }]
    });
    // Mock the chat completion API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: 'Hello!'
            }
          }
        ]
      })
    });

    // Mock navigator.clipboard
    navigator.clipboard = {
      writeText: jest.fn(),
    } as any;

    render(<ChatInterface />);

    const input = screen.getByPlaceholderText(/type your message here/i);
    const button = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Hi' } });
    fireEvent.click(button);

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText(/hello!/i)).toBeInTheDocument();
    });

    // Click copy button
    const copyButton = screen.getByRole('button', { name: /copy conversation/i });
    fireEvent.click(copyButton);

    // Expect alert and clipboard write
    expect(window.alert).toHaveBeenCalledWith('Conversation copied to clipboard!');
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(expect.stringContaining('You: Hi\nAssistant: Hello!'));
  });

  test('export conversation button works', async () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'llama-7b-chat', name: 'Llama 2 7B Chat' }]
    });
    // Mock the chat completion API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: 'Hello!'
            }
          }
        ]
      })
    });

    // Mock URL.createObjectURL and revokeObjectURL
    const urlCreateMock = jest.fn().mockReturnValue('fake-url');
    const urlRevokeMock = jest.fn();
    Object.defineProperty(window, 'URL', {
      value: {
        createObjectURL: urlCreateMock,
        revokeObjectURL: urlRevokeMock,
      },
      writable: true
    });

    render(<ChatInterface />);

    const input = screen.getByPlaceholderText(/type your message here/i);
    const button = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Hi' } });
    fireEvent.click(button);

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText(/hello!/i)).toBeInTheDocument();
    });

    // Click export button
    const exportButton = screen.getByRole('button', { name: /export conversation/i });
    fireEvent.click(exportButton);

    // Expect that a URL was created and an element was clicked
    expect(urlCreateMock).toHaveBeenCalled();
    expect(urlRevokeMock).toHaveBeenCalled();
    // Check that an anchor element was created and clicked (we can't easily test the click, but we can check the call)
  });

  test('clear conversation button works', async () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'llama-7b-chat', name: 'Llama 2 7B Chat' }]
    });
    // Mock the chat completion API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        choices: [
          {
            message: {
              content: 'Hello!'
            }
          }
        ]
      })
    });

    render(<ChatInterface />);

    const input = screen.getByPlaceholderText(/type your message here/i);
    const button = screen.getByRole('button', { name: /send/i });

    fireEvent.change(input, { target: { value: 'Hi' } });
    fireEvent.click(button);

    // Wait for response
    await waitFor(() => {
      expect(screen.getByText(/hello!/i)).toBeInTheDocument();
    });

    // Confirm the alert for clear conversation
    window.confirm = jest.fn().mockReturnValue(true);

    // Click clear button
    const clearButton = screen.getByRole('button', { name: /clear chat/i });
    fireEvent.click(clearButton);

    // Expect that the messages are cleared
    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to clear the conversation?');
    // Wait a bit for the state to update
    await waitFor(() => {
      expect(screen.queryByText(/you:/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/hi/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/assistant:/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/hello!/i)).not.toBeInTheDocument();
    });
  });

  test('disables input and buttons when loading', async () => {
    // Mock the models API response
    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => [{ id: 'llama-7b-chat', name: 'Llama 2 7B Chat' }]
    });
    // Mock the chat completion API response to delay
    fetch.mockImplementationOnce(() => {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            ok: true,
            json: async () => ({
              choices: [
                {
                  message: {
                    content: 'Delayed response'
                  }
                }
              ]
            })
          });
        }, 100);
      });
    });

    render(<ChatInterface />);

    const input = screen.getByPlaceholderText(/type your message here/i);
    const button = screen.getByRole('button', { name: /send/i });
    const modelSelect = screen.getByLabelText(/model:/i);
    const copyButton = screen.getByRole('button', { name: /copy conversation/i });
    const exportButton = screen.getByRole('button', { name: /export conversation/i });
    const clearButton = screen.getByRole('button', { name: /clear chat/i });

    // Initially, buttons should be enabled (no messages yet, but copy/export/clear are disabled until messages exist)
    expect(input).not.toBeDisabled();
    expect(button).not.toBeDisabled();
    expect(modelSelect).not.toBeDisabled();
    expect(copyButton).toBeDisabled(); // No messages yet
    expect(exportButton).toBeDisabled(); // No messages yet
    expect(clearButton).toBeDisabled(); // No messages yet

    // Send a message
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.click(button);

    // While loading, input, send, and model select should be disabled
    expect(await screen.findByText(/sending.../i)).toBeInTheDocument();
    expect(input).toBeDisabled();
    expect(button).toBeDisabled();
    expect(modelSelect).toBeDisabled();
    // Copy, export, clear should remain disabled (they depend on message count, which is 1 user message, but we haven't added assistant yet)
    // Actually, after sending the user message, we have one message, so copy/export/clear should be enabled?
    // In our component, we disable copy/export/clear based on messages.length === 0
    // After sending the user message, we have 1 message, so they should be enabled.
    // However, we set isLoading to true before the API call, and we disable the input and send button, but not the model select?
    // Looking at the code: we disable the input and send button, but not the model select.
    // And we disable copy/export/clear based on messages.length === 0.
    // So after sending the user message, we have 1 message, so copy/export/clear should be enabled.
    // But note: we setMessages with the user message, then setInput(''), then setIsLoading(true).
    // So at the moment of loading, messages.length is 1, so copy/export/clear are enabled.
    expect(copyButton).not.toBeDisabled();
    expect(exportButton).not.toBeDisabled();
    expect(clearButton).not.toBeDisabled();

    // Wait for the response
    await waitFor(() => {
      expect(screen.getByText(/delayed response/i)).toBeInTheDocument();
    });

    // After loading, all should be enabled again
    expect(input).not.toBeDisabled();
    expect(button).not.toBeDisabled();
    expect(modelSelect).not.toBeDisabled();
    expect(copyButton).not.toBeDisabled();
    expect(exportButton).not.toBeDisabled();
    expect(clearButton).not.toBeDisabled();
  });
});