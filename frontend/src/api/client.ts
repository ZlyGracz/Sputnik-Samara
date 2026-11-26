import type {
  AnswerRequest,
  AnswerResult,
  AttemptDetail,
  AttemptSummary,
  AuthResponse,
  Course,
  CourseCreate,
  CourseStats,
  CourseUpdate,
  LoginRequest,
  Media,
  Page,
  Question,
  QuestionInput,
  RegisterRequest,
  Role,
  User,
  UserUpdate,
} from "./types";

const TOKEN_KEY = "sputnik_access_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function extractErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  return fallback;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...options, headers });

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const message = extractErrorMessage(data, `Ошибка запроса (${res.status})`);
    throw new ApiError(res.status, message);
  }

  return data as T;
}

function qs(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      sp.set(key, String(value));
    }
  }
  const str = sp.toString();
  return str ? `?${str}` : "";
}

export const api = {
  // Auth
  register: (payload: RegisterRequest) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: LoginRequest) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: () => request<User>("/api/auth/me"),

  // Users (admin)
  getUsers: (params: { search?: string; role?: Role; limit?: number; offset?: number } = {}) =>
    request<Page<User>>(`/api/users${qs(params)}`),

  updateUser: (userId: number, payload: UserUpdate) =>
    request<User>(`/api/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  // Courses
  getCourses: (params: { search?: string; limit?: number; offset?: number } = {}) =>
    request<Page<Course>>(`/api/courses${qs(params)}`),

  getMyCourses: (params: { limit?: number; offset?: number } = {}) =>
    request<Page<Course>>(`/api/courses/my${qs(params)}`),

  getCourse: (courseId: number) => request<Course>(`/api/courses/${courseId}`),

  createCourse: (payload: CourseCreate) =>
    request<Course>("/api/courses", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateCourse: (courseId: number, payload: CourseUpdate) =>
    request<Course>(`/api/courses/${courseId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteCourse: (courseId: number) =>
    request<void>(`/api/courses/${courseId}`, {
      method: "DELETE",
    }),

  getCourseStats: (courseId: number) =>
    request<CourseStats>(`/api/courses/${courseId}/stats`),

  // Questions
  getCourseQuestions: (courseId: number) =>
    request<Question[]>(`/api/courses/${courseId}/questions`),

  createQuestion: (courseId: number, payload: QuestionInput) =>
    request<Question>(`/api/courses/${courseId}/questions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateQuestion: (questionId: number, payload: QuestionInput) =>
    request<Question>(`/api/questions/${questionId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  deleteQuestion: (questionId: number) =>
    request<void>(`/api/questions/${questionId}`, {
      method: "DELETE",
    }),

  // Media
  uploadMedia: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return request<Media>("/api/media", {
      method: "POST",
      body: formData,
    });
  },

  // Attempts
  startAttempt: (courseId: number) =>
    request<AttemptDetail>(`/api/courses/${courseId}/attempts`, {
      method: "POST",
    }),

  getMyAttempts: (params: { course_id?: number; limit?: number; offset?: number } = {}) =>
    request<Page<AttemptSummary>>(`/api/attempts/my${qs(params)}`),

  getAttempt: (attemptId: number) => request<AttemptDetail>(`/api/attempts/${attemptId}`),

  submitAnswer: (attemptId: number, payload: AnswerRequest) =>
    request<AnswerResult>(`/api/attempts/${attemptId}/answers`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  finishAttempt: (attemptId: number) =>
    request<AttemptDetail>(`/api/attempts/${attemptId}/finish`, {
      method: "POST",
    }),
};