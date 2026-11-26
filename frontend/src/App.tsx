import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { CoursesPage } from "./pages/CoursesPage";
import { AttemptPage } from "./pages/AttemptPage";
import { MyAttemptsPage } from "./pages/MyAttemptsPage";
import { CreatorCoursesPage } from "./pages/CreatorCoursesPage";
import { CourseEditorPage } from "./pages/CourseEditorPage";
import { CourseStatsPage } from "./pages/CourseStatsPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/courses" element={<CoursesPage />} />
            <Route
              path="/attempts"
              element={
                <ProtectedRoute>
                  <MyAttemptsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/attempts/:attemptId"
              element={
                <ProtectedRoute>
                  <AttemptPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/creator"
              element={
                <ProtectedRoute roles={["creator", "admin"]}>
                  <CreatorCoursesPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/creator/courses/:courseId"
              element={
                <ProtectedRoute roles={["creator", "admin"]}>
                  <CourseEditorPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/creator/courses/:courseId/stats"
              element={
                <ProtectedRoute roles={["creator", "admin"]}>
                  <CourseStatsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute roles={["admin"]}>
                  <AdminUsersPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;