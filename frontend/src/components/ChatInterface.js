import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { sendChatMessage } from '../utils/api';

const Message = ({ message, isUser }) => {
  // Format citation references in the message
  const formatMessage = (text) => {
    if (!text) return '';
    
    // Basic formatting for page citations: [Page X]
    const formattedText = text.replace(
      /\[Page (\d+)\]/g, 
      '<span style="color: #63B3ED; font-weight: bold; margin-left: 4px;">[Page $1]</span>'
    );
    
    return <span dangerouslySetInnerHTML={{ __html: formattedText }} />;
  };

  return (
    <div 
      className={`flex mb-4 w-full ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <div 
          className="h-8 w-8 rounded-full bg-blue-500 text-white flex items-center justify-center mr-2"
        >
          AI
        </div>
      )}
      
      <div
        className={`max-w-[80%] p-3 rounded-lg ${isUser ? 'bg-blue-500' : 'bg-gray-700'} text-white`}
      >
        <p>{formatMessage(message.text)}</p>
      </div>
      
      {isUser && (
        <div 
          className="h-8 w-8 rounded-full bg-green-500 text-white flex items-center justify-center ml-2"
        >
          {message.sender?.charAt(0)?.toUpperCase() || 'U'}
        </div>
      )}
    </div>
  );
};

const ChatInterface = ({ documentUrl, documentName }) => {
  const [messages, setMessages] = useState([
    { 
      id: 1, 
      text: `Hello! I'm your construction estimator assistant. I can help answer questions about your document "${documentName}". What would you like to know?`,
      sender: 'AI'
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [contractorType, setContractorType] = useState('General Contractor');
  const messagesEndRef = useRef(null);
  const { currentUser } = useAuth();

  // Auto-scroll to bottom of messages
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
  };

  const handleContractorTypeChange = (e) => {
    setContractorType(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!input.trim()) return;
    
    const userMessage = {
      id: messages.length + 1,
      text: input,
      sender: currentUser?.email || 'User',
      isUser: true
    };
    
    // Add user message to chat
    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setLoading(true);
    
    try {
      // Map contractor type to backend ChatMode enum
      const modeMapping = {
        'General Contractor': 'GC',
        'Mechanical Contractor': 'MC',
        'Electrical Contractor': 'EC'
      };
      const mode = modeMapping[contractorType] || 'NONE';
      
      console.log('[ChatInterface] Sending message to backend:', {
        message: currentInput,
        mode,
        contractorType
      });
      
      // Call the backend API (uses Firebase token automatically)
      const response = await sendChatMessage(currentInput, mode);
      
      console.log('[ChatInterface] Received response from backend:', response);
      
      const aiResponse = {
        id: messages.length + 2,
        text: response.response || "I received your question but couldn't generate a response.",
        sender: 'AI'
      };
      
      // Add AI response to chat
      setMessages(prev => [...prev, aiResponse]);
    } catch (error) {
      console.error('[ChatInterface] Error sending message:', error);
      
      // Show error message as part of the chat
      setMessages(prev => [...prev, {
        id: messages.length + 2,
        text: `Sorry, I encountered an error while processing your request: ${error.message}. Please make sure you have uploaded a PDF document and are logged in.`,
        sender: 'AI'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-2">
        <p className="font-bold">
          Chat with your document: {documentName}
        </p>
        
        <div>
          <label htmlFor="contractor-type" className="text-sm mr-2">Contractor Type:</label>
          <select
            id="contractor-type"
            value={contractorType}
            onChange={handleContractorTypeChange}
            className="text-sm rounded border border-gray-300 px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="General Contractor">General Contractor</option>
            <option value="Mechanical Contractor">Mechanical Contractor</option>
            <option value="Electrical Contractor">Electrical Contractor</option>
          </select>
        </div>
      </div>
      
      {/* Messages display area */}
      <div 
        className="flex-1 overflow-y-auto mb-4 bg-gray-800 p-3 rounded-md"
      >
        <div className="flex flex-col">
          {messages.map((message) => (
            <Message 
              key={message.id} 
              message={message} 
              isUser={message.isUser} 
            />
          ))}
          {loading && (
            <div className="flex justify-start mb-4">
              <div 
                className="p-3 rounded-lg bg-gray-700 text-white flex items-center"
              >
                <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white mr-2"></div>
                <span>Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      {/* Input area */}
      <form onSubmit={handleSubmit} className="mt-auto">
        <div className="flex space-x-2">
          <input
            className="flex-1 px-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Ask a question about your document..."
            value={input}
            onChange={handleInputChange}
            disabled={loading}
          />
          <button 
            type="submit" 
            className={`px-4 py-2 rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
              !input.trim() || loading ? 'opacity-50 cursor-not-allowed' : ''
            }`}
            disabled={!input.trim() || loading}
          >
            {loading ? (
              <>
                <span className="animate-spin inline-block h-4 w-4 border-t-2 border-b-2 border-white rounded-full mr-2"></span>
                Sending...
              </>
            ) : 'Send'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;
