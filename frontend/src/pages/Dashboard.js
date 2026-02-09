import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { ref, uploadBytesResumable, getDownloadURL, listAll, deleteObject } from 'firebase/storage';
import { storage } from '../utils/firebase';
import PDFViewer from '../components/PDFViewer';
import ChatInterface from '../components/ChatInterface';

const Dashboard = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [userDocuments, setUserDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  
  const { currentUser, logout } = useAuth();
  const navigate = useNavigate();

  // Load user documents on component mount
  useEffect(() => {
    loadUserDocuments();
  }, [currentUser]);

  const loadUserDocuments = async () => {
    if (!currentUser) return;
    
    try {
      setLoading(true);
      const userFolderRef = ref(storage, `documents/${currentUser.uid}`);
      const result = await listAll(userFolderRef);
      
      const documentsPromises = result.items.map(async (itemRef) => {
        const url = await getDownloadURL(itemRef);
        return {
          name: itemRef.name,
          url: url,
          ref: itemRef
        };
      });
      
      const documents = await Promise.all(documentsPromises);
      setUserDocuments(documents);
    } catch (error) {
      console.error("Error loading documents:", error);
      if (error.code !== 'storage/object-not-found') {
        setErrorMessage(`Error loading documents: ${error.message}`);
        setTimeout(() => setErrorMessage(''), 5000);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      const selectedFile = e.target.files[0];
      // Validate file is a PDF
      if (selectedFile.type !== 'application/pdf') {
        setErrorMessage("Please upload a PDF file");
        setTimeout(() => setErrorMessage(''), 5000);
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setErrorMessage("Please select a PDF file to upload");
      setTimeout(() => setErrorMessage(''), 5000);
      return;
    }

    try {
      setUploading(true);
      setUploadProgress(0);
      
      // Create a reference to the storage location
      const storageRef = ref(storage, `documents/${currentUser.uid}/${file.name}`);
      
      // Upload the file
      const uploadTask = uploadBytesResumable(storageRef, file);
      
      // Register observer for state changes, errors, and completion
      uploadTask.on(
        'state_changed',
        (snapshot) => {
          // Track upload progress
          const progress = (snapshot.bytesTransferred / snapshot.totalBytes) * 100;
          setUploadProgress(progress);
        },
        (error) => {
          console.error("Upload error:", error);
          setErrorMessage(`Upload failed: ${error.message}`);
          setTimeout(() => setErrorMessage(''), 5000);
          setUploading(false);
        },
        async () => {
          // Upload completed successfully
          const downloadURL = await getDownloadURL(uploadTask.snapshot.ref);
          
          // Add the new document to the list
          setUserDocuments(prev => [...prev, {
            name: file.name,
            url: downloadURL,
            ref: storageRef
          }]);
          
          setSuccessMessage("Your document has been uploaded successfully");
          setTimeout(() => setSuccessMessage(''), 5000);
          
          setUploading(false);
          setFile(null);
          // Reset file input
          document.getElementById('file-upload').value = '';
        }
      );
    } catch (error) {
      console.error("Upload error:", error);
      setErrorMessage(`Upload failed: ${error.message}`);
      setTimeout(() => setErrorMessage(''), 5000);
      setUploading(false);
    }
  };

  const handleSelectDocument = (document) => {
    setSelectedDocument(document);
  };

  const handleDeleteDocument = async (document) => {
    try {
      await deleteObject(document.ref);
      
      setUserDocuments(prev => prev.filter(doc => doc.name !== document.name));
      
      if (selectedDocument && selectedDocument.name === document.name) {
        setSelectedDocument(null);
      }
      
      setSuccessMessage("The document has been removed");
      setTimeout(() => setSuccessMessage(''), 5000);
    } catch (error) {
      console.error("Delete error:", error);
      setErrorMessage(`Delete failed: ${error.message}`);
      setTimeout(() => setErrorMessage(''), 5000);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error("Logout error:", error);
      setErrorMessage(`Logout failed: ${error.message}`);
      setTimeout(() => setErrorMessage(''), 5000);
    }
  };

  return (
    <div className="min-h-screen bg-background text-white">
      {/* Header */}
      <header className="w-full p-4 border-b border-gray-700 flex justify-between items-center">
        <h1 className="text-xl font-bold">Construction Estimator Chatbot</h1>
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-300">{currentUser?.email}</span>
          <Link 
            to="/profile"
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-md transition-colors"
            title="Settings"
          >
            <svg 
              xmlns="http://www.w3.org/2000/svg" 
              className="h-5 w-5" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" 
              />
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" 
              />
            </svg>
          </Link>
          <button 
            onClick={handleLogout} 
            className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            Logout
          </button>
        </div>
      </header>

      {/* Alert Messages */}
      {errorMessage && (
        <div className="mx-4 mt-2 p-2 bg-red-100 border border-red-400 text-red-700 rounded relative" role="alert">
          <span className="block sm:inline">{errorMessage}</span>
        </div>
      )}
      
      {successMessage && (
        <div className="mx-4 mt-2 p-2 bg-green-100 border border-green-400 text-green-700 rounded relative" role="alert">
          <span className="block sm:inline">{successMessage}</span>
        </div>
      )}

      {/* Main Content */}
      <div className="flex flex-col md:flex-row h-[calc(100vh-72px)]">
        {/* Left Sidebar - Document List */}
        <div 
          className="w-full md:w-80 p-4 border-r border-gray-700 h-auto md:h-full overflow-y-auto"
        >
          <div className="flex flex-col space-y-4">
            <h2 className="font-bold text-sm">Upload Document</h2>
            <input
              id="file-upload"
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
              className="p-1 border border-gray-600 rounded-md w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button 
              onClick={handleUpload} 
              className={`py-2 px-4 rounded-md text-white ${
                !file || uploading ? 'bg-blue-500 opacity-50 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
              }`}
              disabled={!file || uploading}
            >
              {uploading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Uploading {uploadProgress.toFixed(0)}%
                </span>
              ) : 'Upload PDF'}
            </button>
            
            <div className="border-t border-gray-700 my-4"></div>
            
            <h2 className="font-bold text-sm">Your Documents</h2>
            {loading ? (
              <div className="flex justify-center p-4">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-white"></div>
              </div>
            ) : userDocuments.length === 0 ? (
              <p className="text-gray-400">No documents yet. Upload a PDF to get started.</p>
            ) : (
              <div className="flex flex-col space-y-2 mt-2">
                {userDocuments.map((doc) => (
                  <div 
                    key={doc.name}
                    className={`p-2 rounded-md ${
                      selectedDocument && selectedDocument.name === doc.name ? 'bg-blue-700' : 'bg-gray-700'
                    } flex justify-between items-center cursor-pointer hover:bg-gray-600`}
                    onClick={() => handleSelectDocument(doc)}
                  >
                    <p className="truncate text-sm">{doc.name}</p>
                    <button
                      aria-label="Delete document"
                      className="text-gray-300 hover:text-white focus:outline-none"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteDocument(doc);
                      }}
                    >
                      🗑️
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Main Content Area */}
        <div 
          className="flex-1 flex flex-col h-full overflow-hidden"
        >
          {selectedDocument ? (
            <>
              {/* PDF Viewer */}
              <div className="h-3/5 p-4 border-b border-gray-700 overflow-y-auto">
                <PDFViewer fileUrl={selectedDocument.url} />
              </div>
              
              {/* Chat Interface */}
              <div className="h-2/5 p-4 overflow-y-auto">
                <ChatInterface documentUrl={selectedDocument.url} documentName={selectedDocument.name} />
              </div>
            </>
          ) : (
            <div className="flex justify-center items-center h-full">
              <p className="text-gray-400">Select a document to start chatting</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
