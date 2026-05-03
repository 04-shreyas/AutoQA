export default function Navbar() {
  return (
    <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">
            <span className="bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">
              AutoQA
            </span>
          </h1>
          <p className="text-gray-400 text-sm">AI Quality Assurance Platform</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-sm text-gray-400">Last Run</div>
            <div className="text-white font-medium">Loading...</div>
          </div>
        </div>
      </div>
    </nav>
  );
}
