import './globals.css';
import localFont from 'next/font/local';
import { ThemeProvider } from 'next-themes';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';

const formulaOne = localFont({
    variable: '--font-formula-one',
    display: 'swap',
    src: [
        { path: '../../f1fonts/a5a7d0679f778e47-s.p.woff2', weight: '400', style: 'normal' },
        { path: '../../f1fonts/1f75a4dd429d77b6-s.p.woff2', weight: '700', style: 'normal' },
        { path: '../../f1fonts/ad585708510478a8-s.p.woff2', weight: '400', style: 'italic' },
        { path: '../../f1fonts/c6e2547e6fd7e039-s.p.woff2', weight: '900', style: 'normal' },
    ],
});

const formulaOneWide = localFont({
    variable: '--font-formula-one-wide',
    display: 'swap',
    src: [
        { path: '../../f1fonts/fc1344fa9bb93795-s.p.woff2', weight: '400', style: 'normal' },
    ],
});

export const metadata = {
    title: 'Penalty Explainer',
    description: 'An application to analyze and understand Formula 1 penalties using historical data and official regulations.',
}

export default function RootLayout({ children }) {
    return (
        <html
            lang="en"
            className={`h-full ${formulaOne.variable} ${formulaOneWide.variable}`}
            suppressHydrationWarning
        >
            <head>
				<link rel="preconnect" href="https://fonts.googleapis.com" />
				<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="true" />
				<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet" />
				<link href="https://fonts.googleapis.com/css2?family=Titillium+Web:wght@600;700&display=swap" rel="stylesheet" />
                <link href="assets/logo.jpeg" rel="shortcut icon" type="image/x-icon"></link>
            </head>
            <body className="flex flex-col min-h-screen">
                <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
                    <Header />
                    <main className="flex-grow pt-16">{children}</main>
                    <Footer />
                </ThemeProvider>
            </body>
        </html>
    );
}
