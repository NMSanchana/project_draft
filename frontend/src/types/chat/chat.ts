export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
}

export interface ChatWidgetProps {
  isDarkMode?: boolean;
  userName?: string;
  onSendMessage?: (message: string) => Promise<string> | void;
}
