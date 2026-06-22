import { Arena } from "./components/Arena";
import { useDebateStream } from "./hooks/useDebateStream";
import "./styles/arena.css";

export default function App() {
  const stream = useDebateStream();
  return <Arena {...stream} onStart={stream.startDebate} onNextTurn={stream.nextTurn} onEnd={stream.endDebate} onNewDebate={stream.newDebate} />;
}
