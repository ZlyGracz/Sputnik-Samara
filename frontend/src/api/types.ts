export type Role = "user" | "creator" | "admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface UserBrief {
  id: number;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: User;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserUpdate {
  role?: Role;
  is_active?: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Course {
  id: number;
  title: string;
  description: string;
  cover_media_id?: string | null;
  cover_url: string | null;
  is_published: boolean;
  author: UserBrief;
  questions_count: number;
  created_at: string;
  updated_at: string;
}

export interface CourseCreate {
  title: string;
  description?: string;
  cover_media_id?: string | null;
}

export interface CourseUpdate {
  title?: string;
  description?: string;
  cover_media_id?: string | null;
  is_published?: boolean;
}

export interface Media {
  id: string;
  kind: "image" | "audio";
  content_type: string;
  size_bytes: number;
  url: string;
}

export interface OptionInput {
  text: string;
  is_correct: boolean;
}

export interface Option {
  id: number;
  text: string;
  is_correct: boolean;
}

export interface QuestionInput {
  text: string;
  image_media_id?: string | null;
  audio_media_id?: string | null;
  position?: number;
  options: OptionInput[];
}

export interface Question {
  id: number;
  course_id: number;
  position: number;
  text: string;
  image_media_id?: string | null;
  image_url: string | null;
  audio_media_id?: string | null;
  audio_url: string | null;
  options: Option[];
}

export interface QuestionStat {
  question_id: number;
  text: string;
  answers_count: number;
  correct_rate: number;
}

export interface CourseStats {
  course_id: number;
  attempts_count: number;
  finished_count: number;
  average_percent: number;
  questions: QuestionStat[];
}

export interface AttemptOption {
  id: number;
  text: string;
}

export interface AttemptQuestion {
  id: number;
  position: number;
  text: string;
  image_url: string | null;
  audio_url: string | null;
  options: AttemptOption[];
  selected_option_id: number | null;
  is_correct: boolean | null;
  correct_option_id: number | null;
}

export type AttemptStatus = "in_progress" | "finished";

export interface AttemptDetail {
  id: number;
  course_id: number;
  course_title: string;
  status: AttemptStatus;
  started_at: string;
  finished_at: string | null;
  total_questions: number;
  answered_count: number;
  score: number | null;
  percent: number | null;
  questions: AttemptQuestion[];
}

export interface AttemptSummary {
  id: number;
  course_id: number;
  course_title: string;
  status: AttemptStatus;
  started_at: string;
  finished_at: string | null;
  total_questions: number;
  score: number | null;
  percent: number | null;
}

export interface AnswerRequest {
  question_id: number;
  option_id: number;
}

export interface AnswerResult {
  question_id: number;
  selected_option_id: number;
  is_correct: boolean;
  correct_option_id: number;
}