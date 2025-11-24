import { useState, useRef, useEffect } from "react";
import { MessageBubble } from "./MessageBubble";
import { StatusIndicator } from "./StatusIndicator";
import { DownloadButton } from "./DownloadButton";
import { PreviewFrame } from "./PreviewFrame";
import type { AgentStage } from "../types";

interface ChatInterfaceProps {
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    timestamp: Date;
  }>;
  isGenerating: boolean;
  currentStage: AgentStage;
  statusMessage: string;
  zipData: string | null;
  fileCount: number | null;
  previewUrl: string | null;
  previewExpiresAt: number | null;
  error: string | null;
  errorCount?: number;
  iteration?: number;
  onSendMessage: (prompt: string) => void;
  onDownload: () => void;
  onClear: () => void;
}

export const ChatInterface = ({
  messages,
  isGenerating,
  currentStage,
  statusMessage,
  zipData,
  fileCount,
  previewUrl,
  previewExpiresAt,
  error,
  errorCount,
  iteration,
  onSendMessage,
  onDownload,
  onClear,
}: ChatInterfaceProps) => {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, statusMessage]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isGenerating) {
      onSendMessage(input.trim());
      setInput("");
      if (inputRef.current) {
        inputRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${e.target.scrollHeight}px`;
  };

  return (
    <div className="flex flex-col h-screen bg-white dark:bg-gray-900">
      {/* Header */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            Code Generator
          </h1>
          <div className="flex space-x-2">
            {messages.length > 0 && (
              <button
                onClick={onClear}
                className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
              >
                Clear
              </button>
            )}
            {zipData && (
              <DownloadButton
                onClick={onDownload}
                fileCount={fileCount}
                disabled={!zipData}
              />
            )}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 && (
            <div className="text-center mt-20">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-2">
                Welcome to Code Generator
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-8">
                Describe the web application you want to build, and we'll
                generate the complete codebase for you.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {isGenerating && (
            <StatusIndicator
              stage={currentStage}
              message={statusMessage}
              errorCount={errorCount}
              iteration={iteration}
            />
          )}

          {error && (
            <div className="mb-4 p-4 bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg">
              <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
          )}

          {zipData && !isGenerating && (
            <div className="mb-4 p-4 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded-lg">
              <p className="text-sm text-green-800 dark:text-green-200 mb-2">
                Codebase generated successfully! Click the download button above
                to get your files.
              </p>
            </div>
          )}

          {previewUrl && previewExpiresAt && (
            <div className="mb-4">
              <PreviewFrame
                previewUrl={previewUrl}
                expiresAt={previewExpiresAt}
              />
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-4">
        <div className="max-w-4xl mx-auto">
          <form onSubmit={handleSubmit} className="flex items-end space-x-2">
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Describe the web application you want to build..."
                disabled={isGenerating}
                rows={1}
                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ maxHeight: "200px" }}
              />
            </div>
            <button
              type="submit"
              disabled={!input.trim() || isGenerating}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isGenerating ? (
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Generating...</span>
                </div>
              ) : (
                "Send"
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
