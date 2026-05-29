import { useAuth } from "./context/AuthContext";
import AuthPage from "./pages/AuthPage";
import Workspace from "./pages/Workspace";

export default function App() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Workspace /> : <AuthPage />;
}
