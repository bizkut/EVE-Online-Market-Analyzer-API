import type { Metadata } from 'next';
import { Orbitron, Inter } from 'next/font/google';
import './globals.css';
import Providers from '@/components/Providers';

const orbitron = Orbitron({
  subsets: ['latin'],
  variable: '--font-orbitron',
  weight: '700',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'EVE Online Market Analyzer',
  description: 'A dashboard to analyze the EVE Online market.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${orbitron.variable} ${inter.variable} font-sans bg-[#0d1117] text-[#c9d1d9]`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}