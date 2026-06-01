export default function Dashboard() {
  return (
    <div className="min-h-screen bg-secondary-50 p-8">
      <h1 className="text-3xl font-bold text-primary-600">pyERP</h1>
      <p className="mt-2 text-secondary-600">
        Full-stack modular ERP for Malaysian businesses
      </p>
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-secondary-800">Finance</h2>
          <p className="mt-1 text-sm text-secondary-500">GL, AP, AR, Bank, Tax</p>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-secondary-800">SCM</h2>
          <p className="mt-1 text-sm text-secondary-500">Items, Inventory, PO, GRN</p>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-secondary-800">CRM</h2>
          <p className="mt-1 text-sm text-secondary-500">Leads, Quotes, SO, DO</p>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-secondary-800">HRM</h2>
          <p className="mt-1 text-sm text-secondary-500">Employees, Payroll, Leave</p>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-secondary-800">MRP</h2>
          <p className="mt-1 text-sm text-secondary-500">BOM, Work Centers, MRP</p>
        </div>
        <div className="rounded-lg border border-secondary-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-secondary-800">Assets</h2>
          <p className="mt-1 text-sm text-secondary-500">Fixed Assets, Depreciation</p>
        </div>
      </div>
    </div>
  );
}
