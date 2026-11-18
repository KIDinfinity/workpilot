export type Citation = {
  index: number;
  doc_id: string;
  title: string;
  section?: string;
  text: string;
  score: number;
};

export type StreamStatus = "idle" | "retrieving" | "streaming" | "done" | "error";
