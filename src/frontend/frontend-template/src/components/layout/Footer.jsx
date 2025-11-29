'use client'

export default function Footer() {
    // UI View
    return (
        <footer className="footer">
            <div className="container mx-auto px-4">
                <p className="footer-text">
                    Copyright © {new Date().getFullYear()} F1 Penalty Explainer. All Rights Reserved.
                </p>
            </div>
        </footer>
    );
}
