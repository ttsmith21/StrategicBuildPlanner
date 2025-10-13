import axios from "axios";
import { API_BASE_URL } from "./config";
import type { MeetingPrepResponseData, TranscribeResponseData } from "./types";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

/**
 * Generate meeting prep materials (project brief + agenda)
 */
export async function generateMeetingPrep(sessionId: string): Promise<MeetingPrepResponseData> {
  const response = await api.post<MeetingPrepResponseData>("/meeting/prep", {
    session_id: sessionId,
  });
  return response.data;
}

/**
 * Transcribe audio file to text using Whisper
 */
export async function transcribeAudio(audioFile: File): Promise<TranscribeResponseData> {
  const formData = new FormData();
  formData.append("audio_file", audioFile);

  const response = await api.post<TranscribeResponseData>("/transcribe", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}
