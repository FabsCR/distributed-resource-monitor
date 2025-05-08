import React, { useEffect, useRef } from 'react'

export function Terminal({ logs }) {
  const ref = useRef(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight
  }, [logs])

  return (
    <div className="bg-black text-green-400 font-mono rounded-lg overflow-hidden border border-gray-700">
      <div className="flex items-center h-8 bg-gray-800 px-4">
        <div className="flex space-x-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500" />
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <div className="w-3 h-3 rounded-full bg-green-500" />
        </div>
        <span className="ml-4 text-gray-200 text-sm">Terminal</span>
      </div>
      <div ref={ref} className="p-4 h-64 overflow-y-auto">
        {logs.map((log, i) => (
          <div key={i} className="mb-1">
            {log}
          </div>
        ))}
        <div className="animate-pulse">_</div>
      </div>
    </div>
  )
}