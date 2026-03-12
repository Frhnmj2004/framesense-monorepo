import Link from "next/link";

export default function Header() {
  return (
    <nav className="fixed top-6 left-1/2 -translate-x-1/2 z-50 w-[90%] max-w-6xl">
      <div className="liquid-glass rounded-full px-6 py-3 flex items-center justify-between shadow-2xl">
        <div className="flex items-center gap-3">
          <div className="bg-primary p-1.5 rounded-lg flex items-center justify-center">
            <span className="text-background-dark text-xl font-bold" aria-hidden>
              ◀
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight">FrameSense</h1>
        </div>
        <div className="hidden md:flex items-center gap-8">
          <Link
            href="/"
            className="text-sm font-medium text-primary border-b-2 border-primary pb-0.5 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-transparent rounded"
          >
            Dashboard
          </Link>
          <Link
            href="#"
            className="text-sm font-medium text-slate-400 hover:text-slate-100 transition-colors"
          >
            Projects
          </Link>
          <Link
            href="#"
            className="text-sm font-medium text-slate-400 hover:text-slate-100 transition-colors"
          >
            Documentation
          </Link>
          <Link
            href="#"
            className="text-sm font-medium text-slate-400 hover:text-slate-100 transition-colors"
          >
            API
          </Link>
        </div>
        <div className="flex items-center gap-4">
          <button
            type="button"
            className="p-2 text-slate-400 hover:text-slate-100 transition-colors rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Notifications"
          >
            <span aria-hidden>🔔</span>
          </button>
          <div
            className="h-8 w-8 rounded-full bg-primary/20 border border-primary/30 overflow-hidden"
            aria-hidden
          >
            <div className="w-full h-full bg-primary/40" />
          </div>
        </div>
      </div>
    </nav>
  );
}
