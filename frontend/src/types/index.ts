export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface StreamEvent {
  status: "starting" | "processing" | "completed" | "error";
  stage?: "planner" | "architect" | "coder" | "validator_fixer" | "downloader" | "preview_server";
  message: string;
  zip_data?: string;
  file_count?: number;
  preview_url?: string;
  preview_token?: string;
  preview_expires_at?: number;
  error_count?: number;
  iteration?: number;
}

export interface CodeRequest {
  prompt: string;
}

export type AgentStage =
  | "planner"
  | "architect"
  | "coder"
  | "validator_fixer"
  | "downloader"
  | "preview_server"
  | null;
