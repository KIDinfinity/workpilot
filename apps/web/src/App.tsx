import { NavLink, Route, Routes } from "react-router";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";

function Nav() {
  const cls = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded ${
      isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100"
    }`;
  return (
    <nav className="flex gap-2 border-b border-gray-200 p-2">
      <NavLink to="/" end className={cls}>
        聊天
      </NavLink>
      <NavLink to="/kb" className={cls}>
        知识库
      </NavLink>
    </nav>
  );
}

export default function App() {
  return (
    <div className="flex h-screen flex-col">
      <Nav />
      <main className="flex-1 min-h-0">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/kb" element={<KnowledgePage />} />
        </Routes>
      </main>
    </div>
  );
}
