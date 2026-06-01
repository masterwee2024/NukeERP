import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary-50">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-secondary-300">404</h1>
        <p className="mt-4 text-lg text-secondary-600">Page not found</p>
        <Link
          to="/"
          className="mt-6 inline-block rounded-md bg-primary-600 px-4 py-2 text-white hover:bg-primary-700"
        >
          Go Home
        </Link>
      </div>
    </div>
  );
}
