'use client';
import Sidebar from "@/components/Sidebar";

export default function AppLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <div className="flex h-screen overflow-hidden bg-black w-full">
            {/* Sidebar is now statically imported for stability */}
            <Sidebar />
            <main className="flex-1 overflow-y-auto bg-black">
                {children}
            </main>
        </div>
    );
}