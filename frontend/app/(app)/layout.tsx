import Sidebar from '@/components/Sidebar';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-muted/30 dark:bg-background">
      <Sidebar />
      <div className="p-4 sm:ml-64">
        <main className="mx-auto max-w-7xl pt-6">
            {/* Fade-in animation for page content */}
            <div className="animate-in fade-in-0 slide-in-from-bottom-3 duration-500">
                {children}
            </div>
        </main>
      </div>
    </div>
  );
}