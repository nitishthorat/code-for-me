import { useState, useCallback } from "react";
import type { Message, StreamEvent, AgentStage } from "../types";
import { generateCode, downloadZip } from "../services/api";

export const useCodeGeneration = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentStage, setCurrentStage] = useState<AgentStage>(null);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [zipData, setZipData] = useState<string | null>(null);
  const [fileCount, setFileCount] = useState<number | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewToken, setPreviewToken] = useState<string | null>(null);
  const [previewExpiresAt, setPreviewExpiresAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCount, setErrorCount] = useState<number | undefined>(undefined);
  const [iteration, setIteration] = useState<number | undefined>(undefined);

  const addMessage = useCallback(
    (role: "user" | "assistant", content: string) => {
      const newMessage: Message = {
        id: Date.now().toString(),
        role,
        content,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, newMessage]);
      return newMessage.id;
    },
    []
  );

  const updateLastMessage = useCallback((content: string) => {
    setMessages((prev) => {
      const updated = [...prev];
      if (
        updated.length > 0 &&
        updated[updated.length - 1].role === "assistant"
      ) {
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content,
        };
      }
      return updated;
    });
  }, []);

  const handleStreamEvent = useCallback(
    (event: StreamEvent) => {
      if (event.status === "error") {
        setError(event.message);
        setIsGenerating(false);
        return;
      }

      setCurrentStage(event.stage || null);
      setStatusMessage(event.message);
      
      // Update error count and iteration if provided
      if (event.error_count !== undefined) {
        setErrorCount(event.error_count);
      }
      if (event.iteration !== undefined) {
        setIteration(event.iteration);
      }

      if (event.status === "completed") {
        setIsGenerating(false);
        if (event.zip_data) {
          setZipData(event.zip_data);
          setFileCount(event.file_count || null);
        }
        // Handle preview info
        if (event.preview_url) {
          setPreviewUrl(event.preview_url);
        }
        if (event.preview_token) {
          setPreviewToken(event.preview_token);
        }
        if (event.preview_expires_at) {
          setPreviewExpiresAt(event.preview_expires_at);
        }
      }

      // Update the last assistant message with status
      updateLastMessage(event.message);
    },
    [updateLastMessage]
  );

  const startGeneration = useCallback(
    async (prompt: string) => {
      setError(null);
      setZipData(null);
      setFileCount(null);
      setPreviewUrl(null);
      setPreviewToken(null);
      setPreviewExpiresAt(null);
      setIsGenerating(true);
      setCurrentStage(null);
      setStatusMessage("");

      // Add user message
      addMessage("user", prompt);

      // Add initial assistant message
      const assistantId = addMessage(
        "assistant",
        "Starting code generation..."
      );

      try {
        await generateCode(prompt, handleStreamEvent);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "An unknown error occurred";
        setError(errorMessage);
        setIsGenerating(false);
        updateLastMessage(`Error: ${errorMessage}`);
      }
    },
    [addMessage, handleStreamEvent, updateLastMessage]
  );

  const handleDownload = useCallback(() => {
    if (zipData) {
      downloadZip(zipData, "codebase.zip");
    }
  }, [zipData]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setZipData(null);
    setFileCount(null);
    setPreviewUrl(null);
    setPreviewToken(null);
    setPreviewExpiresAt(null);
    setError(null);
    setCurrentStage(null);
    setStatusMessage("");
    setErrorCount(undefined);
    setIteration(undefined);
  }, []);

  return {
    messages,
    isGenerating,
    currentStage,
    statusMessage,
    zipData,
    fileCount,
    previewUrl,
    previewToken,
    previewExpiresAt,
    error,
    errorCount,
    iteration,
    startGeneration,
    handleDownload,
    clearMessages,
  };
};
