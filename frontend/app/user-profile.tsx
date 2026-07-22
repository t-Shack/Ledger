"use client";

import { useState, useRef, useEffect } from "react";

export function UserProfile() {
  const [isOpen, setIsOpen] = useState(false);
  const [userId, setUserId] = useState<string>("");
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get user ID from environment or localStorage
  useEffect(() => {
    const id = process.env.NEXT_PUBLIC_USER_ID || "user";
    setUserId(id);
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [isOpen]);

  const handleLogout = () => {
    // Clear any stored auth data
    localStorage.removeItem("token");
    localStorage.removeItem("userId");
    // Redirect to login (we'll implement this later)
    setIsOpen(false);
    window.location.href = "/login";
  };

  const getInitial = (id: string) => id.charAt(0).toUpperCase();

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Avatar Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-600 text-sm font-semibold text-white transition hover:bg-accent-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-600"
        title={userId}
        aria-expanded={isOpen}
        aria-label="User menu"
      >
        {getInitial(userId)}
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 z-50 mt-2 w-48 rounded-md border border-border bg-surface shadow-lg">
          <div className="px-4 py-3 border-b border-border">
            <p className="text-xs font-medium text-text-secondary">Logged in as</p>
            <p className="mt-1 truncate text-sm font-medium text-text-primary">{userId}</p>
          </div>
          <button
            onClick={handleLogout}
            className="w-full px-4 py-2 text-left text-sm text-text-primary transition hover:bg-surface-hover"
          >
            Logout
          </button>
        </div>
      )}
    </div>
  );
}
