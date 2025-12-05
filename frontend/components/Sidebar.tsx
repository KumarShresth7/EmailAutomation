'use client';
import React, { useCallback, memo } from 'react';
import { ShoppingBag, Package, BarChart2, Bot, MessageSquare, AlertTriangle, LogOut } from "lucide-react";
import { useRouter, usePathname } from 'next/navigation';
import { useUser, useClerk } from '@clerk/nextjs';

// Define the menu item type
interface MenuItemProps {
  item: {
    id: number;
    icon: React.ReactNode;
    label: string;
    href: string;
  };
  isActive: boolean;
  onClick: () => void;
}

const MENU_ITEMS = [
  { id: 1, icon: <ShoppingBag size={20} />, label: "Orders", href: "/orders" },
  { id: 2, icon: <Package size={20} />, label: "Inventory", href: "/inventory" },
  { id: 3, icon: <BarChart2 size={20} />, label: "Analytics", href: "/analytics" },
  { id: 4, icon: <Bot size={20} />, label: "Chatbot", href: "/chatbot" },
  { id: 5, icon: <MessageSquare size={20} />, label: "Feedback", href: "/feedback" },
  { id: 6, icon: <AlertTriangle size={20} />, label: "Errors", href: "/errors" },
];

const MenuItem = memo(({ item, isActive, onClick }: MenuItemProps) => (
  <div
    onClick={onClick}
    className={`group flex items-center p-3 rounded-lg mb-2 cursor-pointer transition-all duration-200 border border-transparent
              ${isActive 
                ? 'bg-[#00E676] text-black font-semibold shadow-[0_0_15px_rgba(0,230,118,0.3)]' 
                : 'text-gray-400 hover:bg-gray-900 hover:text-white hover:border-gray-800'}`}
  >
    <div className={`transition-colors ${isActive ? "text-black" : "text-gray-400 group-hover:text-[#00E676]"}`}>
      {item.icon}
    </div>
    <span className="ml-3">{item.label}</span>
  </div>
));
MenuItem.displayName = 'MenuItem';

function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isLoaded } = useUser();
  const { signOut } = useClerk();
  
  const navigate = useCallback((href: string) => {
    router.push(href);
  }, [router]);

  const getInitials = () => {
    if (!isLoaded || !user) return "OM";
    const username = user.username || user.firstName || "";
    return username.substring(0, 2).toUpperCase() || "OM";
  };

  return (
    <aside className="w-64 bg-black border-r border-gray-900 h-screen sticky top-0 flex flex-col shadow-2xl z-50">
      {/* Header / Logo Area */}
      <div className="p-6 border-b border-gray-900">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#00E676] flex items-center justify-center text-black font-bold text-lg shadow-[0_0_10px_rgba(0,230,118,0.2)]">
            {getInitials()}
          </div>
          <div>
            <h2 className="text-white text-sm font-bold tracking-wide uppercase">
              OrderMate<span className="text-[#00E676]">.ai</span>
            </h2>
            <p className="text-gray-500 text-xs">Admin Dashboard</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 overflow-y-auto scrollbar-none">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-4 pl-2">Menu</p>
        {MENU_ITEMS.map((item) => (
          <MenuItem
            key={item.id}
            item={item}
            isActive={pathname?.startsWith(item.href) || false}
            onClick={() => navigate(item.href)}
          />
        ))}
      </nav>

      {/* User / Logout */}
      <div className="p-4 border-t border-gray-900 bg-black">
        <div 
          onClick={() => signOut(() => router.push('/sign-in'))}
          className="flex items-center p-3 rounded-lg cursor-pointer text-gray-400 hover:bg-red-900/20 hover:text-red-500 transition-colors"
        >
          <LogOut size={20} />
          <span className="ml-3 text-sm font-medium">Sign Out</span>
        </div>
      </div>
    </aside>
  );
}

export default memo(Sidebar);