import PDFUpload from './components/PDFUpload'
import ChatApp from './components/ChatApp'

export default function Home() {
  return (
    <div className="h-screen w-screen flex">
      <div className="w-1/3 min-w-[400px]">
        <PDFUpload />
      </div>
      <div className="flex-1">
        <ChatApp />
      </div>
    </div>
  );
}
