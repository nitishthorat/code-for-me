import type { AgentStage } from "../types";

interface StatusIndicatorProps {
  stage: AgentStage;
  message: string;
  errorCount?: number;
  iteration?: number;
}

const stageLabels: Record<string, string> = {
  planner: "Planning & Design",
  architect: "Architecting",
  coder: "Generating Code",
  validator_fixer: "Validating & Fixing",
  downloader: "Packaging",
  preview_server: "Starting Preview",
};

const stageColors: Record<string, string> = {
  planner: "bg-blue-500",
  architect: "bg-purple-500",
  coder: "bg-green-500",
  validator_fixer: "bg-yellow-500",
  downloader: "bg-orange-500",
  preview_server: "bg-indigo-500",
};

export const StatusIndicator = ({ stage, message, errorCount, iteration }: StatusIndicatorProps) => {
  if (!stage) return null;

  const stages: AgentStage[] = [
    "planner",
    "architect",
    "coder",
    "validator_fixer",
    "downloader",
    "preview_server",
  ];
  const currentIndex = stages.indexOf(stage);

  return (
    <div className="mb-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {stageLabels[stage]}
          {iteration !== undefined && iteration > 1 && (
            <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
              (Iteration {iteration})
            </span>
          )}
        </span>
        <div className="flex items-center space-x-2">
          {errorCount !== undefined && errorCount > 0 && (
            <span className="text-xs px-2 py-1 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded">
              {errorCount} error{errorCount !== 1 ? 's' : ''}
            </span>
          )}
          {errorCount !== undefined && errorCount === 0 && (
            <span className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded">
              All errors fixed
            </span>
          )}
          <div className="flex space-x-1">
            {stages.map((s, index) => (
              <div
                key={s}
                className={`w-2 h-2 rounded-full ${
                  index <= currentIndex && s
                    ? stageColors[s]
                    : "bg-gray-300 dark:bg-gray-600"
                }`}
              />
            ))}
          </div>
        </div>
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400">{message}</p>
    </div>
  );
};
