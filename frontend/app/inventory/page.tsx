'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function InventoryPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const router = useRouter() 
  const inventoryData = [
    { id: 'PROD001', name: 'Premium Laptop', category: 'Electronics', price: 1299.99, quantity: 50, reorderPoint: 10, supplier: 'TechCorp', lastRestocked: '2024-01-15' },
    { id: 'PROD002', name: 'Wireless Earbuds', category: 'Electronics', price: 149.99, quantity: 200, reorderPoint: 30, supplier: 'AudioTech', lastRestocked: '2024-02-01' },
  ]

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white p-6 w-full">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-semibold">Inventory Management</h1>
        <div className="flex gap-3">
          <button className="bg-[#00E676] text-black px-4 py-2 rounded-lg hover:bg-[#00ff84]">+ Add Product</button>
          <button className="bg-[#1A1A1A] text-white px-4 py-2 rounded-lg hover:bg-[#00E676] hover:text-black" onClick={()=>router.push('/inventory/forecasting')} >Forecasting</button>
          <button className="bg-[#1A1A1A] text-white px-4 py-2 rounded-lg hover:bg-[#00E676] hover:text-black">Price Adjustment</button>
          <button className="bg-[#1A1A1A] text-white px-4 py-2 rounded-lg hover:bg-[#00E676] hover:text-black">Deadstock</button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search products..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full max-w-md px-4 py-2 rounded-lg bg-[#1A1A1A] border border-[#333] focus:outline-none focus:border-[#00E676]"
        />
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[#1A1A1A]">
            <tr>
              <th className="px-4 py-3 text-left">Product ID</th>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Category</th>
              <th className="px-4 py-3 text-left">Price</th>
              <th className="px-4 py-3 text-left">Quantity</th>
              <th className="px-4 py-3 text-left">Reorder Point</th>
              <th className="px-4 py-3 text-left">Supplier</th>
              <th className="px-4 py-3 text-left">Last Restocked</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {inventoryData.map((item) => (
              <tr key={item.id} className="border-b border-[#333] hover:bg-[#1A1A1A]">
                <td className="px-4 py-3">{item.id}</td>
                <td className="px-4 py-3">{item.name}</td>
                <td className="px-4 py-3">{item.category}</td>
                <td className="px-4 py-3">${item.price}</td>
                <td className="px-4 py-3">
                  <span className={`$ {item.quantity <= item.reorderPoint ? 'text-red-500' : 'text-[#00E676]'}`}>{item.quantity}</span>
                </td>
                <td className="px-4 py-3">{item.reorderPoint}</td>
                <td className="px-4 py-3">{item.supplier}</td>
                <td className="px-4 py-3">{item.lastRestocked}</td>
                <td className="px-4 py-3 flex gap-2">
  <button className="bg-[#00E676] text-black px-3 py-1 rounded-lg hover:bg-[#00C864]">Edit</button>
  <button className="bg-[#1A1A1A] text-white px-3 py-1 rounded-lg hover:bg-[#333333]">Delete</button>
  <button className="bg-[#007F4F] text-white px-3 py-1 rounded-lg hover:bg-[#00A86B]">Restock</button>
</td>

              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
