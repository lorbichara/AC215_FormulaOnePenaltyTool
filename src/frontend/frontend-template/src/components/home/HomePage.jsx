'use client';

import HeroSection from './HeroSection';
import FeaturesSection from './FeaturesSection';

export default function HomePage() {
    return (
        <div className="min-h-screen bg-background">
            <HeroSection />
            <FeaturesSection />
        </div>
    );
}