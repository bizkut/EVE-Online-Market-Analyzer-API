import React from 'react';
import ThemeToggle from './ThemeToggle';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="bg-light-background text-light-neutral-text dark:bg-background dark:text-neutral-text min-h-screen font-sans flex flex-col transition-colors duration-300">
      <header className="bg-light-panel dark:bg-panel p-4 border-b dark:border-gray-700 shadow-md">
        <div className="container mx-auto flex justify-between items-center">
            <h1 className="text-2xl font-bold text-light-neutral-text dark:text-white font-orbitron">EVE Online Market Analyzer</h1>
            <ThemeToggle />
        </div>
      </header>
      <main className="p-4 sm:p-6 lg:p-8 flex-grow container mx-auto">
        {children}
      </main>
    </div>
  );
};

export default Layout;