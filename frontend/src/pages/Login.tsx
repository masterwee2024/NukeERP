export default function Login() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary-50">
      <div className="w-full max-w-md rounded-lg border border-secondary-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-primary-600">pyERP</h1>
        <p className="mt-2 text-secondary-500">Sign in to your account</p>
        <form className="mt-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-secondary-700">
              Email
            </label>
            <input
              type="email"
              className="mt-1 block w-full rounded-md border border-secondary-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-secondary-700">
              Password
            </label>
            <input
              type="password"
              className="mt-1 block w-full rounded-md border border-secondary-300 px-3 py-2 shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <button
            type="submit"
            className="w-full rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
