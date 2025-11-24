import { useCodeGeneration } from "./hooks/useCodeGeneration";
import { ChatInterface } from "./components/ChatInterface";

function App() {
  const {
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
    startGeneration,
    handleDownload,
    clearMessages,
  } = useCodeGeneration();

  return (
    <ChatInterface
      messages={messages}
      isGenerating={isGenerating}
      currentStage={currentStage}
      statusMessage={statusMessage}
      zipData={zipData}
      fileCount={fileCount}
      previewUrl={previewUrl}
      previewExpiresAt={previewExpiresAt}
      error={error}
      errorCount={errorCount}
      iteration={iteration}
      onSendMessage={startGeneration}
      onDownload={handleDownload}
      onClear={clearMessages}
    />
  );
}

export default App;
