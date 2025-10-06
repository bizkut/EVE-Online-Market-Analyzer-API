import React from 'react';
import StatusBar from './StatusBar';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="bg-background text-neutral-text min-h-screen font-sans flex flex-col">
      <header className="bg-panel p-4 border-b border-gray-700">
        <h1 className="text-2xl font-bold text-white font-orbitron">EVE Online Market Analyzer</h1>
      </header>
      <main className="p-4 sm:p-6 lg:p-8 flex-grow">
        {children}
      </main>
      <StatusBar />
    </div>
  );
};

export default Layout;