import { useState, useEffect } from "react";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface PreviewFrameProps {
  previewUrl: string;
  expiresAt: number;
  onExpire?: () => void;
}

export const PreviewFrame = ({
  previewUrl,
  expiresAt,
  onExpire,
}: PreviewFrameProps) => {
  const [timeRemaining, setTimeRemaining] = useState<number>(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [iframeError, setIframeError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadTimeout, setLoadTimeout] = useState<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const updateTimer = () => {
      const now = Date.now() / 1000; // Convert to seconds
      const remaining = Math.max(0, expiresAt - now);
      setTimeRemaining(remaining);

      if (remaining === 0 && onExpire) {
        onExpire();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, [expiresAt, onExpire]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  // Construct full preview URL
  const fullPreviewUrl = previewUrl.startsWith("http")
    ? previewUrl
    : `${API_BASE_URL}${previewUrl.startsWith("/") ? "" : "/"}${previewUrl}`;

  // Debug logging
  useEffect(() => {
    console.log("PreviewFrame - previewUrl:", previewUrl);
    console.log("PreviewFrame - fullPreviewUrl:", fullPreviewUrl);
    console.log("PreviewFrame - expiresAt:", expiresAt);
    console.log("PreviewFrame - timeRemaining:", timeRemaining);
  }, [previewUrl, fullPreviewUrl, expiresAt, timeRemaining]);

  const handleRefresh = () => {
    setIframeError(false);
    setIsLoading(true);
    const iframe = document.getElementById(
      "preview-iframe"
    ) as HTMLIFrameElement;
    if (iframe) {
      // Force reload by setting src to empty then back
      const currentSrc = iframe.src;
      iframe.src = "";
      setTimeout(() => {
        if (iframe) {
          iframe.src = currentSrc;
          // Set timeout for loading
          const timeout = setTimeout(() => {
            setIsLoading(false);
            // Check if iframe content loaded
            try {
              const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
              if (!iframeDoc || iframeDoc.body.innerHTML.trim() === "") {
                console.warn("Preview iframe appears empty after timeout");
                setIframeError(true);
              }
            } catch (e) {
              // Cross-origin, can't check content
              console.log("Cannot check iframe content (cross-origin)");
            }
          }, 10000); // 10 second timeout
          setLoadTimeout(timeout);
        }
      }, 100);
    }
  };

  const handleFullscreen = () => {
    if (!isFullscreen) {
      const iframe = document.getElementById("preview-iframe");
      if (iframe?.requestFullscreen) {
        iframe.requestFullscreen();
        setIsFullscreen(true);
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  // Set loading timeout when previewUrl changes
  useEffect(() => {
    if (!previewUrl) return;
    
    setIsLoading(true);
    setIframeError(false);
    
    // Set timeout for loading
    const timeout = setTimeout(() => {
      setIsLoading(false);
      // Check if iframe loaded
      const iframe = document.getElementById("preview-iframe") as HTMLIFrameElement;
      if (iframe) {
        try {
          const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
          if (!iframeDoc || iframeDoc.body.innerHTML.trim() === "") {
            console.warn("Preview iframe appears empty after timeout");
            setIframeError(true);
          }
        } catch (e) {
          // Cross-origin, can't check content - assume it's loading
          console.log("Cannot check iframe content (cross-origin), assuming loaded");
        }
      }
    }, 15000); // 15 second timeout
    
    return () => {
      clearTimeout(timeout);
    };
  }, [previewUrl]);

  if (timeRemaining === 0) {
    return (
      <div className="p-4 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded-lg">
        <p className="text-sm text-yellow-800 dark:text-yellow-200">
          Preview has expired. Please generate a new codebase to get a fresh
          preview.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
      {/* Preview Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-100 dark:bg-gray-700 border-b border-gray-300 dark:border-gray-600">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Live Preview
          </span>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              Expires in {formatTime(timeRemaining)}
            </span>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRefresh}
            className="p-1.5 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            title="Refresh preview"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
          <button
            onClick={handleFullscreen}
            className="p-1.5 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors"
            title="Toggle fullscreen"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Preview Iframe */}
      <div className="relative" style={{ height: "600px" }}>
        {iframeError ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                Failed to load preview
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-500 mb-4">
                URL: {fullPreviewUrl}
              </p>
              <button
                onClick={handleRefresh}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        ) : (
          <>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-50 dark:bg-gray-900 z-10">
                <div className="text-center">
                  <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Loading preview...
                  </p>
                </div>
              </div>
            )}
            <iframe
              id="preview-iframe"
              src={fullPreviewUrl}
              className="w-full h-full border-0"
              title="Preview"
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
              onLoad={() => {
                console.log("Preview iframe loaded");
                setIsLoading(false);
                setIframeError(false);
                if (loadTimeout) {
                  clearTimeout(loadTimeout);
                  setLoadTimeout(null);
                }
              }}
              onError={(e) => {
                console.error("Preview iframe error:", e);
                setIsLoading(false);
                setIframeError(true);
                if (loadTimeout) {
                  clearTimeout(loadTimeout);
                  setLoadTimeout(null);
                }
              }}
            />
          </>
        )}
      </div>
    </div>
  );
};

