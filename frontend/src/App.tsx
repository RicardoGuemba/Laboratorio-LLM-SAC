import { SacSimulator } from "./components/SacSimulator";
import { useSacStream } from "./hooks/useSacStream";
import "./styles/sac.css";

export default function App() {
  const stream = useSacStream();
  return <SacSimulator session={stream} />;
}
