export type Role = "user" | "assistant";

export type ChatMessage = {
  role: Role;
  content: string;
};

export type Match = {
  id: number;
  file_path: string;
  caption: string | null;
  camera_model: string | null;
  capture_time: string | null;
  rating: number | null;
  similarity: number | null;
  keywords: string[];
  collections: string[];
};

export type ChatResponse = {
  answer: string;
  structured_calls: Record<string, unknown>[];
  matches: Match[];
};

export type Turn = {
  id: string;
  role: Role;
  content: string;
  loading?: boolean;
  error?: string;
  structured_calls?: Record<string, unknown>[];
  matches?: Match[];
};
