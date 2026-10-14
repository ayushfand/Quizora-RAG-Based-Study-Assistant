import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import CreateQuizPage from "./pages/CreateQuizPage";
import DocumentsPage from "./pages/DocumentsPage";
import HistoryPage from "./pages/HistoryPage";
import QuizzesPage from "./pages/QuizzesPage";
import ResultsPage from "./pages/ResultsPage";
import TakeQuizPage from "./pages/TakeQuizPage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DocumentsPage />} />
        <Route path="/quizzes" element={<QuizzesPage />} />
        <Route path="/create" element={<CreateQuizPage />} />
        <Route path="/quizzes/:quizId" element={<TakeQuizPage />} />
        <Route path="/attempts/:attemptId" element={<ResultsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}
