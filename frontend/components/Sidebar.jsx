'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, ShoppingCart, Package, AlertCircle, MessageSquare, Bot } from 'lucide-react'; // Use Lucide icons for consistency

const menuItems = [
  { name: 'Analytics', href: '/analytics', icon: LayoutDashboard },
  { name: 'Orders', href: '/orders', icon: ShoppingCart },
  { name: 'Inventory', href: '/inventory', icon: Package },
  { name: 'Chatbot', href: '/chatbot', icon: Bot },
  { name: 'Feedback', href: '/feedback', icon: MessageSquare },
  { name: 'Errors', href: '/errors', icon: AlertCircle },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r border-border/40 bg-background/80 backdrop-blur-xl transition-transform">
      <div className="flex h-full flex-col px-3 py-4">
        <div className="mb-10 flex items-center pl-2.5">
          <span className="self-center whitespace-nowrap text-xl font-bold tracking-tight text-foreground">
            OrderMate<span className="text-primary">.ai</span>
          </span>
        </div>
        <ul className="space-y-2 font-medium">
          {menuItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={`group flex items-center rounded-lg p-3 text-sm font-medium transition-all duration-200 
                    ${isActive 
                      ? 'bg-primary/10 text-primary' 
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`}
                >
                  <item.icon className={`h-5 w-5 transition-colors ${isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}`} />
                  <span className="ml-3">{item.name}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
}